# Procurement PR LangGraph

A minimal agentic flow for procurement PR handling built with LangGraph. Nodes and edges follow the requested design (Input → Validation → Budget Check → Policy Compliance → Vendor Validation → Decision → Notification), with Clarification/Reject branches.

## Files
- `procurement_graph.py` – graph definition, state dataclass, stubbed external tools, and a demo run.
- `procurement.db` – local SQLite seeded on import; holds budgets, approval matrix, restricted items, and vendors.

## How to run the demo
```bash
python procurement_graph.py
```
You will see the decision and audit log. External integrations are stubbed and default to “pass” paths so the flow compiles.

## Integrate real systems
- `check_budget_with_erp`: call your ERP/finance service with `Budget_Code` and amount; return bool.
- `run_policy_engine`: evaluate thresholds, restricted items, approval matrix; return `{"compliant": bool, "violation": "text"}`.
- `validate_vendor_master`: hit vendor master/contracts; return `{"valid": bool, "reason": "text"}`.
- `send_notification`: push the outcome to email/Slack/Teams.

### Sample data now available
- Budgets: `CC-4200` (allocated 20000, used 5000), `CC-5000` (10000, used 9000).
- Approval matrix: Manager (0–5k), Director (5k–20k), CFO (20k–1M).
- Restricted items: Firearms, Explosives, Personal Travel.
- Vendors: V-7788 (active, MSA-123), V-1234 (active, MSA-555), V-9999 (inactive).

## What I still need (tell me and I’ll wire it up)
- Preferred notification channel and payload format.
- Budget API endpoint/shape and auth method.
- Policy rules source (static file, DB, external service) and thresholds.
- Vendor master lookup interface and expected response fields.
