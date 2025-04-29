from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

def generate_button(
    template, queryset, settings, request
) -> mark_safe:
    """Generate a html button for the tax system"""
    return format_html(
        render_to_string(
            template,
            {
                "queryset": queryset,
                "settings": settings,
            },
            request=request,
        )
    )