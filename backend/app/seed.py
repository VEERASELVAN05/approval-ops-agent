from datetime import timedelta

from sqlalchemy import select

from .models import Allocation, InventoryPool, User, now
from .security import hash_password

DEMO_USERS = [("alice", "requester"), ("bob", "requester"), ("carol", "approver"), ("admin", "admin")]


def seed(db):
    """Demo data. Passwords are '<username>-pass'. DEV ONLY."""
    for name, role in DEMO_USERS:
        db.add(User(username=name, password_hash=hash_password(f"{name}-pass"), role=role))
    db.add_all([InventoryPool(name="pool-a", total_vms=10), InventoryPool(name="pool-b", total_vms=6)])
    db.flush()
    alice = db.scalar(select(User).where(User.username == "alice"))
    db.add(Allocation(owner_id=alice.id, vm_count=2, starts_at=now(),
                      ends_at=now() + timedelta(days=14), status="active"))  # allocation id 1
    db.commit()