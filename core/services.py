import re
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone
from .models import Report, Match, Event, Draft, User
from .forms import TypeForm, DetailsForm, LocationForm, MatchingForm

@transaction.atomic
def get_or_create_draft(user, report=None, defaults=None):
    # Lock an existing owner row: locking an empty draft query cannot stop
    # another request from inserting its own first draft on PostgreSQL.
    User.objects.select_for_update().get(pk=user.pk)
    draft = Draft.objects.filter(owner=user, report=report).order_by("-updated_at", "-pk").first()
    if draft is not None:
        return draft, False
    return Draft.objects.create(owner=user, report=report, **(defaults or {})), True


def haversine_km(lat1, lng1, lat2, lng2):
    from math import asin, cos, radians, sin, sqrt
    R = 6371
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lng2 - lng1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(a))

def location_score(left, right):
    if left.lat is None or left.lng is None or right.lat is None or right.lng is None:
        return 0
    km = haversine_km(float(left.lat), float(left.lng), float(right.lat), float(right.lng))
    if km < 0.5:
        return 20
    if km < 1:
        return 15
    if km < 2:
        return 10
    if km < 5:
        return 5
    return 0

def validated(data):
    data = dict(data)
    event_date_str = data.get("event_date")
    if event_date_str:
        if not isinstance(event_date_str, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_date_str):
            raise ValidationError("Invalid event date stored in the draft.")
        data["event_date"] = datetime.strptime(event_date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
    result = {}
    for form in [TypeForm(data), DetailsForm(data), LocationForm(data), MatchingForm(data.get("answers", {}), category=data.get("category", ""), selection=data.get("answers", {}))]:
        if not form.is_valid():
            raise ValidationError("Complete and check every step before submitting.")
        if isinstance(form, MatchingForm):
            result["answers"] = form.cleaned_data
        else:
            cleaned = dict(form.cleaned_data)
            cleaned.pop("photo", None)
            cleaned.pop("remove_photo", None)
            result.update(cleaned)
    return result

def score(left, right):
    if left.owner_id == right.owner_id or left.category != right.category or left.kind != "Lost" or right.kind != "Found" or left.status != "Open" or right.status != "Open":
        return None
    excluded = {"contents", "bank_count", "logo"}
    def evidence(report):
        return {k: str(v).strip().casefold() for k, v in report.answers.items()
                if k not in excluded and not k.startswith("bank_") and v not in (None, "", "None", "Other", "Not provided", [], "No")}
    a, b = evidence(left), evidence(right)
    keys = set(a) | set(b)
    agreed = sum(a.get(k) == b.get(k) for k in set(a) & set(b))
    # Bank cards are compared as a set of issuer/suffix pairs, independent of entry order.
    def cards(report):
        result = set()
        for key, value in report.answers.items():
            if key.startswith("bank_") and key.endswith("_issuer") and value:
                prefix = key[:-7]
                issuer = report.answers.get(prefix + "_other", value) if value == "Other" else value
                result.add((str(issuer).strip().casefold(), report.answers.get(prefix + "_suffix", "")))
        return result
    ca, cb = cards(left), cards(right)
    total = len(keys) + len(ca | cb)
    agreed += len(ca & cb)
    stop = {"the", "and", "with", "from", "near", "was", "for", "this", "that", "have", "item", "lost", "found"}
    def tokens(value):
        return set(re.findall(r"[a-z0-9]{3,}", value.casefold())) - stop
    x, y = tokens(left.description), tokens(right.description)
    days = abs((left.event_date - right.event_date).days)
    parts = {
        "Category": 20,
        "Location": location_score(left, right),
        "Date": 15 if days == 0 else 10 if days == 1 else 5 if days <= 3 else 0,
        "Description": round(15 * len(x & y) / len(x | y)) if x | y else 0,
        "Private": round(30 * agreed / total) if total else 0,
    }
    total_score = sum(parts.values())
    return (total_score, parts) if agreed >= 2 and total_score >= 70 else None

def lock_report_workflow():
    """Serialize matching/reservations across PostgreSQL workers until commit.

    SQLite already serializes writes with IMMEDIATE transactions. One advisory
    lock preserves that behaviour for this small app without deadlock-prone
    ordering between competing match pairs. Reads remain concurrent.
    """
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [3272026001])


