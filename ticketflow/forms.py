# ticketflow/forms.py
from django import forms
from django.core.validators import RegexValidator

from .models import Form as FormModel, FormField, TicketProcess
from .validators import validate_uploaded_file


def add_fields_to_form(
    django_form,
    form_obj: FormModel,
    role_code: str | None = None,
    role: str | None = None,
    initial_map: dict | None = None,
    exclude_labels: set[str] | None = None,
    readonly: bool = False,  # <--- NEW master switch to force read-only rendering
):
    """
    Add dynamic fields from FormField into the given Django form.

    Args:
        django_form: The form instance to mutate (e.g., self inside __init__).
        form_obj:    The Form model instance that owns FormField rows.
        role_code:   Internal role key to include fields for (e.g. "user", "dev"...).
        role:        Back-compat alias for role_code.
        initial_map: Optional map for initial values by field id (str) or label.
        exclude_labels: Labels to skip completely.
        readonly:    If True, render all included fields disabled/read-only and
                     make them non-required, so approve screens don't re-validate.
                     File fields are displayed as a text field with the stored
                     filename/value.
    """
    if role_code is None:
        role_code = role

    initial_map = initial_map or {}
    exclude_labels = exclude_labels or set()

    qs = form_obj.fields.all()
    if role_code:
        qs = qs.filter(role=role_code)

    for ff in qs:
        # Skip hidden or explicitly excluded fields
        if ff.hidden or (ff.label in exclude_labels):
            continue

        key = str(ff.id)

        # Initial resolution: prefer by id, then by label, then default_value
        init = (
            initial_map.get(key)
            or initial_map.get(ff.label)
            or ff.default_value
            or None
        )

        # Validators
        base_validators = []
        if ff.regex:
            base_validators.append(
                RegexValidator(regex=ff.regex, message="Invalid format")
            )

        # Required is suppressed when we render read-only
        required = bool(ff.required) and not readonly

        # Common kwargs
        common_kwargs = dict(
            label=ff.label,
            required=required,
            help_text=ff.help_text,
            initial=init,
            validators=base_validators,
        )

        # ---- Build the correct Django field ----
        field = None

        if ff.field_type == FormField.TEXT:
            field = forms.CharField(
                max_length=ff.max_length or 255,
                widget=forms.TextInput(attrs={"placeholder": ff.placeholder or ""}),
                **common_kwargs,
            )

        elif ff.field_type == FormField.TEXTAREA:
            field = forms.CharField(
                widget=forms.Textarea(
                    attrs={"placeholder": ff.placeholder or "", "rows": 4}
                ),
                **common_kwargs,
            )

        elif ff.field_type == FormField.SELECT:
            choices = [(c.strip(), c.strip()) for c in (ff.choices or "").split(",") if c.strip()]
            field = forms.ChoiceField(choices=choices, **common_kwargs)

        elif ff.field_type == FormField.FILE:
            if readonly:
                # On approval screens, show existing file name/value as read-only text
                field = forms.CharField(
                    required=False,
                    initial=init,
                    label=ff.label,
                    help_text=ff.help_text,
                )
                field.widget = forms.TextInput()
            else:
                file_validators = list(base_validators) + [validate_uploaded_file]
                file_kwargs = dict(common_kwargs)
                file_kwargs["validators"] = file_validators
                field = forms.FileField(**file_kwargs)

        elif ff.field_type == FormField.EMAIL:
            field = forms.EmailField(
                widget=forms.EmailInput(attrs={"placeholder": ff.placeholder or ""}),
                **common_kwargs,
            )

        elif ff.field_type == FormField.DATE:
            field = forms.DateField(
                input_formats=["%Y-%m-%d"],
                widget=forms.DateInput(attrs={"placeholder": "YYYY-MM-DD"}),
                **common_kwargs,
            )

        elif ff.field_type == FormField.NUMBER:
            field = forms.IntegerField(
                min_value=ff.min_value,
                max_value=ff.max_value,
                **common_kwargs,
            )

        elif ff.field_type == FormField.CHECKBOX:
            field = forms.BooleanField(
                required=required,
                initial=(init in ("True", "true", True, "1", 1)),
                label=ff.label,
                help_text=ff.help_text,
            )

        elif ff.field_type == FormField.RADIO:
            choices = [(c.strip(), c.strip()) for c in (ff.choices or "").split(",") if c.strip()]
            field = forms.ChoiceField(
                choices=choices,
                widget=forms.RadioSelect,
                **common_kwargs,
            )

        else:
            # Fallback so we always render something usable
            field = forms.CharField(**common_kwargs)

        # Attach to the target form
        django_form.fields[key] = field

        # Field-level read-only from DB OR global read-only -> disable UI and validation
        if ff.readonly or readonly:
            f = django_form.fields[key]
            f.required = False
            f.widget.attrs["readonly"] = True
            f.widget.attrs["disabled"] = True


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = TicketProcess
        # The comment field for each role is injected in the view
        fields = []