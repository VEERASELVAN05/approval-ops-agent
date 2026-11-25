from datetime import timedelta

from sqlalchemy import select

from ..models import Allocation, InventoryPool, ResourceRequest, now
from .tools import ToolError, get_capacity


def execute_action(db, action) -> dict:
    """Fake 'infrastructure'. Re-validates everything at approval time, because the world
    may have changed since the proposal. All ToolErrors are raised BEFORE any write."""
    if action.tool == "provision":
        r = db.get(ResourceRequest, action.args["request_id"])
        if r is None or r.status != "awaiting_approval":
            raise ToolError("Request is no longer awaiting approval.")
        db.execute(select(InventoryPool).with_for_update()).all()  # row lock on Postgres
        free = get_capacity(db)["available"]
        if r.vm_count > free:
            raise ToolError(f"Only {free} VMs are free now; {r.vm_count} requested.")
        start = now()
        al = Allocation(request_id=r.id, owner_id=r.requester_id, vm_count=r.vm_count,
                        starts_at=start, ends_at=start + timedelta(days=r.duration_days), status="active")
        db.add(al)
        db.flush()
        r.status = "provisioned"
        return {"allocation_id": al.id, "vms": [f"fake-vm-{al.id}-{i + 1}" for i in range(r.vm_count)]}

    if action.tool == "release":
        al = db.get(Allocation, action.args["allocation_id"])
        if al is None or al.status != "active":
            raise ToolError("Allocation is not active.")
        al.status = "released"
        return {"allocation_id": al.id, "released_vms": al.vm_count}

    raise ToolError(f"Unknown tool '{action.tool}'")