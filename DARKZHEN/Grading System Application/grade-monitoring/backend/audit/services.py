def record_audit(actor, action, entity, entity_id=None, old_values=None, new_values=None):
    from .models import AuditLog

    return AuditLog.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else "",
        old_values=old_values,
        new_values=new_values,
    )
