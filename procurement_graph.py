"""
Procurement PR approval flow built with LangGraph.

The graph models the nodes and edges requested by the user:
Input -> Validation -> Budget Check -> Policy Compliance -> Vendor Validation
-> Decision -> Notification, plus Clarification / Reject branches.

Custom tools (ERP budget lookup, policy engine, vendor master lookup, notifier)
are left as stubs with docstrings describing expected I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal, Optional

from langgraph.graph import StateGraph, START, END


# ---------------------------
# Graph state
# ---------------------------

Decision = Literal["Pending", "Approved", "Rejected", "Clarification Needed"]


@dataclass
class GraphState:
    """Minimal state container carried between nodes."""

    PR_ID: str
    Requester_Info: Dict[str, str]
    Item_Details: Dict[str, str]
    Justification: Optional[str] = None
    Budget_Code: Dict[str, str] = field(default_factory=dict)
    Vendor_Info: Dict[str, str] = field(default_factory=dict)
    Delivery_Requirements: Dict[str, str] = field(default_factory=dict)
    Compliance_Flags: Dict[str, bool] = field(default_factory=dict)
    Approval_Hierarchy: List[Dict[str, str]] = field(default_factory=list)
    Decision_Status: Decision = "Pending"
    Audit_Log: List[str] = field(default_factory=list)
    # Internal flags used for routing
    validation_complete: bool = False
    budget_available: bool = False
    policy_compliant: bool = False
    vendor_valid: bool = False
    clarification_reason: Optional[str] = None

    def log(self, message: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        self.Audit_Log.append(f"{timestamp} | {message}")


# ---------------------------
# Stubbed external tools
# ---------------------------

def check_budget_with_erp(budget_code: Dict[str, str], amount: float) -> bool:
    """
    Placeholder for ERP budget check.

    Expected input:
        budget_code: {"cost_center": "...", "funds": "..."}
        amount: numeric amount requested
    Expected output:
        bool indicating if funds are available
    """
    # Implement integration with ERP or finance microservice here.
    raise NotImplementedError("Integrate ERP budget check here.")


def run_policy_engine(state: GraphState) -> Dict[str, bool]:
    """
    Placeholder for procurement policy evaluation.

    Expected input:
        Full GraphState (thresholds, restricted items, approval matrix)
    Expected output:
        {"compliant": bool, "violation": "reason-if-any"}
    """
    raise NotImplementedError("Integrate policy engine here.")


def validate_vendor_master(vendor_info: Dict[str, str]) -> Dict[str, bool]:
    """
    Placeholder for vendor master lookup.

    Expected input:
        vendor_info: {"vendor_id": "...", "contract_ref": "..."}
    Expected output:
        {"valid": bool, "reason": "text-if-invalid"}
    """
    raise NotImplementedError("Integrate vendor validation here.")


def send_notification(requester: Dict[str, str], decision: Decision, details: Dict[str, str]) -> None:
    """
    Placeholder for notification dispatch (email, Slack, Teams).

    Expected input:
        requester: {"name": "...", "email": "..."}
        decision: "Approved" | "Rejected" | "Clarification Needed"
        details: {"pr_id": "...", "message": "..."}
    Expected output:
        None (side effect: message sent)
    """
    raise NotImplementedError("Wire up notification channel here.")


# ---------------------------
# Node implementations
# ---------------------------

def input_node(state: GraphState) -> GraphState:
    state.log("PR received.")
    return state


def validation_node(state: GraphState) -> GraphState:
    required = [
        state.PR_ID,
        state.Requester_Info.get("name"),
        state.Requester_Info.get("department"),
        state.Item_Details.get("description"),
        state.Budget_Code.get("cost_center"),
        state.Vendor_Info.get("vendor_id"),
    ]
    missing = [idx for idx, value in enumerate(required) if not value]
    if missing:
        state.validation_complete = False
        state.Decision_Status = "Clarification Needed"
        state.clarification_reason = "Missing required fields."
        state.log("Validation failed: missing fields.")
    else:
        state.validation_complete = True
        state.log("Validation complete.")
    return state


def budget_check_node(state: GraphState) -> GraphState:
    # Replace this with real call to ERP when ready.
    try:
        amount = float(state.Budget_Code.get("requested_amount", 0))
        state.budget_available = check_budget_with_erp(state.Budget_Code, amount)
    except NotImplementedError:
        # Default to True for demo wiring.
        state.budget_available = True
    if state.budget_available:
        state.log("Budget available.")
    else:
        state.Decision_Status = "Rejected"
        state.log("Budget exceeded.")
    return state


def policy_compliance_node(state: GraphState) -> GraphState:
    try:
        result = run_policy_engine(state)
        state.policy_compliant = result.get("compliant", False)
        violation = result.get("violation")
    except NotImplementedError:
        state.policy_compliant = True
        violation = None

    if state.policy_compliant:
        state.log("Policy compliant.")
    else:
        state.Decision_Status = "Rejected"
        state.Compliance_Flags["policy_violation"] = True
        if violation:
            state.Compliance_Flags["violation_reason"] = violation
        state.log("Policy violation.")
    return state


def vendor_validation_node(state: GraphState) -> GraphState:
    try:
        result = validate_vendor_master(state.Vendor_Info)
        state.vendor_valid = result.get("valid", False)
        reason = result.get("reason")
    except NotImplementedError:
        state.vendor_valid = True
        reason = None

    if state.vendor_valid:
        state.log("Vendor validated.")
    else:
        state.Decision_Status = "Rejected"
        state.log(f"Vendor invalid: {reason or 'unknown reason'}.")
    return state


def decision_node(state: GraphState) -> GraphState:
    if not state.validation_complete:
        state.Decision_Status = "Clarification Needed"
        state.log("Decision: Clarification Needed.")
    elif not state.budget_available or not state.policy_compliant or not state.vendor_valid:
        state.Decision_Status = "Rejected"
        state.log("Decision: Rejected.")
    else:
        state.Decision_Status = "Approved"
        state.log("Decision: Approved.")
    return state


def notification_node(state: GraphState) -> GraphState:
    message = {
        "pr_id": state.PR_ID,
        "status": state.Decision_Status,
        "reason": state.clarification_reason
        or state.Compliance_Flags.get("violation_reason")
        or "",
    }
    try:
        send_notification(state.Requester_Info, state.Decision_Status, message)
    except NotImplementedError:
        state.log("Notification skipped (stub).")
    return state


# ---------------------------
# Router functions
# ---------------------------

def validation_router(state: GraphState) -> str:
    return "budget_check" if state.validation_complete else "clarification"


def budget_router(state: GraphState) -> str:
    return "policy_compliance" if state.budget_available else "reject"


def policy_router(state: GraphState) -> str:
    return "vendor_validation" if state.policy_compliant else "reject"


def vendor_router(state: GraphState) -> str:
    return "decision"


# ---------------------------
# Graph builder
# ---------------------------

def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("input", input_node)
    builder.add_node("validation", validation_node)
    builder.add_node("clarification", lambda s: s)
    builder.add_node("budget_check", budget_check_node)
    builder.add_node("policy_compliance", policy_compliance_node)
    builder.add_node("vendor_validation", vendor_validation_node)
    builder.add_node("decision", decision_node)
    builder.add_node("reject", lambda s: s)
    builder.add_node("notification", notification_node)

    builder.add_edge(START, "input")
    builder.add_edge("input", "validation")
    builder.add_conditional_edges(
        "validation",
        validation_router,
        {
            "budget_check": "budget_check",
            "clarification": "clarification",
        },
    )
    builder.add_conditional_edges(
        "budget_check",
        budget_router,
        {"policy_compliance": "policy_compliance", "reject": "reject"},
    )
    builder.add_conditional_edges(
        "policy_compliance",
        policy_router,
        {"vendor_validation": "vendor_validation", "reject": "reject"},
    )
    builder.add_edge("vendor_validation", "decision")
    builder.add_edge("clarification", "notification")
    builder.add_edge("reject", "notification")
    builder.add_edge("decision", "notification")
    builder.add_edge("notification", END)

    return builder.compile()


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
    print("Decision:", final_state.Decision_Status)
    print("Audit trail:")
    for line in final_state.Audit_Log:
        print(" -", line)
