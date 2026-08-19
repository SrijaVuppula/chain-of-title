"""
Chain of Title -- Flask API entry point.
"""
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import firestore
from config import GCP_PROJECT_ID
from agents.verification_agent import verify_tool
from agents.director_adk import run_pipeline_adk
from agents.governance_agent import consume_and_log
from google.cloud.firestore_v1.base_query import FieldFilter
import os
import threading
import time

app = Flask(__name__)
CORS(app)
db = firestore.Client(project=GCP_PROJECT_ID, database="chain-of-title-hackathon")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/submit-manifest", methods=["POST"])
def submit_manifest():
    """Accepts a production's AI-tool manifest and stores it in Firestore.
    No agent logic here on purpose -- this just accepts and stores data.
    Verification, remediation, and governance all run separately via
    POST /run-pipeline/<manifest_id>."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "production" not in data or "shots" not in data:
        return jsonify({"error": "Manifest must include 'production' and 'shots'"}), 400
    if not isinstance(data["shots"], list) or len(data["shots"]) == 0:
        return jsonify({"error": "'shots' must be a non-empty list"}), 400
    manifest = {
        "production": data["production"],
        "submitted_by": data.get("submitted_by", "unknown"),
        "submitted_at": datetime.now(timezone.utc),
        "shots": data["shots"],
        "status": "pending",
    }
    doc_ref = db.collection("manifests").document()
    doc_ref.set(manifest)
    return jsonify({"manifest_id": doc_ref.id, "status": "pending"}), 201


@app.route("/verify/<manifest_id>/<shot_id>", methods=["GET"])
def verify_shot(manifest_id, shot_id):
    """Looks up a specific shot within a submitted manifest and verifies
    its AI tool against tool_registry. Returns real, non-mocked results."""
    doc = db.collection("manifests").document(manifest_id).get()
    if not doc.exists:
        return jsonify({"error": f"No manifest found with id '{manifest_id}'"}), 404

    manifest = doc.to_dict()
    shot = next((s for s in manifest.get("shots", []) if s.get("shot_id") == shot_id), None)
    if shot is None:
        return jsonify({"error": f"No shot with id '{shot_id}' in manifest '{manifest_id}'"}), 404

    ai_tool = shot.get("ai_tool")
    if not ai_tool:
        return jsonify({"error": f"Shot '{shot_id}' has no 'ai_tool' field to verify"}), 400

    result = verify_tool(ai_tool)
    return jsonify({
        "manifest_id": manifest_id,
        "shot_id": shot_id,
        "shot_description": shot.get("description"),
        "queried_tool": ai_tool,
        **result,
    }), 200


@app.route("/run-pipeline/<manifest_id>", methods=["POST"])
def run_pipeline_route(manifest_id):
    """Runs the full Director pipeline (Verification -> Remediation ->
    Governance) for an already-submitted manifest and returns the
    aggregated verdict. Not safe to call twice for the same manifest --
    it re-writes holds and re-publishes Kafka events -- so callers must
    invoke this once and hold onto the result rather than re-fetching it."""
    try:
        result = run_pipeline_adk(manifest_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Pipeline failed: {e}"}), 500


@app.route("/audit-log/<manifest_id>", methods=["GET"])
def audit_log_route(manifest_id):
    """Returns every audit_log entry for a manifest, oldest first. Sorted in
    Python, not via Firestore order_by(), to avoid needing a composite index
    (equality filter + order-by on a different field)."""
    docs = list(
        db.collection("audit_log")
        .where(filter=FieldFilter("manifest_id", "==", manifest_id))
        .stream()
    )
    entries = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        ts = data.get("timestamp")
        data["timestamp"] = ts.isoformat() if ts else None
        entries.append(data)
    entries.sort(key=lambda e: e["timestamp"] or "")
    return jsonify({"manifest_id": manifest_id, "entries": entries}), 200

# TODO: GET /report/<production_id> -- aggregate compliance report across
# every manifest submitted for a given production.

def _run_governance_consumer_forever():
    """Runs the Governance Agent's Kafka consumer loop continuously in a
    background thread so audit_log entries appear automatically, with no
    second process to start manually. Wrapped in a retry loop so a
    transient Kafka/Firestore error doesn't silently kill logging."""
    while True:
        try:
            consume_and_log(max_messages=None)
        except Exception as e:
            app.logger.error(f"Governance consumer crashed, restarting in 5s: {e}")
            time.sleep(5)


def _start_governance_consumer():
    thread = threading.Thread(target=_run_governance_consumer_forever, daemon=True)
    thread.start()
    app.logger.info("Governance Agent consumer thread started.")


if __name__ == "__main__":
    # Flask's debug reloader re-imports this module in a watcher process
    # before spawning the real serving process; WERKZEUG_RUN_MAIN is only
    # set in that second process, so this prevents two consumer threads
    # from starting at once.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        _start_governance_consumer()
    app.run(debug=True, port=5001)
