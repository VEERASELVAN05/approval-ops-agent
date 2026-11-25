import pytest
from sqlalchemy import func, select

from app.agent.runner import dispatch
from app.models import Allocation, PendingAction


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_provision_only_creates_pending_action(db, get_user):
    alice = get_user("alice")
    out, err = dispatch(db, alice, "create_request", {"vm_count": 4, "duration_days": 14, "purpose": "load test"}, "t")
    assert not err
    before = count(db, Allocation)
    out, err = dispatch(db, alice, "provision", {"request_id": out["request_id"], "reasoning": "fits"}, "t")
    assert not err and out["status"] == "pending_approval"
    assert count(db, Allocation) == before          # nothing provisioned
    assert count(db, PendingAction) == 1


@pytest.mark.parametrize("args", [
    {"vm_count": 9, "duration_days": 14, "purpose": "too many"},
    {"vm_count": 4, "duration_days": 31, "purpose": "too long"},
])
def test_requester_policy_limits(db, get_user, args):
    out, err = dispatch(db, get_user("alice"), "create_request", args, "t")
    assert err and "Policy" in out["error"]


@pytest.mark.parametrize("args", [
    {"vm_count": -1, "duration_days": 5, "purpose": "negative"},
    {"vm_count": 0, "duration_days": 5, "purpose": "zero"},
    {"vm_count": "four", "duration_days": 5, "purpose": "string"},
    {"vm_count": 2, "duration_days": 5, "purpose": "extra", "user_id": 99},   # smuggled field
])
def test_invalid_args_rejected(db, get_user, args):
    out, err = dispatch(db, get_user("alice"), "create_request", args, "t")
    assert err and out["error"] == "Invalid arguments"


def test_non_dict_args_rejected(db, get_user):
    out, err = dispatch(db, get_user("alice"), "create_request", None, "t")
    assert err


def test_unknown_tool(db, get_user):
    out, err = dispatch(db, get_user("alice"), "drop_database", {}, "t")
    assert err and "Unknown tool" in out["error"]


def test_approver_cannot_provision(db, get_user):
    out, err = dispatch(db, get_user("carol"), "provision", {"request_id": 1, "reasoning": "please"}, "t")
    assert err and "not allowed" in out["error"]


def test_cannot_release_someone_elses_allocation(db, get_user):
    out, err = dispatch(db, get_user("bob"), "release", {"allocation_id": 1, "reasoning": "mine"}, "t")
    assert err and count(db, PendingAction) == 0
    out, err = dispatch(db, get_user("alice"), "release", {"allocation_id": 1, "reasoning": "done"}, "t")
    assert not err and count(db, PendingAction) == 1


def test_duplicate_release_blocked(db, get_user):
    alice = get_user("alice")
    dispatch(db, alice, "release", {"allocation_id": 1, "reasoning": "done"}, "t")
    out, err = dispatch(db, alice, "release", {"allocation_id": 1, "reasoning": "again"}, "t")
    assert err