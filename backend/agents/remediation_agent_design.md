# Remediation Agent — Design Notes (Day 15)

## Trigger
Verification Agent returns one of: `flagged`, `needs_review`, `discontinued` → Remediation Agent runs.
`cleared` → no action, nothing written.

## Hold record
New Firestore collection: `holds`

Fields:
- `manifest_id`
- `shot_id`
- `tool_name`
- `status` — flagged / needs_review / discontinued (why it's held)
- `evidence` — copied from `tool_registry` at time of hold (so it survives if the registry entry changes later)
- `suggested_substitute` — null until Day 18 substitute-lookup logic fills it in
- `created_at`
- `resolved` — bool, default false
- `resolved_at` — null until resolved

## Delivery-ready gate
A manifest is "delivery ready" only if querying `holds` for that `manifest_id` where `resolved == false` returns zero results. Computed on read, not cached on the manifest doc — avoids stale-flag bugs if a hold is added or resolved after the fact.

## Pipeline position
Director calls: Verification → (if not cleared) Remediation → Governance.
Remediation's job today is scoped to: write the hold record. Two things intentionally deferred:
- Cloud Function notification trigger → Day 17
- Substitute-tool suggestion logic → Day 18

## Open question
Does `resolved` need its own resolved_by/resolved_at trail, or does Governance's `audit_log` own that? Leaning: Governance logs the resolution *event* (who/why); the `holds` doc just flips `resolved` + `resolved_at` for fast querying. Revisit at Day 20 (Governance Agent build).

## Update — Aug 9
Decided: `unknown` (tool not in registry at all) also triggers a hold, same as flagged/needs_review/discontinued. Untracked tools are at least as risky as flagged ones. Trigger set is now: flagged, needs_review, discontinued, unknown. Only `cleared` skips the hold.

## Update — Aug 10 (Day 20)
Decided (Option B): Kafka pub/sub is real, not decorative. governance_agent.py's consumer is built. Actual publish-to-Kafka calls (from Verification for "cleared", from Remediation for held statuses) will be added when Director is built (Day 22) -- Director is the only component that holds manifest_id/shot_id alongside both agents' results, so publishing belongs there rather than forcing a signature change onto already-tested verify_tool().
