from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from ..models import Match, Event
from .workflow import lock_report_workflow

@transaction.atomic
def moderate(report, user, action):
    if not user.is_staff or action not in ("close", "remove"):
        raise ValidationError("Moderator access required.")
    lock_report_workflow()
    report.refresh_from_db()
    if report.reserved or report.status != "Open":
        raise ValidationError("Only open reports without a handover can be moderated.")
    report.status = "Closed" if action == "close" else "Removed"
    report.save()
    Match.objects.filter(Q(lost=report) | Q(found=report), state="Possible Match").update(state="Rejected")
    Event.objects.create(report=report, actor=user, text=report.status + " by management")
