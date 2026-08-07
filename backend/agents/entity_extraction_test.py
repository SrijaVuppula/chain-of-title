"""
Day 9 — entity extraction proof of concept.

Feeds a free-text manifest line to Gemini and gets back structured
fields (shot_id, tool_name, vendor). This is a standalone test to
confirm the pattern works before it's wired into verification_agent.py
on Day 10.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
import config

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "shot_id": {"type": "STRING"},
        "tool_name": {"type": "STRING"},
        "vendor": {"type": "STRING"},
    },
    "required": ["shot_id", "tool_name"],
}


def extract_entities(manifest_line: str) -> dict:
    client = genai.Client(
        vertexai=True,
        project=config.GCP_PROJECT_ID,
        location=config.GCP_LOCATION,
    )
    prompt = f"""Extract the shot ID, AI tool name, and vendor/company name
from this film production manifest line. If the vendor isn't explicitly
named, infer it only if you're confident (e.g. "MidJourney" implies vendor
"Midjourney Inc."). Leave vendor as an empty string if unsure.

Manifest line: "{manifest_line}"
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
        },
    )
    return json.loads(response.text)


if __name__ == "__main__":
    test_line = "Shot 34: de-aging on lead actor using a MidJourney-based tool"
    result = extract_entities(test_line)
    print(json.dumps(result, indent=2))
