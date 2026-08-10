"""
Cloud Function: notify_hold
HTTP-triggered. Called by remediation_agent.py whenever a hold is written.
Logs the event to Cloud Logging -- the "notification" for Day 17 is
intentionally just a structured log line, not email (decided Aug 9, to
keep this zero-cost/zero-setup, same reasoning as the Confluent->Kafka swap).

Note: functions_framework pre-attaches a root log handler before user code
runs, so logging.basicConfig() alone is a no-op and INFO-level calls get
silently dropped (effective level stays WARNING). force=True overrides this.
"""
import functions_framework
import logging

logging.basicConfig(level=logging.INFO, force=True)


@functions_framework.http
def notify_hold(request):
    data = request.get_json(silent=True) or {}
    manifest_id = data.get("manifest_id", "unknown")
    shot_id = data.get("shot_id", "unknown")
    tool_name = data.get("tool_name", "unknown")
    status = data.get("status", "unknown")
    hold_id = data.get("hold_id", "unknown")

    msg = f"HOLD NOTIFICATION | manifest={manifest_id} shot={shot_id} tool={tool_name} status={status} hold_id={hold_id}"
    logging.info(msg)
    print(msg)  # stdout is always captured by Cloud Logging regardless of log-level config

    return {"logged": True, "hold_id": hold_id}, 200
