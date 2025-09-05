# services/classifier/agent.py
from dotenv import load_dotenv
load_dotenv()

import os
import json
from typing import List
from openai import OpenAI
from services.classifier.prompts import SYSTEM_PROMPT, CLASSIFY_PROMPT
from services.classifier.classifier_types import ClassifiedSignal
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise RuntimeError(
        "Missing OPENAI_API_KEY. Please add it to your .env file."
    )
client = OpenAI(api_key=OPENAI_API_KEY)


def _coerce_json(text: str) -> dict:
    # Fast path: try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip common Markdown code fences
    stripped = text.strip()
    if stripped.startswith("```"):
        # remove leading ```json or ``` and trailing ```
        stripped = stripped.strip("`")
        # after strip, try to find the first '{' and last '}'
    # Generic: extract JSON object boundaries
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start:end+1]
        return json.loads(candidate)  # will raise if still invalid
    # If all fails, throw with original for debugging
    raise ValueError(f"LLM returned invalid JSON: {text}")


def classify_signal(signal_text: str, signal_id: str = "sig_1") -> ClassifiedSignal:
    """
    Classify a single raw text signal into a structured ClassifiedSignal.
    """
    user_prompt = CLASSIFY_PROMPT.format(signal_text=signal_text)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\nReturn only a single valid JSON object. No prose. No code fences."},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=300,
        temperature=0.2,
        # Ask the model to format as strict JSON
        response_format={"type": "json_object"},
    )

    raw_output = response.choices[0].message.content or ""
    parsed = _coerce_json(raw_output)

    # Always enforce our ID (don’t rely on model’s)
    parsed["id"] = signal_id

    return ClassifiedSignal(**parsed)



def classify_signals_batch(signals: List[str]) -> List[ClassifiedSignal]:
    """
    Classify a batch of raw signals.
    """
    results = []
    for idx, text in enumerate(signals, start=1):
        signal_id = f"sig_{idx}"
        classified = classify_signal(text, signal_id=signal_id)
        results.append(classified)
    return results


if __name__ == "__main__":
    # Example run
    sample_signals = [
        "Acme Corp is expanding its sales team in Europe.",
        "Globex Inc raised $50M in Series B funding.",
        "Initech just launched a new SaaS product."
    ]

    classified = classify_signals_batch(sample_signals)
    for sig in classified:
        print(sig.model_dump_json(indent=2))