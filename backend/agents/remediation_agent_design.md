# Remediation Agent — Design Notes

## Trigger
Verification Agent returns one of: `flagged`, `needs_review`, `discontinued`, `unknown` → Remediation Agent runs.
`cleared` → no action, nothing written.

`unknown` (tool not in registry at all) is included deliberately: an untracked tool is at least as risky as one that's explicitly flagged, so it gets the same hold treatment rather than being silently waved through.

## Hold record
Firestore collection: `holds`

Fields:
- `manifest_id`
- `shot_id`
- `tool_name`
- `status` — flagged / needs_review / discontinued / unknown (why it's held)
- `evidence` — copied from `tool_registry` at time of hold (so it survives if the registry entry changes later)
- `suggested_substitute` — filled in by the substitute-lookup logic, or null if no cleared substitute exists in the same category
- `created_at`
- `resolved` — bool, default false
- `resolved_at` — null until resolved

## Delivery-ready gate
A manifest is "delivery ready" only if querying `holds` for that `manifest_id` where `resolved == false` returns zero results. Computed on read, not cached on the manifest doc — avoids stale-flag bugs if a hold is added or resolved after the fact.

## Pipeline position
Director calls: Verification → (if not cleared) Remediation → Governance.

Remediation's responsibilities: write the hold record, fire a best-effort Cloud Function notification, and look up a cleared substitute tool in the same category.

Kafka publish-to-Governance calls happen in the Director, not in Verification or Remediation — the Director is the only component that holds `manifest_id`/`shot_id` alongside both agents' results, so publishing belongs there rather than forcing a signature change onto the already-tested `verify_tool()`.

## Open question
Does `resolved` need its own `resolved_by`/`resolved_at` trail, or does Governance's `audit_log` own that? Leaning: Governance logs the resolution *event* (who/why); the `holds` doc just flips `resolved` + `resolved_at` for fast querying. Not yet implemented.
