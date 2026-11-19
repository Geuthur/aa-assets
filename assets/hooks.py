"""AA Hooks"""

# Alliance Auth
from allianceauth.authentication.models import UserProfile


def add_info_to_context(request, context: dict) -> dict:
    """Add additional information to the context for the view."""
    # pylint: disable=import-outside-toplevel, cyclic-import
    theme = None
    try:
        user = UserProfile.objects.get(id=request.user.id)
        theme = user.theme
    except UserProfile.DoesNotExist:
        pass

    new_context = {
        **{
            "theme": theme,
        },
        **context,
    }
    return new_context
