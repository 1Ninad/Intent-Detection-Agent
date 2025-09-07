# services/orchestrator/nodes/intent_parser.py
import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# Canonical value spaces
_EMPLOYEE_BANDS = {"1-50", "51-200", "201-1000", "1001-5000", "5000+"}
_REVENUE_BANDS  = {"<5m", "5-20m", "20-100m", "100m-1b", "1b+"}
_FUNDING_STAGES = {"pre-seed", "seed", "series a", "series b", "series c", "growth", "public"}
_PRIORITY_KEYS  = ["hiring", "funding", "revenue", "leadership", "tech", "product", "events"]



# Data model
@dataclass
class IntentSpec:
    # PROSPECTING BLUEPRINT
    companySeeds: List[str]              # prospect companies explicitly named by the user (3rd-party targets only)
    industry: List[str]                  # e.g., "saas", "fintech", "ecommerce", "healthcare"
    geo: List[str]                       # e.g., "us", "europe", "dach", "apac", "uk"
    employeeBands: List[str]             # choose from _EMPLOYEE_BANDS
    revenueBands: List[str]              # choose from _REVENUE_BANDS
    roleKeywords: List[str]              # buyer teams/titles: "data engineer","ml engineer","revops","cto"
    productKeywords: List[str]           # tech/topics: "snowflake","databricks","kafka","crm"
    stackHints: List[str]                # infra hints: "aws","gcp","azure","postgres","kubernetes"
    useCases: List[str]                  # problems: "etl","observability","cdp","experimentation","rag"
    verticals: List[str]                 # more specific than industry: "insurtech","biotech","gaming","defense"
    fundingStages: List[str]             # normalized to _FUNDING_STAGES
    excludeCompanies: List[str]          # hard exclusions
    excludeKeywords: List[str]           # negative terms to avoid
    priority: Dict[str, float]           # soft weights 0–1 for later task bias
    maxResultsPerTask: Optional[int]     # numeric only if user sets a limit; else None

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)


        def _lc_list(v: List[str]) -> List[str]:
            return [x.strip().lower() for x in (v or []) if x and x.strip()]

        out["industry"]        = _lc_list(self.industry)
        out["geo"]             = _lc_list(self.geo)
        out["roleKeywords"]    = _lc_list(self.roleKeywords)
        out["productKeywords"] = _lc_list(self.productKeywords)
        out["stackHints"]      = _lc_list(self.stackHints)
        out["useCases"]        = _lc_list(self.useCases)
        out["verticals"]       = _lc_list(self.verticals)
        out["excludeKeywords"] = _lc_list(self.excludeKeywords)
        out["employeeBands"] = [b for b in (self.employeeBands or []) if b in _EMPLOYEE_BANDS]
        out["revenueBands"]  = [b for b in (self.revenueBands or []) if b in _REVENUE_BANDS]
        out["fundingStages"] = [s for s in (x.strip().lower() for x in (self.fundingStages or [])) if s in _FUNDING_STAGES]


        pr: Dict[str, float] = {}
        for k in _PRIORITY_KEYS:
            v = (self.priority or {}).get(k, 0.0)
            try:
                v = float(v)
            except Exception:
                v = 0.0
            pr[k] = max(0.0, min(1.0, v))
        out["priority"] = pr


        if self.maxResultsPerTask is not None:
            try:
                m = int(self.maxResultsPerTask)
                out["maxResultsPerTask"] = max(5, min(500, m))
            except Exception: out["maxResultsPerTask"] = None
        else: out["maxResultsPerTask"] = None

        def _dedupe(seq: List[str]) -> List[str]:
            seen = set()
            out_list = []
            for item in seq or []:
                key = item
                if key not in seen:
                    seen.add(key)
                    out_list.append(item)
            return out_list

        for key in [
            "companySeeds", "industry", "geo", "employeeBands", "revenueBands",
            "roleKeywords", "productKeywords", "stackHints", "useCases",
            "verticals", "fundingStages", "excludeCompanies", "excludeKeywords"
        ]:
            out[key] = _dedupe(out[key])

        return out

