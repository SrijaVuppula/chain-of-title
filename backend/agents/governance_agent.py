"""
Governance Agent -- logs every decision via the IBM watsonx MCP server for an
immutable audit trail. This is the required IBM partner integration point.
Implemented: BUILD_PLAN.md Days 19-20 (Aug 20-21)
"""


def log_decision(shot_id: str, agent_name: str, decision: dict) -> None:
    """Calls the IBM MCP server to record a decision with timestamp and reasoning."""
    raise NotImplementedError("See BUILD_PLAN.md Days 19-20")
