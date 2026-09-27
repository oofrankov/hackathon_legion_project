"""Builds the HTML report from template.html with session data embedded as JSON."""
import json
import os
import re
import webbrowser
from pathlib import Path

import config

TEMPLATE = config.resource_path("report/template.html")
CHART_JS = config.resource_path("report/vendor/chart.umd.js")


def inline_vendor(html):
    """Put the bundled Chart.js into the page so the export never loads remote code."""
    try:
        # only "</script" could end the inline <script> early (Chart.js 4.4.1 has none)
        js = re.sub(r"</(script)", r"<\\/\1", CHART_JS.read_text(encoding="utf-8"), flags=re.I)
    except OSError:
        js = ""   # charts fall back to the tables/lists in the page
    return html.replace("/*__CHART_JS__*/", js)


def report_filename(started_at):
    return f"report_{(started_at or 'session').replace(':', '').replace('-', '')}.html"


def build_report(session_data, out_dir=config.SESSIONS_DIR, open_browser=True):
    from session.summary import normalize_session
    normalize_session(session_data)
    payload = {
        "session": session_data,
        "colors": config.STATE_COLORS,
        "labels": config.STATE_LABELS,
        "privacy": config.TEXTS["privacy_footer"],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = inline_vendor(TEMPLATE.read_text(encoding="utf-8")).replace("/*__SESSION_DATA__*/null", data)

    os.makedirs(out_dir, exist_ok=True)
    path = Path(out_dir, report_filename(session_data.get("started_at"))).resolve()
    path.write_text(html, encoding="utf-8")
    if open_browser:
        webbrowser.open(path.as_uri())
    return str(path)
