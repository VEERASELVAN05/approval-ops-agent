import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select

from ..agent.llm import get_llm
from ..agent.runner import run_agent
from ..db import get_db
from ..models import PendingAction
from ..schemas import ChatIn, ChatOut
from ..security import get_current_user
from ..serializers import action_out

router = APIRouter(tags=["agent"])


@router.post("/agent/chat", response_model=ChatOut)
def chat(body: ChatIn, db=Depends(get_db), user=Depends(get_current_user), llm=Depends(get_llm)):
    trace_id = uuid.uuid4().hex
    r = run_agent(db, user, body.message, llm, trace_id)
    return ChatOut(reply=r.reply, ok=r.ok, pending_action_ids=r.pending_action_ids, trace_id=trace_id)


@router.get("/actions/mine")
def my_actions(db=Depends(get_db), user=Depends(get_current_user)):
    rows = db.scalars(select(PendingAction).where(PendingAction.proposed_by == user.id)
                      .order_by(PendingAction.id.desc()).limit(20))
    return [action_out(db, a) for a in rows]