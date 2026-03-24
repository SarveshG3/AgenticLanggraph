"""
Procurement PR approval graph logic using LangGraph.

Models the nodes and edges for the workflow:
Input -> Validation -> Budget Check -> Policy Compliance -> Vendor Validation
-> Decision -> Notification, plus Clarification / Reject branches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from langgraph.graph import StateGraph, START, END

from tools import (
    check_budget_with_erp,
    run_policy_engine,
    validate_vendor_master,
    send_notification,
)


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
        timestamp = datetime.now(timezone.utc).isoformat()
        self.Audit_Log.append(f"{timestamp} | {message}")


# ---------------------------
# Node implementations
# ---------------------------


def input_node(state: GraphState) -> GraphState:
    """Process incoming PR."""
    state.log("PR received.")
    return state


def validation_node(state: GraphState) -> GraphState:
    """Validate required fields in the PR."""
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
    """Check budget availability in ERP."""
    try:
        amount = float(state.Budget_Code.get("requested_amount", 0))
        state.budget_available = check_budget_with_erp(state.Budget_Code, amount)
    except (NotImplementedError, ValueError):
        # Default to True for demo wiring
        state.budget_available = True
    if state.budget_available:
        state.log("Budget available.")
    else:
        state.Decision_Status = "Rejected"
        state.log("Budget exceeded.")
    return state


def policy_compliance_node(state: GraphState) -> GraphState:
    """Check policy compliance using policy engine."""
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
    """Validate vendor against vendor master."""
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
    """Make final approval decision based on all checks."""
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
    """Send notification to requester."""
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
    """Route based on validation result."""
    return "budget_check" if state.validation_complete else "clarification"


def budget_router(state: GraphState) -> str:
    """Route based on budget availability."""
    return "policy_compliance" if state.budget_available else "reject"


def policy_router(state: GraphState) -> str:
    """Route based on policy compliance."""
    return "vendor_validation" if state.policy_compliant else "reject"


# ---------------------------
# Graph builder
# ---------------------------


def build_graph():
    """Build and compile the procurement approval workflow graph."""
    builder = StateGraph(GraphState)

    # Add nodes
    builder.add_node("input", input_node)
    builder.add_node("validation", validation_node)
    builder.add_node("clarification", lambda s: s)
    builder.add_node("budget_check", budget_check_node)
    builder.add_node("policy_compliance", policy_compliance_node)
    builder.add_node("vendor_validation", vendor_validation_node)
    builder.add_node("decision", decision_node)
    builder.add_node("reject", lambda s: s)
    builder.add_node("notification", notification_node)

    # Add edges
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
