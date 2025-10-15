# ticketflow/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import Form, FormField, FormEntry, FormEntryValue, TicketProcess

try:
    from .dynamic_models import WorkflowTemplate, WorkflowStage
except Exception:
    WorkflowTemplate = WorkflowStage = None


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 0
    ordering = ("order", "id")
    fields = (
        "drag",
        "label",
        "field_type",
        "required",
        "help_text",
        "choices",
        "max_length",
        "role",
        "placeholder",
        "readonly",
        "hidden",
    )
    readonly_fields = ("drag",)

    def drag(self, obj=None):
        return format_html('<span class="drag-handle" title="Drag to reorder">⋮⋮</span>')

    drag.short_description = ""

    class Media:
        # NOTE: no ?v=1 here – Django will URL-encode it and break the path.
        css = {
            "all": (
                "ticketflow/admin-inline-compact.v2.css",
                "ticketflow/admin-field-sizes.css",
                "ticketflow/admin-inline-force.v1.css",   # compact widths / hide order
            )
        }
        js = (
            "ticketflow/admin-sortable-inline.js",
            "ticketflow/admin-inline-mark.js",  # adds “⋮⋮” handle & drag cursor
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