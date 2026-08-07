"""
Tests for verification_agent.py (Day 11).
Confirms each of the three original seeded tools returns the correct status.

Run: backend/venv/bin/python -m pytest backend/tests/test_verification_agent.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.verification_agent import verify_tool


def test_adobe_firefly_cleared():
    result = verify_tool("Adobe Firefly")
    assert result["status"] == "cleared"
    assert result["matched_name"] == "Adobe Firefly"


def test_midjourney_flagged():
    result = verify_tool("MidJourney-based tool")
    assert result["status"] == "flagged"
    assert "MidJourney" in result["matched_name"]


def test_topaz_needs_review():
    result = verify_tool("Topaz Video AI")
    assert result["status"] == "needs_review"
    assert result["matched_name"] == "Topaz Video AI"


def test_unknown_tool_returns_unknown_status():
    result = verify_tool("some completely made up tool")
    assert result["status"] == "unknown"
    assert result["matched_name"] is None


def test_multiple_tools_in_one_string():
    """A shot's ai_tool field naming two tools shouldn't silently misfire --
    should either flag it as ambiguous or resolve to the more restrictive
    (worse) status of the two, not just pick one arbitrarily."""
    result = verify_tool("MidJourney and Topaz Video AI")
    assert result["status"] in ("flagged", "needs_review", "ambiguous")


def test_empty_string_tool_name():
    result = verify_tool("")
    assert result["status"] == "unknown"


def test_whitespace_only_tool_name():
    result = verify_tool("   ")
    assert result["status"] == "unknown"


def test_none_tool_name_does_not_crash():
    result = verify_tool(None)
    assert result["status"] == "unknown"
