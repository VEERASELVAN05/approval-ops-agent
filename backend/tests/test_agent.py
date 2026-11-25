from app.agent.llm import ScriptedLLM, get_llm
from app.main import app
from app.models import AuditLog


def text(t):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": t}]}


def use(i, name, inp):
    return {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]}


def chat(client, headers, llm, msg="I need 4 VMs for two weeks"):
    app.dependency_overrides[get_llm] = lambda: llm
    return client.post("/api/agent/chat", json={"message": msg}, headers=headers)


def test_happy_path(client, login):
    llm = ScriptedLLM([
        use("1", "check_capacity", {"vm_count": 4, "duration_days": 14}),
        use("2", "create_request", {"vm_count": 4, "duration_days": 14, "purpose": "test env"}),
        use("3", "provision", {"request_id": 1, "reasoning": "4 VMs fit in capacity"}),
        text("Submitted for approval."),
    ])
    r = chat(client, login("alice"), llm)
    assert r.status_code == 200 and r.json()["ok"] and len(r.json()["pending_action_ids"]) == 1


def test_llm_outage_is_graceful(client, login):
    class Boom:
        def complete(self, *a):
            raise RuntimeError("API down")
    r = chat(client, login("alice"), Boom())
    assert r.status_code == 200 and r.json()["ok"] is False


def test_garbage_tool_call_does_not_crash(client, login, db):
    llm = ScriptedLLM([use("1", "drop_database", {"confirm": True}), text("Sorry, I can't do that.")])
    r = chat(client, login("alice"), llm)
    assert r.status_code == 200
    assert db.query(AuditLog).filter_by(event="tool_unknown").count() == 1


def test_step_limit(client, login):
    llm = ScriptedLLM([use(str(i), "check_capacity", {"vm_count": 1, "duration_days": 1}) for i in range(20)])
    r = chat(client, login("alice"), llm)
    assert r.json()["ok"] is False


def test_approver_is_not_even_shown_risky_tools(client, login):
    llm = ScriptedLLM([text("ok")])
    chat(client, login("carol"), llm)
    assert llm.last_tools == ["check_capacity"]


def test_message_validation(client, login):
    r = client.post("/api/agent/chat", json={"message": "x" * 5000}, headers=login("alice"))
    assert r.status_code == 422
    assert client.post("/api/agent/chat", json={"message": ""}, headers=login("alice")).status_code == 422


def test_audit_trail_records_run(client, login, db):
    chat(client, login("alice"), ScriptedLLM([text("hello")]))
    events = {e.event for e in db.query(AuditLog).all()}
    assert {"agent_request", "agent_reply", "login_ok"} <= events