def intent_to_dict(intent: IntentSpec) -> Dict[str, Any]:
    return intent.to_dict()


# System prompt (BLUEPRINT ONLY)
SYSTEM_PROMPT = """You are an intent parser for a B2B prospecting agent.
Convert the user's free text (they describe THEIR company and target preferences) into a STRICT JSON
"search blueprint" for discovering PROSPECT companies. Return JSON ONLY (no commentary, no markdown)
with EXACTLY this schema and keys:

{
  "companySeeds": string[],           // if any prospect companies explicitly named
  "industry": string[],               // e.g., "saas", "fintech", "ecommerce", "healthcare"
  "geo": string[],                    // e.g., "us", "europe", "dach", "apac", "uk"
  "employeeBands": string[],          // one of: "1-50","51-200","201-1000","1001-5000","5000+"
  "revenueBands": string[],           // one of: "<5m","5-20m","20-100m","100m-1b","1b+"
  "roleKeywords": string[],           // buyer teams/titles: "data engineer","ml engineer","revops","cto"
  "productKeywords": string[],        // tech/topics you care to detect: "snowflake","databricks","kafka","crm"
  "stackHints": string[],             // optional stack/infra hints: "aws","gcp","azure","postgres","kubernetes"
  "useCases": string[],               // problems they should have: "etl","observability","cdp","experimentation","rag"
  "verticals": string[],              // more specific than industry: "insurtech","biotech","gaming","defense"
  "fundingStages": string[],          // normalized to: "pre-seed","seed","series a","series b","series c","growth","public"
  "excludeCompanies": string[],       // hard exclusions if present
  "excludeKeywords": string[],        // terms to avoid in search if present
  "priority": {                       // soft weights to bias task generation later (0–1)
    "hiring": number,
    "funding": number,
    "revenue": number,
    "leadership": number,
    "tech": number,
    "product": number,
    "events": number
  },
  "maxResultsPerTask": number|null    // number only if the user gives a limit
}

Normalization & rules:
- "companySeeds": ONLY third-party target companies named by the user (proper case). Do NOT include the user's own company/product.
- Use lowercase for tokens in industry/geo/roleKeywords/productKeywords/stackHints/useCases/verticals/fundingStages.
- fundingStages: normalize to exactly one of: "pre-seed","seed","series a","series b","series c","growth","public".
- employeeBands: choose only from: "1-50","51-200","201-1000","1001-5000","5000+" when implied; else [].
- revenueBands: choose only from: "<5m","5-20m","20-100m","100m-1b","1b+" when implied; else [].
- excludeCompanies/excludeKeywords: fill only if the user explicitly says to avoid some companies/terms.
- priority: start all at 0.0. Set a key >0.0 only if the text implies emphasis on that signal type. Values must be 0.0–1.0.
- maxResultsPerTask: numeric ONLY if the user specifies a limit; else null.
- Keep arrays concise (<= 6 items each). Do not invent facts. Output JSON only, nothing else.
"""


# OpenAI Parser
def parse_intent(freeText: str) -> IntentSpec:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": freeText or ""}
        ],
        temperature=0.0,  
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    d = json.loads(content)


    return IntentSpec(
        companySeeds=d.get("companySeeds") or [],
        industry=d.get("industry") or [],
        geo=d.get("geo") or [],
        employeeBands=d.get("employeeBands") or [],
        revenueBands=d.get("revenueBands") or [],
        roleKeywords=d.get("roleKeywords") or [],
        productKeywords=d.get("productKeywords") or [],
        stackHints=d.get("stackHints") or [],
        useCases=d.get("useCases") or [],
        verticals=d.get("verticals") or [],
        fundingStages=d.get("fundingStages") or [],
        excludeCompanies=d.get("excludeCompanies") or [],
        excludeKeywords=d.get("excludeKeywords") or [],
        priority=d.get("priority") or {},
        maxResultsPerTask=d.get("maxResultsPerTask"),
    )