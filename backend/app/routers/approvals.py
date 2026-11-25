from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..agent.executor import execute_action
from ..agent.tools import ToolError
from ..audit import audit
from ..db import get_db
from ..models import PendingAction, ResourceRequest, now
from ..schemas import DecisionIn
from ..security import require_roles
from ..serializers import action_out

router = APIRouter(prefix="/approvals", tags=["approvals"])
reviewer = require_roles("approver", "admin")


@router.get("")
def list_actions(status: Literal["pending", "executed", "rejected", "failed", "all"] = "pending",
                 db=Depends(get_db), user=Depends(reviewer)):
    q = select(PendingAction).order_by(PendingAction.id.desc()).limit(100)
    if status != "all":
        q = q.where(PendingAction.status == status)
    return [action_out(db, a) for a in db.scalars(q)]


def _close_request(db, action, new_status):
    if action.tool == "provision":
        r = db.get(ResourceRequest, action.args.get("request_id"))
        if r and r.status == "awaiting_approval":
            r.status = new_status


@router.post("/{action_id}/decision")
def decide(action_id: int, body: DecisionIn, db=Depends(get_db), user=Depends(reviewer)):
    action = db.execute(select(PendingAction).where(PendingAction.id == action_id)
                        .with_for_update()).scalar_one_or_none()   # lock row: no double-decisions
    if not action:
        raise HTTPException(404, "Action not found")
    if action.status != "pending":
        raise HTTPException(409, f"Action already {action.status}")
    if action.proposed_by == user.id:
        raise HTTPException(403, "You cannot decide an action you proposed")

    action.decided_by, action.decided_at, action.decision_note = user.id, now(), body.note

    if body.decision == "reject":
        action.status = "rejected"
        _close_request(db, action, "rejected")
        audit(db, user.username, "user", "action_rejected", "pending_action", action.id, {"note": body.note})
    else:
        try:
            action.result = execute_action(db, action)
            action.status = "executed"
            audit(db, user.username, "user", "action_executed", "pending_action", action.id, {"result": action.result})
        except ToolError as e:
            action.status, action.result = "failed", {"error": str(e)}
            _close_request(db, action, "failed")
            audit(db, user.username, "user", "action_failed", "pending_action", action.id, {"error": str(e)})
    db.commit()
    return action_out(db, action)