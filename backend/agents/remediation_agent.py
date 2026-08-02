"""
Remediation Agent -- for flagged/needs-review tools: writes a hold flag,
triggers a Cloud Function notification, and suggests a cleared substitute.
Implemented: BUILD_PLAN.md Days 15-18 (Aug 16-19)
"""


def remediate(shot_id: str, verification_result: dict) -> dict:
    """Writes a hold flag to Firestore, fires a notification, and returns a
    substitute-tool suggestion."""
    raise NotImplementedError("See BUILD_PLAN.md Days 15-18")
