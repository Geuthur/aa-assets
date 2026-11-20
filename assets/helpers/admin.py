"""Administration tasks shared by the admin view and the API."""

# Django
from django.utils.translation import gettext_lazy as _

# AA Assets
from assets.tasks import (
    clear_all_etags,
    update_all_assets,
    update_all_locations,
    update_all_parent_locations,
)


def queue_admin_tasks(
    force_refresh: bool = False,
    clear_etags: bool = False,
    update_assets: bool = False,
    update_locations: bool = False,
    update_parent_locations: bool = False,
) -> list[str]:
    """Queue the selected administration tasks and return a message for each."""
    queued = []
    if clear_etags:
        queued.append(str(_("Queued Clear All ETags")))
        clear_all_etags.apply_async(priority=1)
    if update_assets:
        queued.append(str(_("Queued Update All Assets")))
        update_all_assets.apply_async(
            kwargs={"force_refresh": force_refresh}, priority=7
        )
    if update_locations:
        queued.append(str(_("Queued Update All Locations")))
        update_all_locations.apply_async(
            kwargs={"force_refresh": force_refresh}, priority=7
        )
    if update_parent_locations:
        queued.append(str(_("Queued Update All Parent Locations")))
        update_all_parent_locations.apply_async(
            kwargs={"force_refresh": force_refresh}, priority=7
        )
    return queued
