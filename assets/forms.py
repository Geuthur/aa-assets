"""Forms for the taxsystem app."""

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from assets.api.assets.helper import update_asset_object
from assets.models import Assets


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


class RequestMultiOrder(forms.Form):
    """Form for Multi-Ordering."""

    def __init__(self, *args, location_flag=None, location_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_fields = []  # Liste der dynamisch hinzugefügten Felder
        if location_id is not None:
            # Dynamisch Felder für jedes Asset mit der gegebenen location_id hinzufügen
            for asset in Assets.objects.filter(
                location_flag=location_flag, location_id=location_id
            ).order_by("eve_type__name"):
                asset = update_asset_object(asset)
                if asset is False:
                    continue

                field_name = f"item_id_{asset.pk}"
                self.fields[field_name] = forms.IntegerField(
                    label=_("Amount for ") + asset.eve_type.name,
                    min_value=1,
                    required=False,
                    widget=forms.NumberInput(
                        attrs={
                            "class": "form-control",
                            "data-item-id": asset.eve_type.id,
                            "data-quantity": asset.quantity,
                            "data-asset-pk": asset.pk,
                        }
                    ),
                )
                self.asset_fields.append(field_name)  # Feldname zur Liste hinzufügen
