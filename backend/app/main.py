import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .logging_setup import setup_logging
from .models import User
from .routers import agent, approvals, auth, metrics
from .seed import seed

log = logging.getLogger("http")


@asynccontextmanager
async def lifespan(app):
    setup_logging()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User.id).limit(1)):
            seed(db)
    yield


app = FastAPI(title="Approval-Gated Ops Agent", lifespan=lifespan)


@app.middleware("http")
async def access_log(request: Request, call_next):
    rid, t0 = uuid.uuid4().hex[:12], time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled_error", extra={"fields": {"request_id": rid, "path": request.url.path}})
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)
    response.headers["X-Request-ID"] = rid
    log.info("http_request", extra={"fields": {"request_id": rid, "method": request.method,
             "path": request.url.path, "status": response.status_code,
             "ms": round((time.perf_counter() - t0) * 1000, 1)}})
    return response


@app.get("/api/health")
def health():
    return {"status": "ok"}


for r in (auth.router, agent.router, approvals.router, metrics.router):
    app.include_router(r, prefix="/api")