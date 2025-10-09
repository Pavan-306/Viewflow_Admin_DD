from django.contrib import admin
from .models import (
    Form,
    FormField,
    FormEntry,
    FormEntryValue,
    TicketProcess,
)

# Dynamic workflow admin
from .dynamic_models import WorkflowTemplate, WorkflowStage


# =========================
#  FORM ADMIN
# =========================
@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ("name", "workflow_template", "created")
    search_fields = ("name",)
    list_filter = ("workflow_template",)
    fieldsets = (
        (None, {"fields": ("name", "workflow_template")}),
        ("Notifications", {"fields": ("notify_emails",)}),
    )


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 0


# =========================
#  FORM ENTRY ADMIN
# =========================
@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "form", "submitted_by", "submitted_at")
    list_filter = ("form",)
    search_fields = ("id", "form__name", "submitted_by__username")


@admin.register(FormEntryValue)
class FormEntryValueAdmin(admin.ModelAdmin):
    list_display = ("entry", "field", "value_text", "value_file")
    search_fields = ("entry__id", "field__label", "value_text")


# =========================
#  TICKET PROCESS ADMIN
# =========================
@admin.register(TicketProcess)
class TicketProcessAdmin(admin.ModelAdmin):
    """
    Note:
    - 'is_finished' is NOT a model field; we expose a computed boolean column instead.
    """
    list_display = (
        "id",
        "form",
        "workflow_template",
        "created",
        "finished",
        "get_is_finished",   # <- computed column (replaces 'is_finished')
    )
    list_filter = ("form", "workflow_template")
    search_fields = ("id", "form__name")
    readonly_fields = ()

    @admin.display(boolean=True, description="Finished?")
    def get_is_finished(self, obj: TicketProcess) -> bool:
        """
        Consider the process 'finished' if the 'finished' datetime is set.
        """
        return bool(getattr(obj, "finished", None))


# =========================
#  WORKFLOW TEMPLATE ADMIN
# =========================
class WorkflowStageInline(admin.TabularInline):
    model = WorkflowStage
    extra = 0


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "updated", "created")
    search_fields = ("name",)
    inlines = [WorkflowStageInline]