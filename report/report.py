"""Builds the HTML report from template.html with session data embedded as JSON."""
import json
import os
import webbrowser
from pathlib import Path

import config

TEMPLATE = config.resource_path("report/template.html")


def report_filename(started_at):
    return f"report_{(started_at or 'session').replace(':', '').replace('-', '')}.html"


def build_report(session_data, out_dir=config.SESSIONS_DIR, open_browser=True):
    payload = {
        "session": session_data,
        "colors": config.STATE_COLORS,
        "labels": config.STATE_LABELS,
        "privacy": config.TEXTS["privacy_footer"],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__SESSION_DATA__*/null", data)

    os.makedirs(out_dir, exist_ok=True)
    path = Path(out_dir, report_filename(session_data.get("started_at"))).resolve()
    path.write_text(html, encoding="utf-8")
    if open_browser:
        webbrowser.open(path.as_uri())
    return str(path)
