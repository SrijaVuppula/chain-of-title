"""
Verification Agent -- checks an extracted AI tool name against tool_registry
in Firestore and returns cleared / flagged / needs_review / discontinued /
unknown, plus the evidence text.

Built Day 10. Edge cases (empty/None input, unmatched tools) handled Day 13.
See CLAUDE.md for the full agent architecture.
"""

import sys
import re
import difflib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import firestore
import config


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def _base_name(name: str) -> str:
    """Strips parenthetical qualifiers, e.g. 'MidJourney (image/video)' -> 'MidJourney'.
    Registry entries sometimes append category info in parens that Gemini's
    extracted names won't include."""
    return re.sub(r"\s*\([^)]*\)", "", name).strip()


def _get_db():
    return firestore.Client(project=config.GCP_PROJECT_ID, database=config.FIRESTORE_DATABASE)


def _unknown_result(reason: str) -> dict:
    return {
        "matched_name": None,
        "status": "unknown",
        "evidence": reason,
        "vendor": None,
        "match_confidence": 0.0,
    }


def verify_tool(tool_name) -> dict:
    """
    Looks up a (possibly freeform) extracted tool name against the registry.
    Tries an exact slug match first, then a whole-word match on the base
    (paren-stripped) name, then falls back to full-string fuzzy matching.

    Handles None, empty string, and whitespace-only input by returning
    'unknown' immediately, before any Firestore call is made (Day 13 --
    an empty/None name previously caused a malformed Firestore document
    path and either crashed or raised InvalidArgument).
    """
    if not tool_name or not tool_name.strip():
        return _unknown_result("No tool name provided to verify.")

    db = _get_db()

    # Fast path: exact slug match
    doc = db.collection("tool_registry").document(slugify(tool_name)).get()
    if doc.exists:
        return _format_result(doc.to_dict(), confidence=1.0)

    entries = [d.to_dict() for d in db.collection("tool_registry").stream()]
    normalized_query = _normalize(tool_name)

    best_match, best_score = None, 0.0
    for entry in entries:
        normalized_base = _normalize(_base_name(entry["name"]))
        normalized_full = _normalize(entry["name"])

        # Whole-word match on the base name (handles "MidJourney (image/video)"
        # vs. Gemini's "MidJourney-based tool")
        if re.search(rf"\b{re.escape(normalized_base)}\b", normalized_query):
            score = 0.9
        else:
            score = difflib.SequenceMatcher(None, normalized_full, normalized_query).ratio()

        if score > best_score:
            best_match, best_score = entry, score

    if best_match and best_score >= 0.6:
        return _format_result(best_match, confidence=round(best_score, 2))

    return _unknown_result(f"'{tool_name}' does not match any entry in the tool registry.")


def _format_result(entry: dict, confidence: float) -> dict:
    return {
        "matched_name": entry["name"],
        "status": entry["status"],
        "evidence": entry["evidence"],
        "vendor": entry.get("vendor"),
        "match_confidence": confidence,
    }


if __name__ == "__main__":
    test_cases = ["Adobe Firefly", "MidJourney-based tool", "some completely made up tool"]
    for name in test_cases:
        result = verify_tool(name)
        print(f"\nInput: {name!r}")
        for k, v in result.items():
            print(f"  {k}: {v}")
