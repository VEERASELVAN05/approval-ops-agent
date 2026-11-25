from app.agent.runner import dispatch
from app.models import Allocation, ResourceRequest


def propose_provision(db, get_user, who="alice", vms=4):
    u = get_user(who)

    out, is_error = dispatch(
        db, u, "create_request",
        {
            "vm_count": vms,
            "duration_days": 14,
            "purpose": "test env"
        },
        "t"
    )

    assert not is_error, f"create_request failed: {out}"
    assert "request_id" in out, f"Missing request_id: {out}"

    out, is_error = dispatch(
        db, u, "provision",
        {
            "request_id": out["request_id"],
            "reasoning": "Provisioning required for testing"
        },
        "t"
    )

    if is_error:
        print("PROVISION VALIDATION ERROR:", out)

    assert not is_error, f"provision failed: {out}"
    assert "pending_action_id" in out, f"Missing pending_action_id: {out}"

    return out["pending_action_id"]


def decide(client, headers, aid, decision="approve"):
    return client.post(f"/api/approvals/{aid}/decision", json={"decision": decision}, headers=headers)


def test_requester_cannot_access_approvals(client, login):
    assert client.get("/api/approvals", headers=login("alice")).status_code == 403
    assert client.get("/api/approvals").status_code == 401


def test_approve_executes(client, login, db, get_user):
    aid = propose_provision(db, get_user)
    r = decide(client, login("carol"), aid)
    assert r.status_code == 200 and r.json()["status"] == "executed"
    assert db.query(Allocation).count() == 2
    assert db.get(ResourceRequest, 1).status == "provisioned"


def test_reject_does_not_execute(client, login, db, get_user):
    aid = propose_provision(db, get_user)
    assert decide(client, login("carol"), aid, "reject").json()["status"] == "rejected"
    assert db.query(Allocation).count() == 1


def test_cannot_decide_own_action(client, login, db, get_user):
    aid = propose_provision(db, get_user, who="admin")
    assert decide(client, login("admin"), aid).status_code == 403


def test_double_decision_conflict(client, login, db, get_user):
    aid = propose_provision(db, get_user)
    assert decide(client, login("carol"), aid).status_code == 200
    assert decide(client, login("carol"), aid).status_code == 409


def test_capacity_rechecked_at_approval_time(client, login, db, get_user):
    aid = propose_provision(db, get_user, vms=8)
    from app.models import now
    db.add(Allocation(owner_id=2, vm_count=10, starts_at=now(), ends_at=now(), status="active"))
    db.commit()                                    # someone else grabbed capacity meanwhile
    r = decide(client, login("carol"), aid)
    assert r.json()["status"] == "failed" and "free" in r.json()["result"]["error"]


def test_invalid_decision_422(client, login, db, get_user):
    aid = propose_provision(db, get_user)
    r = client.post(f"/api/approvals/{aid}/decision", json={"decision": "yolo"}, headers=login("carol"))
    assert r.status_code == 422


def test_unknown_action_404(client, login):
    assert decide(client, login("carol"), 999).status_code == 404