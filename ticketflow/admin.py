# ticketflow/admin.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import Form, FormField, FormEntry, FormEntryValue, TicketProcess
try:
    from .dynamic_models import WorkflowTemplate, WorkflowStage
except Exception:  # pragma: no cover
    WorkflowTemplate = WorkflowStage = None


class FormFieldInline(admin.TabularInline):
    """
    Tabular inline with a drag handle. We KEEP the 'order' form field but hide
    its widget so our JS can update it on drag and Django will persist it.
    """
    model = FormField
    extra = 0
    ordering = ("order", "id")

    # Don't show 'order' visibly, but DO keep it in the form
    fields = (
        "drag",
        "label", "field_type", "required", "help_text", "choices",
        "max_length", "role", "placeholder",
        "readonly", "hidden",
        "order",  # keep in the form; we will hide with a HiddenInput
    )
    readonly_fields = ("drag",)

    def drag(self, obj=None):
        return format_html('<span class="drag-handle" title="Drag to reorder">⋮⋮</span>')
    drag.short_description = ""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "order":
            formfield.widget = forms.HiddenInput()   # <-- keep in POST, hide in UI
        return formfield

    class Media:
        # We still declare Media for classic admin;
        # new admin may ignore it, so we will also inject via base_site.html below.
        css = {
            "all": (
                "ticketflow/admin-field-sizes.css",
                "ticketflow/admin-inline-compact.v2.css",
                "ticketflow/admin-sortable-inline.css",
            )
        }
        js = (
            "ticketflow/admin-inline-mark.js",
            "ticketflow/admin-sortable-inline.js",
        )


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ("name", "workflow_template", "created")
    search_fields = ("name",)
    list_filter = ("workflow_template",)
    fieldsets = (
        (None, {"fields": ("name", "workflow_template")}),
        ("Notifications", {"fields": ("notify_emails",)}),
    )
    inlines = [FormFieldInline]


@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "form", "submitted_by", "submitted_at")
    list_filter = ("form",)
    search_fields = ("id", "form__name", "submitted_by__username")


@admin.register(FormEntryValue)
class FormEntryValueAdmin(admin.ModelAdmin):
    list_display = ("entry", "field", "value_text", "value_file")
    search_fields = ("entry__id", "field__label", "value_text")


@admin.register(TicketProcess)
class TicketProcessAdmin(admin.ModelAdmin):
    list_display = ("id", "form", "workflow_template", "created", "finished")
    list_filter = ("form", "workflow_template")
    search_fields = ("id", "form__name")


if WorkflowTemplate and WorkflowStage:
    class WorkflowStageInline(admin.TabularInline):
        model = WorkflowStage
        extra = 0
        ordering = ("order", "id")

    @admin.register(WorkflowTemplate)
    class WorkflowTemplateAdmin(admin.ModelAdmin):
        list_display = ("name", "updated", "created")
        search_fields = ("name",)
        inlines = [WorkflowStageInline]