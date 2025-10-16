import os
import json
import time
import uuid
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

# -------------------- Logging --------------------
logger = logging.getLogger("pplx_signal_search")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# -------------------- API --------------------
PPLX_API_URL = "https://api.perplexity.ai/chat/completions"
PPLX_API_KEY = os.getenv("PPLX_API_KEY")

# -------------------- Structured Output Schema (EXACTLY YOUR SCHEMA) --------------------
RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "companyInfo": {
                "type": "object",
                "properties": {
                    "companyDomain": {"type": "string"},
                    "companyName": {"type": "string"},
                },
                "required": ["companyDomain", "companyName"],
            },
            "signalInfo": {
                "type": "object",
                "properties": {
                    "signalId": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["tech", "hiring", "product", "finance", "other"],
                    },
                    "action": {"type": "string"},
                    "title": {"type": "string"},
                    "snippet": {"type": "string"},
                    "primaryTime": {"type": "string"},
                    "detectedAt": {"type": "string"},
                },
                "required": [
                    "signalId",
                    "type",
                    "action",
                    "title",
                    "snippet",
                    "primaryTime",
                    "detectedAt",
                ],
            },
            "sourceInfo": {
                "type": "object",
                "properties": {
                    "sourceUrl": {"type": "string"},
                    "host": {"type": "string"},
                    "sourceType": {
                        "type": "string",
                        "enum": ["news", "press", "job", "social", "blog", "report", "gov"],
                    },
                },
                "required": ["sourceUrl", "host", "sourceType"],
            },
            "enrichmentInfo": {
                "type": "object",
                "properties": {
                    "geo": {"type": ["string", "null"]},
                    "industry": {"type": ["string", "null"]},
                    "productKeywords": {"type": "array", "items": {"type": "string"}},
                    "tech": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                    "hash": {"type": "string"},
                },
                "required": ["productKeywords", "tech", "confidence", "hash"],
            },
        },
        "required": ["companyInfo", "signalInfo", "sourceInfo", "enrichmentInfo"],
        "additionalProperties": False,
    },
}

# Allowed values per Perplexity API for search_recency_filter
_ALLOWED_RECENCY = {"hour", "day", "week", "month", "year"}

def _sanitize_recency(recency: str) -> str:
    r = (recency or "month").lower().strip()
    return r if r in _ALLOWED_RECENCY else "month"


# -------------------- Heuristics & Utilities --------------------
DEFAULT_PREFERRED_SOURCES = ["press", "news", "job", "blog"]

JOB_HOST_HINTS = [
    "greenhouse.io", "boards.greenhouse", "lever.co", "ashbyhq.com", "workable.com",
    "smartrecruiters.com", "icims.com", "jobvite.com", "bamboohr.com", "teamtailor.com",
    "myworkdayjobs.com", "workday.com", "wellfound.com", "angel.co", "indeed.com", "glassdoor.com",
    "careers", "jobs"
]

_GEO_ALIASES = {
    "US": ["us", "usa", "united states", "america", "u.s."],
    "CA": ["canada", "ca"],
    "UK": ["uk", "united kingdom", "britain", "england"],
    "EU": ["eu", "europe", "european"],
    "IN": ["india", "in"],
}

_INDUSTRY_HINTS = {
    "Fintech": ["fintech", "payments", "bank", "banking", "lending", "insurtech", "wealth", "brokerage", "trading"],
    "Healthcare": ["healthcare", "health tech", "medtech", "biotech", "pharma", "clinical"],
    "SaaS": ["saas", "software-as-a-service", "b2b software", "cloud software"],
    "Ecommerce": ["e-commerce", "ecommerce", "retail tech", "marketplace"],
    "Security": ["security", "cybersecurity", "infosec"],
    "AI": ["ai", "artificial intelligence", "ml", "machine learning", "genai", "generative ai"],
    "Data": ["data platform", "analytics", "data engineering", "lakehouse", "warehouse"],
}

