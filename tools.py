"""
External tool stubs for Procurement PR approval flow.

This module contains wrappers for ERP systems, policy engines, vendor masters,
and notification services. These can be replaced with real integrations.
"""

from typing import Dict

from database import get_db


def check_budget_with_erp(budget_code: Dict[str, str], amount: float) -> bool:
    """
    Expected input:
        budget_code: {"cost_center": "...", "funds": "..."}
        amount: numeric amount requested
    Expected output:
        bool indicating if funds are available
    """
    cost_center = budget_code.get("cost_center")
    if not cost_center:
        return False

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT allocated, used FROM budgets WHERE cost_center = ?", (cost_center,)
        )
        row = cur.fetchone()
        if not row:
            return False
        allocated, used = row
        available = allocated - used
        return available >= amount


def run_policy_engine(state) -> Dict[str, str | bool]:
    """
    Expected input:
        Full GraphState (thresholds, restricted items, approval matrix)
    Expected output:
        {"compliant": bool, "violation": "reason-if-any"}
    """
    description = (state.Item_Details.get("description") or "").lower()
    requested_amount = float(state.Budget_Code.get("requested_amount", 0) or 0)

    with get_db() as conn:
        cur = conn.cursor()

        # Restricted item check
        cur.execute("SELECT category FROM restricted_items")
        for (category,) in cur.fetchall():
            if category.lower() in description:
                return {"compliant": False, "violation": f"Restricted item: {category}"}

        # Approval matrix lookup
        cur.execute(
            """
            SELECT role, min_amount, max_amount
            FROM approval_matrix
            WHERE ? >= min_amount AND ? < max_amount
            ORDER BY min_amount ASC
            LIMIT 1
            """,
            (requested_amount, requested_amount),
        )
        approval_row = cur.fetchone()

    if not approval_row:
        return {"compliant": False, "violation": "No approval rule for amount"}

    role, min_amt, max_amt = approval_row
    state.Approval_Hierarchy = [
        {
            "role": role,
            "min_amount": f"{min_amt}",
            "max_amount": f"{max_amt}",
        }
    ]
    return {"compliant": True, "violation": ""}


def validate_vendor_master(vendor_info: Dict[str, str]) -> Dict[str, str | bool]:
    """
    Expected input:
        vendor_info: {"vendor_id": "...", "contract_ref": "..."}
    Expected output:
        {"valid": bool, "reason": "text-if-invalid"}
    """
    vendor_id = vendor_info.get("vendor_id")
    if not vendor_id:
        return {"valid": False, "reason": "Missing vendor_id"}

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT vendor_id, active, contract_ref FROM vendors WHERE vendor_id = ?",
            (vendor_id,),
        )
        row = cur.fetchone()

    if not row:
        return {"valid": False, "reason": "Vendor not found"}

    _, active, contract_ref = row
    if not active:
        return {"valid": False, "reason": "Vendor inactive/blocked"}

    requested_contract = vendor_info.get("contract_ref")
    if requested_contract and requested_contract != contract_ref:
        return {"valid": False, "reason": "Contract reference mismatch"}

    return {"valid": True, "reason": ""}


def send_notification(requester: Dict[str, str], decision: str, details: Dict[str, str]) -> None:
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