@transaction.atomic
def recalculate(report):
    lock_report_workflow()
    Match.objects.filter(Q(lost=report) | Q(found=report), state="Possible Match").delete()
    candidates = Report.objects.filter(category=report.category, status="Open", reserved=False).exclude(owner=report.owner).exclude(kind=report.kind)
    for candidate in candidates:
        lost, found = (report, candidate) if report.kind == "Lost" else (candidate, report)
        result = score(lost, found)
        if result:
            match, _ = Match.objects.get_or_create(
                lost=lost, found=found,
                defaults={"score": result[0], "breakdown": result[1]},
            )
            match.score, match.breakdown = result
            match.save(update_fields=["score", "breakdown"])

@transaction.atomic
def publish(draft, user):
    lock_report_workflow()
    try:
        draft = Draft.objects.select_for_update().get(pk=draft.pk, owner=user)
    except Draft.DoesNotExist:
        raise ValidationError("This draft has already been submitted or removed.")
    data = validated(draft.data)
    uploaded_photo = draft.photo.name if draft.photo else ""
    remove_photo = bool(draft.data.get("remove_photo"))
    if draft.report_id:
        report = Report.objects.get(pk=draft.report_id, owner=user)
        if report.status != "Open" or report.reserved:
            raise ValidationError("Editing is locked because this report is closed or has a handover.")
        previous_photo = report.photo.name
        if uploaded_photo:
            report.photo.name = uploaded_photo
        elif remove_photo:
            report.photo.name = ""
        for key, value in data.items():
            setattr(report, key, value)
        report.save()
        if previous_photo and previous_photo != report.photo.name:
            storage = report.photo.storage
            transaction.on_commit(lambda: storage.delete(previous_photo))
    else:
        if uploaded_photo:
            data["photo"] = uploaded_photo
        report = Report.objects.create(owner=user, **data)
    Event.objects.create(report=report, actor=user, text="Report updated" if draft.report_id else "Report created")
    recalculate(report)
    draft.delete()
    return report

@transaction.atomic
def transition(pk, user, action, meeting=None):
    lock_report_workflow()
    match = Match.objects.select_related("lost", "found").get(pk=pk)
    if user.pk not in (match.lost.owner_id, match.found.owner_id):
        raise ValidationError("Only participants can change this match.")
    reports = Report.objects.filter(pk__in=[match.lost_id, match.found_id])
    if any(r.status != "Open" for r in reports):
        raise ValidationError("These reports are no longer open.")
    if action == "propose" and match.state == "Possible Match":
        if reports.filter(reserved=True).exists():
            raise ValidationError("A handover already reserves one of these reports.")
        if not meeting or meeting.get("meeting_place") is None or meeting.get("meeting_at") is None:
            raise ValidationError("Provide a meeting place and time.")
        if meeting["meeting_at"] <= timezone.now():
            raise ValidationError("Choose a future meeting.")
        reports.update(reserved=True)
        match.proposer = user
        match.meeting_place = meeting["meeting_place"]
        match.meeting_at = meeting["meeting_at"]
        match.state = "Handover Proposed"
    elif action == "accept" and match.state == "Handover Proposed" and match.proposer_id != user.pk:
        if match.meeting_at <= timezone.now():
            raise ValidationError("This meeting time has passed. Reject the proposal.")
        match.state = "Handover Scheduled"
    elif action == "reject" and match.state in ("Possible Match", "Handover Proposed"):
        if match.state == "Handover Proposed":
            reports.update(reserved=False)
        match.state = "Rejected"
        match.rejected_by = user
    elif action == "restore" and match.state == "Rejected":
        if match.rejected_by_id != user.pk:
            raise ValidationError("Only the participant who dismissed this suggestion can restore it.")
        if reports.filter(reserved=True).exists():
            raise ValidationError("This suggestion cannot be restored while a handover is in progress.")
        result = score(match.lost, match.found)
        if not result:
            raise ValidationError("This suggestion no longer meets the matching rules.")
        match.score, match.breakdown = result
        match.state = "Possible Match"
        match.rejected_by = None
    elif action == "returned" and match.state == "Handover Scheduled":
        if match.meeting_at > timezone.now():
            raise ValidationError("Confirm return at or after the meeting time.")
        reports.update(status="Returned", reserved=False)
        Match.objects.filter(Q(lost_id__in=reports.values("pk")) | Q(found_id__in=reports.values("pk")), state="Possible Match").exclude(pk=match.pk).update(state="Rejected")
        match.state = "Returned"
    else:
        raise ValidationError("That action is unavailable in this state.")
    match.save()
    for report in reports:
        Event.objects.create(report=report, actor=user, text=match.state)

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