_ROLE_LEADERSHIP = [
    "ceo","chief executive officer","cfo","chief financial officer","cto","chief technology officer",
    "cdo","chief data officer","chief ai officer","cpo","chief product officer","cro","chief revenue officer",
    "coo","chief operating officer","chief information officer","cio"
]
_VERBS_LEADERSHIP = [
    "appoints","appointed","names","named","hires","hired","steps down","resigns","resigned",
    "replaces","replaced","succeeds","succeeded","joins as","promotes","promoted"
]
_ROLE_HIRING = [
    "ml engineer","machine learning engineer","data engineer","analytics engineer","data scientist",
    "site reliability engineer","sre","backend engineer","frontend engineer","full stack","devops"
]

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _host_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def _infer_source_type(url: str, fallback: str = "news") -> str:
    host = _host_from_url(url)
    path = urlparse(url).path.lower()
    if any(h in host for h in JOB_HOST_HINTS) or "/careers" in path or "/jobs" in path:
        return "job"
    if "press" in host or "/press" in path or "/newsroom" in path:
        return "press"
    if "blog" in host or "/blog" in path or "medium.com" in host or "substack.com" in host:
        return "blog"
    return fallback

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _coerce_list_str(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x if isinstance(i, (str, int, float, bool))]
    if isinstance(x, (str, int, float, bool)):
        return [str(x)]
    return []

def _canonical_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    if d.startswith("www."):
        d = d[4:]
    parts = d.split(".")
    if len(parts) <= 2:
        return d
    return ".".join(parts[-2:])  # naive eTLD+1

def _recent_enough(iso_str: str, recency_days: int) -> bool:
    if not iso_str:
        return True
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)) <= timedelta(days=recency_days)
    except Exception:
        return True

def _contains_any(text: str, needles: List[str]) -> bool:
    s = (text or "").lower()
    return any(n in s for n in needles)

def _rank_prefer_sources(items: List[Dict[str, Any]], prefer: List[str]) -> List[Dict[str, Any]]:
    prio = {t: i for i, t in enumerate(prefer)}
    return sorted(items, key=lambda it: prio.get(it.get("sourceInfo", {}).get("sourceType", "other"), 999))

# -------------------- Lenient JSON parsing (repairs truncated arrays) --------------------
def _extract_json_objects(raw: str) -> List[Dict[str, Any]]:
    """Extract top-level JSON objects by brace-balancing, ignoring braces inside strings."""
    objs: List[Dict[str, Any]] = []
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(raw):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start != -1:
                candidate = raw[start:i+1]
                try:
                    objs.append(json.loads(candidate))
                except Exception:
                    pass
                start = -1
    return objs

def _safe_json_array(raw: str) -> List[Dict[str, Any]]:
    """Try strict JSON first; if it fails, recover objects and return as a list."""
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        # If it's a single object, wrap it
        if isinstance(data, dict):
            return [data]
    except Exception:
        pass
    # Lenient recovery
    recovered = _extract_json_objects(raw)
    return recovered


# -------------------- Auto-derive constraints from free text --------------------
def _find_geos(text: str) -> List[str]:
    t = (text or "").lower()
    out = []
    for code, aliases in _GEO_ALIASES.items():
        if any(a in t for a in aliases):
            out.append(code)
    if "north america" in t:
        for code in ["US", "CA"]:
            if code not in out:
                out.append(code)
    return out

def _find_industries(text: str) -> List[str]:
    t = (text or "").lower()
    out = []
    for tag, hints in _INDUSTRY_HINTS.items():
        if any(h in t for h in hints):
            out.append(tag)
    return out

def _infer_signal_types(text: str) -> List[str]:
    t = (text or "").lower()
    signal = set()
    if "leadership" in t or _contains_any(t, _ROLE_LEADERSHIP) or _contains_any(t, _VERBS_LEADERSHIP):
        signal.add("other")   # leadership changes
    if "hiring" in t or "roles" in t or "jobs" in t or _contains_any(t, _ROLE_HIRING):
        signal.add("hiring")
    if "funding" in t or "raised" in t or "series a" in t or "series b" in t or "seed" in t:
        signal.add("finance")
    if "launch" in t or "partner" in t or "partnership" in t or "acquire" in t or "acquisition" in t:
        signal.add("product")
    if "stack" in t or "adopt" in t or "migrate" in t or "technology" in t:
        signal.add("tech")
    return list(signal) or ["other"]

def _guess_prefer_sources(text: str) -> List[str]:
    t = (text or "").lower()
    if "hiring" in t or _contains_any(t, _ROLE_HIRING):
        return ["job", "press", "news", "blog"]
    if "leadership" in t or _contains_any(t, _ROLE_LEADERSHIP):
        return ["press", "news", "blog"]
    return ["press", "news", "job", "blog"]

