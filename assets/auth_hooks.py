"""Hook into Alliance Auth"""

# Django
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

# AA Assets
from assets import app_settings, urls
from assets.managers import GeneralManager
from assets.models import Request


class AssetsMenuItem(MenuItemHook):
    """This class ensures only authorized users will see the menu entry"""

    def __init__(self):
        super().__init__(
            f"{app_settings.ASSETS_APP_NAME}",
            "fas fa-building-user fa-fw",
            "assets:location",
            navactive=["assets:"],
        )

    def render(self, request):
        if GeneralManager.has_basic_access(request.user):
            if GeneralManager.has_manage_requests_access(request.user):
                app_count = Request.objects.open_requests_total_count()
            else:
                app_count = None
            self.count = app_count if app_count and app_count > 0 else None
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    """Register the menu item"""

    return AssetsMenuItem()


@hooks.register("url_hook")
def register_urls():
    """Register app urls"""

    return UrlHook(urls, "assets", r"^assets/")
