"""User choices for the distracting-apps list, stored locally in user_settings.json.

Contains only what the user picked/typed (catalogue ids + custom names),
never anything observed from their windows.
"""
import json
import os

import config


def default_settings():
    return {"enabled": {i["id"]: i["default"] for i in config.DISTRACTION_CATALOG}, "custom": []}


def load_settings(path=None):
    """Returns (settings, first_run)."""
    path = path or config.USER_SETTINGS_PATH
    settings = default_settings()
    if not os.path.exists(path):
        return settings, True
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        settings["enabled"].update({k: bool(v) for k, v in data.get("enabled", {}).items()})
        settings["custom"] = [str(c) for c in data.get("custom", []) if str(c).strip()]
    except (OSError, ValueError):
        pass
    return settings, False


def save_settings(settings, path=None):
    with open(path or config.USER_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=1)


def enabled_count(settings):
    return sum(1 for v in settings["enabled"].values() if v) + len(settings["custom"])
