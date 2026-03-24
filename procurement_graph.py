"""
Procurement PR approval flow main entry point.

This module serves as the main entry point for the procurement workflow,
orchestrating the database, tools, and graph components.
"""

from langchain_core.runnables.graph import MermaidDrawMethod

from database import init_db
from graph import build_graph, GraphState

import ssl
ssl._create_default_https_context = ssl._create_unverified_context


# Ensure database is initialized
init_db()


# ---------------------------
# Demo run
# ---------------------------

if __name__ == "__main__":
    graph = build_graph()
    sample_state = GraphState(
        PR_ID="PR-2026-001",
        Requester_Info={"name": "A. Buyer", "department": "IT", "authorization_level": "L2"},
        Item_Details={"description": "Laptops", "quantity": "10", "specifications": "16GB RAM"},
        Justification="Refresh fleet",
        Budget_Code={"cost_center": "CC-4200", "allocated_funds": "20000", "requested_amount": "15000"},
        Vendor_Info={"vendor_id": "V-7788", "contract_ref": "MSA-123"},
        Delivery_Requirements={"timeline": "2026-05-01", "urgency": "Medium"},
    )
    final_state = graph.invoke(sample_state)
    decision_status = (
        final_state.Decision_Status
        if isinstance(final_state, GraphState)
        else final_state.get("Decision_Status")
    )
    audit = (
        final_state.Audit_Log
        if isinstance(final_state, GraphState)
        else final_state.get("Audit_Log", [])
    )
    print(graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER))
    # print(graph.get_graph().draw_png())
    print("\n✓ Decision:", decision_status)
    print("\n✓ Audit trail:")
    for line in audit:
        print("  -", line)
