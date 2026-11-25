import logging
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from ..audit import audit
from ..models import Allocation, InventoryPool, PendingAction, ResourceRequest
from ..policy import ROLE_LIMITS

log = logging.getLogger("tools")


class ToolError(Exception):
    """Expected, user-explainable failure (policy, not-found, etc.)."""


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")  # model can't smuggle in e.g. user_id


class CheckCapacityArgs(_Args):
    vm_count: int = Field(ge=1, le=100, description="Number of VMs wanted")
    duration_days: int = Field(ge=1, le=365, description="How many days")


class CreateRequestArgs(_Args):
    vm_count: int = Field(ge=1, le=100)
    duration_days: int = Field(ge=1, le=365)
    purpose: str = Field(min_length=3, max_length=200, description="Short purpose of the environment")


class ProvisionArgs(_Args):
    request_id: int = Field(ge=1)
    reasoning: str = Field(min_length=3, max_length=600,
                           description="Why this is appropriate; shown to the human reviewer")


class ReleaseArgs(_Args):
    allocation_id: int = Field(ge=1)
    reasoning: str = Field(min_length=3, max_length=600,
                           description="Why releasing is appropriate; shown to the human reviewer")


def get_capacity(db) -> dict:
    total = db.scalar(select(func.coalesce(func.sum(InventoryPool.total_vms), 0)))
    used = db.scalar(select(func.coalesce(func.sum(Allocation.vm_count), 0))
                     .where(Allocation.status == "active"))
    return {"total": int(total), "in_use": int(used), "available": int(total - used)}


def _owns(user, owner_id) -> bool:
    return user.role == "admin" or owner_id == user.id


def _propose(db, user, tool, args: dict, reasoning: str) -> dict:
    p = PendingAction(tool=tool, args=args, reasoning=reasoning, proposed_by=user.id, status="pending")
    db.add(p)
    db.flush()
    audit(db, user.username, "agent", "action_proposed", "pending_action", p.id, {"tool": tool, "args": args})
    return {"pending_action_id": p.id, "status": "pending_approval",
            "note": "NOT executed. A human approver must approve it first."}


def check_capacity(db, user, a: CheckCapacityArgs) -> dict:
    cap = get_capacity(db)
    return {**cap, "requested": a.vm_count, "can_fit": a.vm_count <= cap["available"]}


def create_request(db, user, a: CreateRequestArgs) -> dict:
    lim = ROLE_LIMITS[user.role]
    if a.vm_count > lim["max_vms"]:
        raise ToolError(f"Policy: {user.role} may request at most {lim['max_vms']} VMs.")
    if a.duration_days > lim["max_days"]:
        raise ToolError(f"Policy: {user.role} may request at most {lim['max_days']} days.")
    r = ResourceRequest(requester_id=user.id, vm_count=a.vm_count,
                        duration_days=a.duration_days, purpose=a.purpose, status="draft")
    db.add(r)
    db.flush()
    return {"request_id": r.id, "status": "draft"}


def provision(db, user, a: ProvisionArgs) -> dict:
    r = db.get(ResourceRequest, a.request_id)
    if not r or not _owns(user, r.requester_id):
        raise ToolError("Request not found.")  # same message either way: no existence leak
    if r.status != "draft":
        raise ToolError(f"Request is '{r.status}', only drafts can be submitted.")
    r.status = "awaiting_approval"
    return _propose(db, user, "provision", {"request_id": r.id}, a.reasoning)


def release(db, user, a: ReleaseArgs) -> dict:
    al = db.get(Allocation, a.allocation_id)
    if not al or not _owns(user, al.owner_id):
        raise ToolError("Allocation not found.")
    if al.status != "active":
        raise ToolError("Allocation is not active.")
    for p in db.scalars(select(PendingAction).where(PendingAction.tool == "release",
                                                    PendingAction.status == "pending")):
        if p.args.get("allocation_id") == al.id:
            raise ToolError("A release for this allocation is already pending.")
    return _propose(db, user, "release", {"allocation_id": al.id}, a.reasoning)


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable

    def schema(self) -> dict:
        s = self.args_model.model_json_schema()
        s.pop("title", None)
        return {"name": self.name, "description": self.description, "input_schema": s}


TOOLS = {t.name: t for t in [
    Tool("check_capacity", "Check how many VMs are free in the inventory.", CheckCapacityArgs, check_capacity),
    Tool("create_request", "Create a draft environment request. Does not allocate anything.", CreateRequestArgs, create_request),
    Tool("provision", "Propose provisioning a drafted request. Creates a pending action; a human must approve.", ProvisionArgs, provision),
    Tool("release", "Propose releasing an active allocation. Creates a pending action; a human must approve.", ReleaseArgs, release),
]}