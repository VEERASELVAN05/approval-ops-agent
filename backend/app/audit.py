import logging

from .models import AuditLog

log = logging.getLogger("audit")


def audit(db, actor, actor_type, event, entity=None, entity_id=None, details=None, trace_id=None):
    """Adds an audit row (caller commits) and emits a structured log line."""
    db.add(AuditLog(actor=actor, actor_type=actor_type, event=event, entity=entity,
                    entity_id=entity_id, details=details, trace_id=trace_id))
    log.info(event, extra={"fields": {"actor": actor, "actor_type": actor_type, "entity": entity,
                                      "entity_id": entity_id, "trace_id": trace_id, "details": details}})