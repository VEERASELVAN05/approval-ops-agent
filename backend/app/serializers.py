from .agent.tools import get_capacity
from .models import Allocation, ResourceRequest, User


def action_out(db, a) -> dict:
    proposer = db.get(User, a.proposed_by)
    ctx = {}
    if a.tool == "provision":
        r = db.get(ResourceRequest, a.args.get("request_id"))
        if r:
            ctx = {"vm_count": r.vm_count, "duration_days": r.duration_days,
                   "purpose": r.purpose, "request_status": r.status}
    elif a.tool == "release":
        al = db.get(Allocation, a.args.get("allocation_id"))
        if al:
            owner = db.get(User, al.owner_id)
            ctx = {"vm_count": al.vm_count, "owner": owner.username if owner else None, "allocation_status": al.status}
    return {
        "id": a.id, "tool": a.tool, "args": a.args, "status": a.status,
        "agent_reasoning": a.reasoning,       # model-written: UNVERIFIED, label it so in the UI
        "context": ctx,                       # DB-derived: trustworthy
        "capacity_now": get_capacity(db),
        "proposed_by": proposer.username if proposer else None,
        "decision_note": a.decision_note, "result": a.result,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
    }