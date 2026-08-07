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
