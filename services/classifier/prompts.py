# services/classifier/prompts.py
"""
This file holds the prompt templates used by the classifier agent.
They guide the LLM on how to classify raw text signals into categories.
"""


# System message (LLM's permanent role)
SYSTEM_PROMPT = """You are a company signal classifier.
Your job is to read a given signal (like a news snippet, LinkedIn update, or blog post)
and classify it into one of these categories:
- hiring
- funding
- tech
- exec
- launch
- other

You must return valid JSON only.
"""


# For asking LLM to classify a single signal
CLASSIFY_PROMPT = """Classify the following signal:

Signal: "{signal_text}"

Return a JSON object with these keys:
- id: unique string id (use "sig_1", "sig_2", etc.)
- type: one of [hiring, funding, tech, exec, launch, other]
- spans: list of key phrases from the text that support your classification
- sentiment: one of [pos, neu, neg]
- confidence: float between 0 and 1
- decidedBy: "llm"
"""