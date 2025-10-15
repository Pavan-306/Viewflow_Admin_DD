# ticketflow/views.py
from django import forms
from django.core.mail import EmailMultiAlternatives
from django.views.generic import ListView, RedirectView
from viewflow.workflow.flow.views import CreateProcessView, UpdateProcessView

from .models import (
    TicketProcess,
    Form as FormModel,
    FormEntry,
    FormEntryValue,
    FormField,
)
from .forms import add_fields_to_form, ApprovalForm


# ---- Role display mapping ----
ROLE_DISPLAY = {
    "user": "Risk Representative",
    "dev": "Risk Champion",
    "ba": "Risk Approver",
    "pm": "CRO",
}


def _values_map_for_entry(entry: FormEntry) -> dict[int, str]:
    out = {}
    for v in entry.values.all():
        out[v.field_id] = v.value_text or (v.value_file.name if v.value_file else "")
    return out


def build_ticket_summary_html(process: TicketProcess) -> str:
    if not process.entry:
        return "<p><em>No data yet</em></p>"

    values_map = _values_map_for_entry(process.entry)
    rows = []
    for ff in process.form.fields.all():
        val = values_map.get(ff.id, "")
        rows.append(
            f"<tr><th style='text-align:left;padding:4px 8px'>{ff.label}</th>"
            f"<td style='padding:4px 8px'>{val}</td></tr>"
        )
    return (
        "<table border='1' cellpadding='0' cellspacing='0' style='border-collapse:collapse'>"
        + "".join(rows)
        + "</table>"
    )


def _update_entry_values_for_role(
    entry: FormEntry, form_obj: FormModel, cleaned_data: dict, files, role: str
):
    for ff in form_obj.fields.filter(role=role):
        key = str(ff.id)
        if ff.field_type == FormField.FILE:
            file_obj = (files or {}).get(key)
            if file_obj:
                v, _ = FormEntryValue.objects.get_or_create(entry=entry, field=ff)
                v.value_text = ""
                v.value_file = file_obj
                v.save()
        else:
            val = cleaned_data.get(key, "")
            v, _ = FormEntryValue.objects.get_or_create(entry=entry, field=ff)
            v.value_file = None
            v.value_text = str(val) if val is not None else ""
            v.save()


def _snapshot_from_entry(entry: FormEntry) -> dict:
    snap = {}
    for ff in entry.form.fields.all():
        try:
            v = entry.values.get(field=ff)
            snap[ff.label] = v.value_text or (v.value_file.name if v.value_file else "")
        except FormEntryValue.DoesNotExist:
            snap[ff.label] = ""
    return snap


def send_submission_emails(process: TicketProcess, subject_prefix="New submission"):
    form_obj = process.form
    emails = [e.strip() for e in (form_obj.notify_emails or "").split(",") if e.strip()]
    if not emails:
        return

    subject = f"{subject_prefix}: {form_obj.name}"
    rows = "".join(
        f"<tr><th align='left' style='padding:6px 10px'>{k}</th><td style='padding:6px 10px'>{v}</td></tr>"
        for k, v in (process.ticket_data or {}).items()
    )
    html = f"""
      <h3>{subject_prefix}: {form_obj.name}</h3>
      <table border="1" cellpadding="0" cellspacing="0" style="border-collapse:collapse">{rows}</table>
      <p>Process ID: {process.pk}</p>
    """
    plain = "\n".join(f"{k}: {v}" for k, v in (process.ticket_data or {}).items())

    msg = EmailMultiAlternatives(subject, plain, to=emails)
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)


# -----------------------------------------------------
#  DYNAMIC START VIEW
# -----------------------------------------------------
class DynamicStartView(CreateProcessView):
    model = TicketProcess

    def get_form_class(self):
        selected_form_id = self.request.POST.get("form") or self.request.GET.get("form")

        class StartForm(forms.ModelForm):
            class Meta:
                model = TicketProcess
                fields = ["form"]

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                form_obj = None
                if selected_form_id:
                    try:
                        form_obj = FormModel.objects.get(id=selected_form_id)
                    except FormModel.DoesNotExist:
                        form_obj = None
                if form_obj:
                    # Show only Risk Representative fields at start
                    add_fields_to_form(self, form_obj, role=FormField.ROLE_USER)

        return StartForm

    def form_valid(self, form):
        # Let Viewflow save the process with the selected Form
        response = super().form_valid(form)
        process: TicketProcess = self.object
        form_obj = process.form

        # Ensure we have a single entry for the entire flow
        if not process.entry:
            process.entry = FormEntry.objects.create(
                form=form_obj,
                submitted_by=self.request.user if self.request.user.is_authenticated else None,
            )

        # Save user-stage dynamic fields into the entry
        _update_entry_values_for_role(
            entry=process.entry,
            form_obj=form_obj,
            cleaned_data=form.cleaned_data,
            files=self.request.FILES,
            role=FormField.ROLE_USER,
        )

        # Prepare a snapshot (will persist if your model has ticket_data)
        process.ticket_data = _snapshot_from_entry(process.entry)

        # IMPORTANT: do not include 'ticket_data' in update_fields
        try:
            process.save(update_fields=["entry"])
        except ValueError:
            # If update_fields complains for any reason, fall back to a plain save
            process.save()

        return response


