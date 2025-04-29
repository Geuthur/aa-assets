"""Forms for the taxsystem app."""

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


def get_mandatory_form_label_text(text: str) -> str:
    """Label text for mandatory form fields"""

    required_marker = "<span class='form-required-marker'>*</span>"

    return mark_safe(
        f"<span class='form-field-required'>{text} {required_marker}</span>"
    )


class RequestOrder(forms.Form):
    """Form for Ordering."""

    amount = forms.IntegerField(
        label=get_mandatory_form_label_text(_("Amount")),
        min_value=1,
    )
