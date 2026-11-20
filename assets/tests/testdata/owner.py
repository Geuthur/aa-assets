"""Factories of the owner module."""

# Third Party
import factory
import factory.fuzzy

# AA EVE SDE Factory
from evesde_factory.allianceauth import BaseMetaFactory

# Django
from django.utils import timezone

# AA Assets
from assets.models.helpers.update_manager import OwnerUpdateSection
from assets.models.owner import OwnerUpdateStatus


class OwnerUpdateStatusFactory(
    factory.django.DjangoModelFactory,
    metaclass=BaseMetaFactory[OwnerUpdateStatus],
):
    """
    Generate an OwnerUpdateStatus object for testing.

    Args:
        owner (Owner): The owner of the status, required.
    """

    class Meta:
        model = OwnerUpdateStatus
        django_get_or_create = ("owner", "section")

    section = factory.fuzzy.FuzzyChoice(OwnerUpdateSection.values)
    is_success = True
    error_message = ""
    has_token_error = False
    last_run_at = factory.fuzzy.FuzzyDateTime(
        start_dt=timezone.make_aware(timezone.datetime(2020, 1, 1)),
        end_dt=timezone.make_aware(timezone.datetime(2024, 12, 31)),
    )
    last_run_finished_at = factory.fuzzy.FuzzyDateTime(
        start_dt=timezone.make_aware(timezone.datetime(2020, 1, 1)),
        end_dt=timezone.make_aware(timezone.datetime(2024, 12, 31)),
    )
    last_update_at = factory.fuzzy.FuzzyDateTime(
        start_dt=timezone.make_aware(timezone.datetime(2020, 1, 1)),
        end_dt=timezone.make_aware(timezone.datetime(2024, 12, 31)),
    )
    last_update_finished_at = factory.fuzzy.FuzzyDateTime(
        start_dt=timezone.make_aware(timezone.datetime(2020, 1, 1)),
        end_dt=timezone.make_aware(timezone.datetime(2024, 12, 31)),
    )