def _infer_recency_days(text: str) -> int:
    t = (text or "").lower()
    if "last 30 days" in t or "past 30 days" in t or "last month" in t:
        return 35
    if "last quarter" in t or "past quarter" in t:
        return 100
    if "last 6 months" in t or "past 6 months" in t:
        return 190
    return 120

def _infer_min_results(text: str) -> int:
    t = f" { (text or '').lower() } "
    for n in [5, 8, 10, 12, 15, 20, 25]:
        if f" {n} " in t:
            return max(8, n)
    return 10

def deriveConstraintsFromText(freeText: str) -> Dict[str, Any]:
    geos = _find_geos(freeText)
    industries = _find_industries(freeText)
    signal_types = _infer_signal_types(freeText)
    prefer = _guess_prefer_sources(freeText)
    recency_days = _infer_recency_days(freeText)
    min_results = _infer_min_results(freeText)

    role_keywords: List[str] = []
    if "leadership" in freeText.lower():
        role_keywords = list(dict.fromkeys(_ROLE_LEADERSHIP + _VERBS_LEADERSHIP))

    # Extract soft needles from the free text to help relevance checks
    soft_terms = []
    for bag in _INDUSTRY_HINTS.values():
        for w in bag:
            if w in freeText.lower():
                soft_terms.append(w)
    soft_terms = list(dict.fromkeys(soft_terms))

    return {
        "geos": geos,                         # e.g., ["US","CA"]
        "industries": industries,             # e.g., ["Fintech","SaaS"]
        "signalTypes": signal_types,          # subset of {"tech","hiring","product","finance","other"}
        "roleKeywords": role_keywords,        # leadership or hiring titles if detected
        "productKeywords": soft_terms,        # soft relevance needles from text
        "techKeywords": [],                   # keep open; can be extended later
        "preferSources": prefer,              # preferred source order
        "recencyDays": recency_days,          # post-filter freshness window
        "minResults": min_results,            # aim to collect before trimming to limit
    }

