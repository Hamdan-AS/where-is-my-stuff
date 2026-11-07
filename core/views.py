from datetime import date
from django.core.files.base import ContentFile
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import DatabaseError, transaction
from django.db.models import Q, Case, When, Value, IntegerField
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Report, Draft, Match, QRLabel
from .forms import EmailLogin, Registration, TypeForm, DetailsForm, LocationForm, MatchingForm, MeetingForm, QRLabelForm, BAD_CHARS
from .services import publish, transition, moderate, get_or_create_draft
from .qr import generate_qr_png
from .images import normalize_photo
from .qr_labels import new_label_token, token_digest, expiry_after_months, make_label_qr

class AccountLoginView(LoginView):
    template_name = "auth.html"
    authentication_form = EmailLogin

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(None if form.cleaned_data["remember_me"] else 0)
        return response

    def get_success_url(self):
        redirect_url = super().get_success_url()
        if redirect_url != "/":
            return redirect_url
        if not Report.objects.filter(owner=self.request.user).exists():
            draft = Draft.objects.filter(owner=self.request.user, report__isnull=True).order_by("-updated_at").first()
            if draft:
                return reverse("draft", args=[draft.pk])
            return reverse("create")
        return redirect_url

def register(request):
    form = Registration(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("create")
    return render(request, "auth.html", {"form": form, "register": True})

@login_required
def dashboard(request):
    all_reports = Report.objects.filter(owner=request.user).exclude(status="Removed")
    if not all_reports.exists():
        draft = Draft.objects.filter(owner=request.user, report__isnull=True).order_by("-updated_at").first()
        if draft:
            return redirect("draft", pk=draft.pk)
        return redirect("create")
    reports = all_reports.filter(status="Open").order_by("-reserved", "-created_at", "-pk")[:3]
    match_base = Match.objects.filter(
        Q(lost__owner=request.user) | Q(found__owner=request.user)
    ).select_related("lost", "found")
    matches = match_base.filter(
        state__in=["Possible Match", "Handover Proposed", "Handover Scheduled"]
    ).exclude(
        state="Possible Match", lost__reserved=True
    ).exclude(
        state="Possible Match", found__reserved=True
    ).annotate(
        state_order=Case(
            When(state="Handover Proposed", proposer=request.user, then=Value(2)),
            When(state="Handover Proposed", then=Value(0)),
            When(state="Handover Scheduled", then=Value(1)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by("state_order", "-pk")
    match_list = list(matches)
    hero_match = match_list[0] if match_list else None
    open_count = all_reports.filter(status="Open").count()
    returned_count = all_reports.filter(status="Returned").count()
    possible_count = match_base.filter(state="Possible Match").exclude(
        lost__reserved=True
    ).exclude(found__reserved=True).count()
    handover_count = match_base.filter(state__in=["Handover Proposed", "Handover Scheduled"]).count()
    returned_reports = all_reports.filter(status="Returned").order_by("-created_at", "-pk")[:10]
    return render(request, "dashboard.html", {
        "reports": reports,
        "hero": hero_match,
        "other_matches": match_list[1:],
        "drafts": Draft.objects.filter(owner=request.user).order_by("-updated_at"),
        "returned_reports": returned_reports,
        "total_count": all_reports.count(),
        "open_count": open_count,
        "returned_count": returned_count,
        "possible_count": possible_count,
        "handover_count": handover_count,
    })

@login_required
def report_history(request):
    reports = Report.objects.filter(owner=request.user).exclude(status="Removed")
    search = request.GET.get("q", "").strip()
    if BAD_CHARS.search(search):
        return HttpResponse("Remove special or invisible characters from your search.", status=400)
    status_filter = request.GET.get("status", "").strip()
    kind_filter = request.GET.get("kind", "").strip()
    if search:
        reports = reports.filter(
            Q(title__icontains=search) | Q(location__icontains=search)
        )
    if status_filter in {"Open", "Returned", "Closed"}:
        reports = reports.filter(status=status_filter)
    if kind_filter in {"Lost", "Found"}:
        reports = reports.filter(kind=kind_filter)
    page_obj = Paginator(reports.order_by("-created_at", "-pk"), 10).get_page(request.GET.get("page"))
    return render(request, "reports.html", {
        "page_obj": page_obj,
        "search": search,
        "status_filter": status_filter,
        "kind_filter": kind_filter,
    })

def posted_selection(post):
    data = post.dict()
    data["contents"] = post.getlist("contents")
    return data

@login_required
def wizard(request, pk=None):
    if pk is None:
        existing, created = get_or_create_draft(request.user)
        if not created:
            if request.method == "POST" and request.POST.get("action") == "new":
                if (request.POST.get("confirm_discard") != "yes" or
                        request.POST.get("discard_draft_id") != str(existing.pk)):
                    discard_error = "Confirm that you want to discard this saved draft before starting a new report."
                    return render(request, "resume_draft.html", {"draft": existing, "discard_error": discard_error})
                previous_photo = existing.photo
                existing.delete()
                if previous_photo:
                    previous_photo.delete(save=False)
                messages.info(request, "Previous draft discarded.")
                return redirect("create")
            return render(request, "resume_draft.html", {"draft": existing})
        return redirect("draft", pk=existing.pk)
    draft = get_object_or_404(Draft, pk=pk, owner=request.user)
    if draft.report_id and (draft.report.status != "Open" or draft.report.reserved):
        messages.error(request, "Editing is locked while a handover is in progress or the report is closed.")
        return redirect("report", pk=draft.report_id)
    try:
        step = max(1, min(5, int(request.GET.get("step", "1"))))
    except ValueError:
        step = 1
    data = draft.data
    if step > 1 and not all(k in data for k in ("kind", "title", "category", "event_date")):
        return redirect(request.path + "?step=1")
    if step > 2 and "description" not in data:
        return redirect(request.path + "?step=2")
    if step > 3 and not all(k in data for k in ("location", "lat", "lng", "location_detail")):
        return redirect(request.path + "?step=3")
    if step > 4 and "answers" not in data:
        return redirect(request.path + "?step=4")
    # Location edits need the saved place and coordinates. Private answers are
    # only the initial values for the Matching step.
    initial = data.get("answers", {}) if step == 4 else data
    if step == 1 and data.get("event_date"):
        try:
            initial = {**data, "event_date": date.fromisoformat(data["event_date"])}
        except (TypeError, ValueError):
            # A tampered or legacy draft can hold a date the wizard did not
            # write. Render the step with blank initial data rather than 500.
            initial = {**data, "event_date": None}
    form = None
    if step < 5:
        klass = {1: TypeForm, 2: DetailsForm, 3: LocationForm, 4: MatchingForm}[step]
        kwargs = {"category": data["category"], "selection": posted_selection(request.POST) if request.method == "POST" else initial} if step == 4 else {}
        # Convert saved ISO date only at the storage boundary.
        bound = request.POST if request.method == "POST" else None
        form = klass(bound, request.FILES or None, initial=initial, **kwargs)
        if request.method == "POST":
            if step == 4 and request.POST.get("action") == "refresh":
                form = klass(initial=posted_selection(request.POST), **kwargs)
            elif form.is_valid():
                cleaned = form.cleaned_data
                uploaded_photo = cleaned.pop("photo", None) if step == 2 else None
                remove_photo = cleaned.pop("remove_photo", False) if step == 2 else False
                if step == 1:
                    cleaned["event_date"] = cleaned["event_date"].isoformat()
                    if data.get("category") != cleaned["category"]:
                        data.pop("answers", None)
                if step == 4:
                    data["answers"] = cleaned
                else:
                    cleaned = dict(cleaned)
                    for key in ("lat", "lng"):
                        if cleaned.get(key) is not None:
                            cleaned[key] = str(cleaned[key])
                    data.update(cleaned)
                if step == 2:
                    if uploaded_photo:
                        old_photo = draft.photo.name
                        draft.photo.save("item-photo.jpg", normalize_photo(uploaded_photo), save=False)
                        data.pop("remove_photo", None)
                        if old_photo and old_photo != draft.photo.name:
                            draft.photo.storage.delete(old_photo)
                    elif remove_photo:
                        data["remove_photo"] = True
                        if draft.photo:
                            draft.photo.delete(save=False)
                draft.data = data
                try:
                    # Never insert a stale draft that another tab published or discarded.
                    draft.save(update_fields=["data", "photo", "updated_at"])
                except DatabaseError:
                    if Draft.objects.filter(pk=draft.pk, owner=request.user).exists():
                        raise
                    messages.info(request, "This draft is no longer available. Check your reports before starting again.")
                    return redirect("dashboard")
                messages.success(request, "Draft saved to your account.")
                return redirect(request.path + f"?step={step + 1}")
    elif request.method == "POST":
        try:
            with transaction.atomic():
                draft = get_object_or_404(Draft, pk=draft.pk, owner=request.user)
                report = publish(draft, request.user)
            match_count = Match.objects.filter(
                Q(lost=report) | Q(found=report), state="Possible Match"
            ).count()
            if match_count:
                messages.success(request, f"Report saved. {match_count} possible match{'es' if match_count != 1 else ''} found.")
            else:
                messages.success(request, "Report saved. No possible matches yet.")
            return redirect(reverse("dashboard") + f"?new={report.pk}#report-{report.pk}")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    duplicate = Report.objects.filter(owner=request.user, status="Open", title__iexact=data.get("title", ""), kind=data.get("kind", ""), category=data.get("category", "")).exclude(pk=draft.report_id).exists() if step == 5 else False
    try:
        display_date = date.fromisoformat(data["event_date"]).strftime("%d-%m-%Y") if data.get("event_date") else ""
    except (TypeError, ValueError):
        display_date = ""
    has_saved_photo = bool(draft.photo or (draft.report_id and draft.report.photo))
    item_phrase = {
        "Wallet / Purse": "a wallet or purse", "Cards / IDs": "a card or ID",
        "Keys": "a set of keys", "Electronics": "an electronic item",
        "Bag": "a bag", "Documents": "a document", "Cash / Money": "some cash",
        "Other": "an item",
    }.get(data.get("category"), "an item")
    report_summary = f"You {data['kind'].lower()} {item_phrase}." if data.get("kind") in {"Lost", "Found"} else ""
    return render(request, "wizard.html", {"form": form, "step": step, "previous": step - 1, "draft": draft, "data": data, "report_summary": report_summary, "display_date": display_date, "duplicate": duplicate, "current_photo": has_saved_photo and not data.get("remove_photo"), "steps": [(1, "Type"), (2, "Details"), (3, "Location"), (4, "Matching"), (5, "Review")]})

@login_required
def report_detail(request, pk):
    report = get_object_or_404(Report, pk=pk, owner=request.user)
    related_matches = Match.objects.filter(Q(lost=report) | Q(found=report)).select_related("lost", "found").exclude(state="Rejected").order_by("-pk")
    return render(request, "report.html", {"report": report, "events": report.event_set.order_by("-created_at"), "related_matches": related_matches})


@login_required
def report_photo(request, pk):
    report = get_object_or_404(Report, pk=pk)
    is_owner = report.owner_id == request.user.pk
    is_match_participant = Match.objects.filter(
        Q(lost=report, found__owner=request.user) |
        Q(found=report, lost__owner=request.user)
    ).exists()
    if not (is_owner or is_match_participant) or not report.photo:
        raise Http404
    try:
        photo = report.photo.open("rb")
    except FileNotFoundError as exc:
        raise Http404("Photo is no longer available.") from exc
    response = FileResponse(photo, content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def draft_photo(request, pk):
    draft = get_object_or_404(Draft, pk=pk, owner=request.user)
    if not draft.photo:
        raise Http404
    try:
        photo = draft.photo.open("rb")
    except FileNotFoundError as exc:
        raise Http404("Photo is no longer available.") from exc
    response = FileResponse(photo, content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def qr_labels(request):
    form = QRLabelForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        token = new_label_token()
        label = QRLabel.objects.create(
            owner=request.user,
            item_name=form.cleaned_data["item_name"],
            contact_phone=form.cleaned_data["contact_phone"],
            token_hash=token_digest(token),
            expires_at=expiry_after_months(timezone.now()),
        )
        qr_url = request.build_absolute_uri(reverse("qr-label-public", args=[token]))
        try:
            label.qr_image.save(f"label-{label.pk}.png", ContentFile(make_label_qr(qr_url).read()), save=True)
        except Exception:
            label.delete()
            raise
        messages.success(request, "QR label created. Download it, print it, and attach it to your item.")
        return redirect("qr-labels")
    return render(request, "qr_labels.html", {"form": form, "labels": QRLabel.objects.filter(owner=request.user)})


@login_required
@require_POST
def reactivate_qr_label(request, pk):
    label = get_object_or_404(QRLabel, pk=pk, owner=request.user)
    label.expires_at = expiry_after_months(timezone.now())
    label.revoked = False
    label.save(update_fields=["expires_at", "revoked"])
    messages.success(request, "Label reactivated. The same printed QR code works again for six months.")
    return redirect("qr-labels")


@login_required
@require_POST
def deactivate_qr_label(request, pk):
    label = get_object_or_404(QRLabel, pk=pk, owner=request.user)
    label.revoked = True
    label.save(update_fields=["revoked"])
    messages.success(request, "Label deactivated. Scanning it will no longer show your phone number.")
    return redirect("qr-labels")


@login_required
def qr_label_image(request, pk):
    label = get_object_or_404(QRLabel, pk=pk, owner=request.user)
    if not label.qr_image:
        raise Http404("QR image is no longer available.")
    try:
        qr_image = label.qr_image.open("rb")
    except FileNotFoundError as exc:
        raise Http404("QR image is no longer available.") from exc
    response = FileResponse(
        qr_image, content_type="image/png",
        as_attachment=request.GET.get("download") == "1",
        filename=f"item-qr-{label.pk}.png",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def qr_label_public(request, token):
    label = get_object_or_404(QRLabel, token_hash=token_digest(token))
    response = render(request, "qr_label_public.html", {"label": label, "active": label.is_active})
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response

@login_required
@require_POST
def edit_report(request, pk):
    report = get_object_or_404(Report, pk=pk, owner=request.user)
    if report.status != "Open" or report.reserved:
        messages.error(request, "This report is locked.")
        return redirect("report", pk=pk)
    data = {key: getattr(report, key) for key in ["kind", "title", "category", "description", "location", "lat", "lng", "location_detail", "contact", "answers"]}
    for key in ("lat", "lng"):
        if data[key] is not None:
            data[key] = str(data[key])
    data["event_date"] = report.event_date.isoformat()
    draft, _ = get_or_create_draft(request.user, report=report, defaults={"data": data})
    return redirect("draft", pk=draft.pk)

@login_required
def match_detail(request, pk):
    match = get_object_or_404(Match.objects.select_related("lost", "found").filter(Q(lost__owner=request.user) | Q(found__owner=request.user)), pk=pk)
    form = MeetingForm(request.POST or None)
    if request.method == "POST":
        action = request.POST.get("action")
        propose_invalid = action == "propose" and not form.is_valid()
        if not propose_invalid:
            try:
                meeting = form.cleaned_data if action == "propose" else None
                transition(pk, request.user, action, meeting)
                if action == "reject":
                    messages.warning(request, "Suggestion dismissed. You can restore it if this was accidental.")
                elif action == "restore":
                    messages.success(request, "Suggestion restored and checked again.")
                return redirect("match", pk=pk)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
    return render(request, "match.html", {"match": match, "form": form, "contacts": match.state in ("Handover Scheduled", "Returned"), "can_restore": match.state == "Rejected" and match.rejected_by_id == request.user.pk})

@login_required
def management(request):
    if not request.user.is_staff:
        raise PermissionDenied
    if request.method == "POST":
        try:
            report_id = int(request.POST.get("report", ""))
            if not 0 < report_id <= 9223372036854775807:
                raise ValueError
        except (ValueError, TypeError):
            return HttpResponse("Choose a valid report.", status=400)
        report = get_object_or_404(Report, pk=report_id)
        try:
            moderate(report, request.user, request.POST.get("action"))
            messages.success(request, "Report updated.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("management")
    return render(request, "management.html", {"reports": Report.objects.exclude(status="Removed").order_by("-pk")})

def report_qr_image(request, public_id):
    report = get_object_or_404(Report, public_id=public_id)
    url = request.build_absolute_uri(reverse("report-found", args=[report.public_id]))
    response = FileResponse(
        generate_qr_png(url),
        content_type="image/png",
        as_attachment=request.GET.get("download") == "1",
        filename="report-qr.png",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response

@login_required
def report_found(request, public_id):
    lost_report = get_object_or_404(Report, public_id=public_id)
    if lost_report.owner_id == request.user.pk:
        messages.info(request, "This QR belongs to your own report; only a finder scans it.")
        return redirect("report", pk=lost_report.pk)
    if lost_report.status != "Open" or lost_report.reserved:
        return render(request, "closed_notice.html", {"report": lost_report})
    # Older or overlapping requests can leave multiple unfinished drafts.
    # Resume the newest rather than failing with MultipleObjectsReturned.
    draft, _ = get_or_create_draft(request.user)
    draft.data.update({
        "kind": "Found",
        "category": lost_report.category,
        "title": lost_report.title,
        "location": lost_report.location,
        "event_date": timezone.localdate().isoformat(),
    })
    # The place name is a coarse hint the finder can confirm, but the exact
    # coordinates are where the owner thinks the item was lost, not where the
    # finder recovered it. Carrying them over would publish the owner's drop
    # point as the finder's, and location_score would award the pair 20 points
    # for a position that was never independently observed.
    for key in ("description", "location_detail", "contact", "answers", "lat", "lng"):
        draft.data.pop(key, None)
    draft.save(update_fields=["data"])
    return redirect(reverse("draft", args=[draft.pk]) + "?step=3")
