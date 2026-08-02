"""
Chain of Title -- Flask API entry point.
Implemented: BUILD_PLAN.md Days 5-6 (Aug 6-7)
"""
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# TODO Day 5:  POST /submit-manifest
# TODO Day 12: GET  /verify/<shot_id>
# TODO Day 22: GET  /report/<production_id>

if __name__ == "__main__":
    app.run(debug=True, port=5000)
