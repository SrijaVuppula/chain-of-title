"""
Governance Agent -- consumes decision events from a Confluent topic (published
by Verification/Remediation) and persists them to `audit_log` for an immutable
audit trail. Built using IBM Bob as part of the development process, per the
IBM track's mandatory requirement (see CLAUDE.md).
Implemented: BUILD_PLAN.md Days 19-20 (Aug 20-21)
"""


def log_decision(shot_id: str, agent_name: str, decision: dict) -> None:
    """Consumes a decision event from Confluent and records it with timestamp and reasoning."""
    raise NotImplementedError("See BUILD_PLAN.md Days 19-20")
