from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..audit import audit
from ..db import get_db
from ..models import User
from ..schemas import LoginIn, TokenOut, UserOut
from ..security import DUMMY_HASH, create_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db=Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok:
        audit(db, body.username[:50], "user", "login_failed")
        db.commit()
        raise HTTPException(401, "Invalid credentials")
    audit(db, user.username, "user", "login_ok")
    db.commit()
    return TokenOut(access_token=create_token(user))


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return UserOut(id=user.id, username=user.username, role=user.role)