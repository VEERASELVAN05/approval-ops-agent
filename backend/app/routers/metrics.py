from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from ..db import get_db
from ..models import AgentRun, AuditLog, PendingAction, ResourceRequest, ToolCall
from ..security import require_roles

router = APIRouter(tags=["observability"])


def _n(db, q):
    return int(db.scalar(q) or 0)


@router.get("/metrics")
def metrics(db=Depends(get_db), user=Depends(require_roles("approver", "admin"))):
    approved = _n(db, select(func.count(PendingAction.id)).where(PendingAction.status.in_(["executed", "failed"])))
    rejected = _n(db, select(func.count(PendingAction.id)).where(PendingAction.status == "rejected"))
    pending = _n(db, select(func.count(PendingAction.id)).where(PendingAction.status == "pending"))
    decided = approved + rejected
    lat = sorted(db.scalars(select(AgentRun.latency_ms).order_by(AgentRun.id.desc()).limit(500)))
    return {
        "requests_total": _n(db, select(func.count(ResourceRequest.id))),
        "actions": {"pending": pending, "approved": approved, "rejected": rejected},
        "approval_rate": round(approved / decided, 3) if decided else None,
        "tool_calls_total": _n(db, select(func.count(ToolCall.id))),
        "tool_errors_total": _n(db, select(func.count(ToolCall.id)).where(ToolCall.ok.is_(False))),
        "agent_runs_total": _n(db, select(func.count(AgentRun.id))),
        "agent_runs_failed": _n(db, select(func.count(AgentRun.id)).where(AgentRun.ok.is_(False))),
        "latency_ms_avg": round(sum(lat) / len(lat), 1) if lat else None,
        "latency_ms_p95": round(lat[int(0.95 * (len(lat) - 1))], 1) if lat else None,
    }


@router.get("/audit")
def audit_trail(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                db=Depends(get_db), user=Depends(require_roles("admin"))):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset))
    return [{"id": r.id, "ts": r.ts.isoformat(), "actor": r.actor, "actor_type": r.actor_type,
             "event": r.event, "entity": r.entity, "entity_id": r.entity_id,
             "details": r.details, "trace_id": r.trace_id} for r in rows]