# -----------------------------------------------------
#  APPROVAL VIEW (FOR ALL STAGES)
# -----------------------------------------------------
class ApprovalView(UpdateProcessView):
    model = TicketProcess
    template_name = "viewflow/workflow/task.html"
    role = None  # set via as_view(role="user"/"dev"/"ba"/"pm")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        role = self.role or self.kwargs.get("role")
        ctx["ticket_summary_html"] = build_ticket_summary_html(self.object)
        ctx["is_approval"] = True
        ctx["role"] = role
        ctx["role_display"] = ROLE_DISPLAY.get(role, role)
        ctx["status_row"] = {
            ROLE_DISPLAY["user"]: (self.object.user_decision or "-"),
            ROLE_DISPLAY["dev"]: (self.object.dev_decision or "-"),
            ROLE_DISPLAY["ba"]: (self.object.ba_decision or "-"),
            ROLE_DISPLAY["pm"]: (self.object.pm_decision or "-"),
        }
        return ctx

    def get_form_class(self):
        process = self.get_object()
        role = self.role or self.kwargs.get("role")
        comment_field = f"{role}_comment"
        form_obj = process.form

        class _Form(ApprovalForm):
            class Meta(ApprovalForm.Meta):
                model = TicketProcess
                fields = [comment_field]

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Pre-fill dynamic values if present
                initial_map = {}
                if process.entry:
                    for v in process.entry.values.all():
                        initial_map[str(v.field_id)] = v.value_text or (
                            v.value_file.name if v.value_file else ""
                        )

                # Exclude Description for all approval stages
                add_fields_to_form(
                    self,
                    form_obj,
                    role=role,
                    initial_map=initial_map,
                    exclude_labels={"Description"},
                )

                # Beautify the comment field
                lbl = f"{ROLE_DISPLAY.get(role, role)} comment"
                self.fields[comment_field].label = lbl
                self.fields[comment_field].help_text = ""
                self.fields[comment_field].widget = forms.Textarea(
                    attrs={"rows": 6, "style": "width:100%"}
                )

        return _Form

    def form_valid(self, form):
        process = form.instance
        role = self.role or self.kwargs.get("role")

        decision = self.request.POST.get("decision")
        if decision not in ("approved", "rejected"):
            form.add_error(None, "Please click Approve or Reject.")
            return self.form_invalid(form)

        if not process.entry:
            process.entry = FormEntry.objects.create(
                form=process.form, submitted_by=self.request.user
            )

        _update_entry_values_for_role(
            process.entry, process.form, form.cleaned_data, self.request.FILES, role
        )
        process.ticket_data = _snapshot_from_entry(process.entry)

        # Save without specifying update_fields (avoids the ticket_data problem)
        setattr(process, f"{role}_decision", decision)
        setattr(process, f"approved_by_{role}", self.request.user.get_username())
        process.save()

        return super().form_valid(form)


# =====================================================
#  Dynamic Application Views (for the /grc tile)
# =====================================================
class FormListView(ListView):
    """
    Lists Forms that have a WorkflowTemplate linked.
    Used by the 'GRC Dynamic Requests' application tile (/grc/).
    """
    template_name = "grc/form_list.html"
    context_object_name = "forms"

    def get_queryset(self):
        return FormModel.objects.filter(workflow_template__isnull=False).order_by("name")


class StartFromTemplateView(RedirectView):
    """
    Redirect to the REAL Viewflow start URL and pass the selected form id.
    This avoids using CreateProcessView outside of an activation.
    """
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        form_pk = kwargs["pk"]
        # Viewflow app is mounted under /ticketflow/, flow slug is "ticket"
        # (you already have URLs like /ticketflow/ticket/... in your project)
        start_url = "/ticketflow/ticket/start/"
        return f"{start_url}?form={form_pk}"