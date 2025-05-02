"""
Constants
"""

# Standard Library
import os

AA_ASSETS_BASE_DIR = os.path.join(os.path.dirname(__file__))
AA_ASSETS_STATIC_DIR = os.path.join(AA_ASSETS_BASE_DIR, "static", "assets")

# Embed colors
DISCORD_EMBED_COLOR_INFO = 0x5BC0DE
DISCORD_EMBED_COLOR_SUCCESS = 0x5CB85C
DISCORD_EMBED_COLOR_WARNING = 0xF0AD4E
DISCORD_EMBED_COLOR_DANGER = 0xD9534F

# Discord embed color map
DISCORD_EMBED_COLOR_MAP = {
    "info": DISCORD_EMBED_COLOR_INFO,
    "success": DISCORD_EMBED_COLOR_SUCCESS,
    "warning": DISCORD_EMBED_COLOR_WARNING,
    "danger": DISCORD_EMBED_COLOR_DANGER,
}