# -------------------- Validation / Normalization --------------------
def _validate_and_fix(items: List[Dict[str, Any]], search_results: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    fixed: List[Dict[str, Any]] = []
    sr_url = None
    if search_results:
        for sr in search_results:
            u = sr.get("url")
            if isinstance(u, str) and u.startswith("http"):
                sr_url = u
                break

    detected_at = _now_iso()

    for item in items:
        try:
            company = item.get("companyInfo", {}) or {}
            signal = item.get("signalInfo", {}) or {}
            source = item.get("sourceInfo", {}) or {}
            enrich = item.get("enrichmentInfo", {}) or {}

            # Company
            companyDomain = _canonical_domain(str(company.get("companyDomain", "")).strip())
            companyName = str(company.get("companyName", "")).strip()

            # Source
            sourceUrl = source.get("sourceUrl")
            if not isinstance(sourceUrl, str) or not sourceUrl.startswith("http"):
                sourceUrl = sr_url or ""
            host = _host_from_url(sourceUrl)
            sourceType = source.get("sourceType")
            if sourceType not in ["news", "press", "job", "social", "blog", "report", "gov"]:
                sourceType = _infer_source_type(sourceUrl)

            # Signal
            signalType = signal.get("type")
            if signalType not in ["tech", "hiring", "product", "finance", "other"]:
                signalType = "other"
            signalId = str(signal.get("signalId") or uuid.uuid4())
            title = str(signal.get("title", "")).strip()
            snippet = str(signal.get("snippet", "")).strip()
            primaryTime = str(signal.get("primaryTime", "")).strip()
            detectedAt = str(signal.get("detectedAt") or detected_at)

            # Enrichment
            geo = enrich.get("geo")
            geo = None if geo in (None, "", "null", "None") else str(geo)
            industry = enrich.get("industry")
            industry = None if industry in (None, "", "null", "None") else str(industry)
            productKeywords = _coerce_list_str(enrich.get("productKeywords"))
            tech = _coerce_list_str(enrich.get("tech"))
            try:
                confidence = float(enrich.get("confidence"))
                confidence = max(0.0, min(1.0, confidence))
            except Exception:
                confidence = 0.7  # sensible default floor

            dedup_hash = _sha256(f"{sourceUrl}|{title}")

            fixed.append({
                "companyInfo": {"companyDomain": companyDomain, "companyName": companyName},
                "signalInfo": {
                    "signalId": signalId, "type": signalType, "action": str(signal.get("action","")).strip(),
                    "title": title, "snippet": snippet, "primaryTime": primaryTime, "detectedAt": detectedAt
                },
                "sourceInfo": {"sourceUrl": sourceUrl, "host": host, "sourceType": sourceType},
                "enrichmentInfo": {
                    "geo": geo, "industry": industry, "productKeywords": productKeywords,
                    "tech": tech, "confidence": confidence, "hash": dedup_hash
                },
            })
        except Exception as e:
            logger.warning(f"Skipping malformed item: {e}")
    return fixed

def _is_valid_by_constraints(item: Dict[str, Any], cons: Dict[str, Any], free_text: str) -> bool:
    ci = item.get("companyInfo", {}) or {}
    si = item.get("signalInfo", {}) or {}
    so = item.get("sourceInfo", {}) or {}
    ei = item.get("enrichmentInfo", {}) or {}

    # Domain sanity
    domain = _canonical_domain(ci.get("companyDomain", ""))
    if not domain or "." not in domain:
        return False

    # Geo filter (if the model emitted geo)
    if cons.get("geos"):
        geo = (ei.get("geo") or "").upper()
        if geo and geo not in [g.upper() for g in cons["geos"]]:
            return False

    # Industry filter (if the model emitted industry)
    if cons.get("industries"):
        ind = (ei.get("industry") or "").lower()
        if ind and not _contains_any(ind, [x.lower() for x in cons["industries"]]):
            return False

    # Signal type filter
    if cons.get("signalTypes"):
        if si.get("type") not in cons["signalTypes"]:
            return False

    # Role keywords (if any) must appear in title/snippet for hiring/leadership use-cases
    rk = cons.get("roleKeywords") or []
    if rk:
        blob = f"{si.get('title','')} {si.get('snippet','')}"
        if not _contains_any(blob, rk):
            return False

    # Soft relevance: product/tech keywords (from free text) should help accept
    soft_needles = (cons.get("productKeywords") or []) + (cons.get("techKeywords") or [])
    if soft_needles:
        blob = f"{si.get('title','')} {si.get('snippet','')}"
        if not _contains_any(blob, soft_needles):
            # let it pass if roleKeywords were satisfied; otherwise drop
            if not rk:
                return False

    # Recency
    if not _recent_enough(si.get("primaryTime",""), int(cons.get("recencyDays", 120))):
        return False

    return True

def _apply_constraints(items: List[Dict[str, Any]], cons: Dict[str, Any], free_text: str) -> List[Dict[str, Any]]:
    # Hard-filter + dedupe
    filtered: List[Dict[str, Any]] = []
    seen = set()
    for it in items:
        if not _is_valid_by_constraints(it, cons, free_text):
            continue
        key = (it["companyInfo"]["companyDomain"], it["enrichmentInfo"]["hash"])
        if key in seen:
            continue
        seen.add(key)
        filtered.append(it)

    # If too few, relax soft needles (product/tech) first
    want_min = int(cons.get("minResults", 10))
    if len(filtered) < want_min and ((cons.get("productKeywords") or []) or (cons.get("techKeywords") or [])):
        relaxed = []
        seen2 = set()
        for it in items:
            # Copy cons and remove soft needles
            cons2 = dict(cons)
            cons2["productKeywords"] = []
            cons2["techKeywords"] = []
            if not _is_valid_by_constraints(it, cons2, free_text):
                continue
            key = (it["companyInfo"]["companyDomain"], it["enrichmentInfo"]["hash"])
            if key in seen or key in seen2:
                continue
            seen2.add(key)
            relaxed.append(it)
            if len(filtered) + len(relaxed) >= want_min:
                break
        filtered.extend(relaxed)

    # Prefer desired source types
    filtered = _rank_prefer_sources(filtered, cons.get("preferSources") or DEFAULT_PREFERRED_SOURCES)
    return filtered

# -------------------- Prompting --------------------
def _build_prompt(free_text: str, cons: Dict[str, Any], limit: int) -> List[Dict[str, str]]:
    # System prompt emphasizes RELEVANCE to the salesperson's company/offering.
    sys = (
        "You are a B2B prospecting agent. Search the live web and extract concrete company-level buying signals "
        "(hiring, product launches, technology adoption/migrations, funding, partnerships, acquisitions, leadership changes). "
        "ONLY return companies that are RELEVANT PROSPECTS for the salesperson's company and offering described by the user. "
        "Avoid generic market reports, vendor lists, or companies outside the described scope. Prefer official sources, also sources like each company's blog and news or similar websites then LinkedIn for company's hiring etc related and Crunchbase for funding etc related"
        "(company press/newsroom, careers, reputable news/job boards). Output MUST strictly match the provided JSON Schema. "
        "Use the canonical company domain (eTLD+1). Use ISO-8601 timestamps. Snippet = 1–3 sentences. One strong signal per company."
    )

    bullets = []
    if cons.get("geos"):
        bullets.append(f"- Geography: {', '.join(cons['geos'])}")
    if cons.get("industries"):
        bullets.append(f"- Industry: {', '.join(cons['industries'])}")
    if cons.get("signalTypes"):
        bullets.append(f"- Signal types: {', '.join(cons['signalTypes'])}")
    if cons.get("roleKeywords"):
        bullets.append(f"- Role keywords: {', '.join(cons['roleKeywords'])}")
    if cons.get("productKeywords"):
        bullets.append(f"- Product keywords (soft relevance): {', '.join(cons['productKeywords'])}")
    if cons.get("techKeywords"):
        bullets.append(f"- Tech keywords (soft relevance): {', '.join(cons['techKeywords'])}")
    if cons.get("preferSources"):
        bullets.append(f"- Prefer sources: {', '.join(cons['preferSources'])}")
    bullets.append(f"- Aim for recency within ~{int(cons.get('recencyDays', 120))} days where possible")
    bullets.append(f"- Return up to {max(limit*2, 12)} candidates before filtering to top {limit}")

    user = (
        f"Salesperson free text describing THEIR company, offering, and target preferences:\n{free_text}\n\n"
        "Constraints to obey:\n" + "\n".join(bullets)
    )

    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ]

