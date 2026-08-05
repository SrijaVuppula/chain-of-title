"""
Chain of Title -- Flask API entry point.
Implemented: BUILD_PLAN.md Days 5-6 (Aug 6-7)
"""
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from google.cloud import firestore

from config import GCP_PROJECT_ID

app = Flask(__name__)
db = firestore.Client(project=GCP_PROJECT_ID, database="chain-of-title-hackathon")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/submit-manifest", methods=["POST"])
def submit_manifest():
    """Accepts a production's AI-tool manifest and stores it in Firestore.
    No agent logic here on purpose (BUILD_PLAN Day 5) -- this just accepts
    and stores data. Verification/Remediation/Governance come in Phase 2-3."""
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


# TODO Day 12: GET  /verify/<shot_id>
# TODO Day 22: GET  /report/<production_id>

if __name__ == "__main__":
    app.run(debug=True, port=5001)