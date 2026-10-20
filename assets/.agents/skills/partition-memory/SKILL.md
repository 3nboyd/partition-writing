---
name: partition-memory
description: Remember, inspect, correct, or forget explicit personal facts and preferences in Partition's local memory when the user requests memory management.
---

Use `python3 .partition/partition.py memory list` to inspect records and `context "terms"` to find relevant memories. Keep personal context local under `.partition/private/`; the selected model may see any content you read.

Retain durable information only with explicit user authorization or a user-authored opt-in retention instruction. Add a focused record with `memory add "text" --scope global --source "user request"`; use a project scope when appropriate. Inference must use `--kind inferred` and must not be presented as a confirmed user fact. Do not infer preferences from fiction or third-party text.

Correct a record by deleting its full ID and adding the corrected fact. For forgetting, identify the relevant records, delete them, and check the remaining results. Avoid claiming deletion from ChatGPT, backups, model-provider logs, or external systems: these commands only manage Partition's local JSON records. Do not write in analysis-only sessions. User-authored preferences and instructions can also be edited directly when requested.