# -------------------- Perplexity Request --------------------
def _pplx_request(messages: List[Dict[str, str]],
                  recency: str = "month",
                  domains: Optional[List[str]] = None,
                  model: str = "sonar-pro",
                  max_tokens: int = 2200,
                  temperature: float = 0.15) -> Dict[str, Any]:
    if not PPLX_API_KEY:
        raise RuntimeError("PPLX_API_KEY is not set")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "search_recency_filter": _sanitize_recency(recency),  
        "response_format": {"type": "json_schema", "json_schema": {"schema": RESPONSE_SCHEMA}},
    }
    
    if domains:
        payload["search_domain_filter"] = domains

    headers = {"Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json"}

    for attempt in range(3):
        resp = requests.post(PPLX_API_URL, headers=headers, json=payload, timeout=120)
        if resp.status_code >= 500:
            time.sleep(1.2 * (attempt + 1))
            continue
        if resp.status_code != 200:
            raise RuntimeError(f"Perplexity API error {resp.status_code}: {resp.text}")
        return resp.json()
    raise RuntimeError("Perplexity API unavailable after retries")

# -------------------- Public Entrypoint --------------------
def searchProspectSignals(inputText: str,
                          limit: int = 10,
                          constraints: Optional[Dict[str, Any]] = None,
                          recency: str = "month",
                          domains: Optional[List[str]] = None,
                          model: str = "sonar-pro") -> List[Dict[str, Any]]:
    """
    Generic Perplexity-backed search that adapts to the salesperson's free text.
    - Auto-derives constraints if none are provided.
    - Enforces normalization and post-filtering for clean Neo4j/Qdrant ingestion.
    """
    cons = constraints or deriveConstraintsFromText(inputText)
    messages = _build_prompt(inputText, cons, limit)

    data = _pplx_request(
        messages=messages,
        recency=recency,
        domains=domains,
        model=model,
        max_tokens=2200,
        temperature=0.15,
    )

    raw = data["choices"][0]["message"]["content"]
    search_results = data.get("search_results", None)

    parsed = _safe_json_array(raw)
    if not isinstance(parsed, list) or len(parsed) == 0:
        # Keep a short preview of raw to avoid huge logs
        preview = (raw or "")[:600]
        raise RuntimeError(f"Model did not return parseable JSON array. Raw preview: {preview}")


    fixed = _validate_and_fix(parsed, search_results)
    filtered = _apply_constraints(fixed, cons, inputText)

    now_iso = _now_iso()
    for it in filtered:
        it["signalInfo"]["detectedAt"] = it["signalInfo"].get("detectedAt") or now_iso

    return filtered[:limit]
