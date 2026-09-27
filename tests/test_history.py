"""History page: loading old/new session formats and overall stats (no browser)."""
import json

from report.history import build_history, compute_overall, load_sessions
from session.summary import compute_summary
from session.demo import fake_events


def write_session(folder, stamp, **meta):
    events = fake_events()
    data = {"started_at": f"2026-09-{stamp}", "events": events,
            "summary": compute_summary(events, meta.pop("pct", 80), 1), **meta}
    path = folder / f"session_{stamp.replace(':', '').replace('T', '_')}.json"
    path.write_text(json.dumps(data))
    return path, data


def test_loads_old_and_new_formats(tmp_path):
    path, old = write_session(tmp_path, "26T18:54:11", task="Essay", planned_min=50, self_estimate_min=40)
    old["summary"].pop("self_estimate_pct")        # the first sessions had no % estimate
    path.write_text(json.dumps(old))
    write_session(tmp_path, "27T09:00:00", name="Session 2 · 09:00", pct=90)
    (tmp_path / "session_broken.json").write_text("{not json")

    rows = load_sessions(tmp_path)
    assert [r["name"] for r in rows] == ["Essay", "Session 2 · 09:00"]
    assert rows[0]["expected_pct"] == 80            # 40 of 50 planned minutes
    assert rows[1]["expected_pct"] == 90


def test_overall_stats(tmp_path):
    write_session(tmp_path, "26T10:00:00", name="A", pct=90)
    write_session(tmp_path, "27T10:00:00", name="B", pct=60)
    o = compute_overall(load_sessions(tmp_path))
    assert o["sessions"] == 2 and o["days"] == 2
    assert o["total_min"] == 60.0
    assert o["focus_pct"] == 71
    assert o["avg_gap_pct"] == round(((90 - 71) + (60 - 71)) / 2)


def test_empty_history_page(tmp_path):
    path = build_history(tmp_path, open_browser=False)
    html = open(path, encoding="utf-8").read()
    assert '"sessions": []' in html


def test_short_session_counts_exact_seconds(tmp_path):
    """2 s focus + 5 s away: 29 %, not 0 % from rounded minutes (review item 7)."""
    import config
    events = [{"t": i, "state": config.FOCUSED} for i in range(2)] + \
             [{"t": i, "state": config.AWAY} for i in range(2, 7)]
    data = {"started_at": "2026-09-27T10:00:00", "events": events, "summary": compute_summary(events, 80, 0)}
    (tmp_path / "session_20260927_100000.json").write_text(json.dumps(data))
    rows = load_sessions(tmp_path)
    assert len(rows) == 1 and rows[0]["focus_pct"] == 29
    assert compute_overall(rows)["focus_pct"] == 29


def test_broken_session_files_are_skipped(tmp_path):
    write_session(tmp_path, "27T09:00:00", name="Good")
    (tmp_path / "session_bad_list.json").write_text("[]")
    (tmp_path / "session_bad_types.json").write_text(json.dumps(
        {"started_at": 5, "events": "x", "summary": {"total_min": "a", "state_sec": None}}))
    (tmp_path / "session_null.json").write_text("null")
    rows = load_sessions(tmp_path)
    assert [r["name"] for r in rows] == ["Good"]


def test_bad_settings_fall_back_to_defaults(tmp_path):
    from monitors.app_settings import default_settings, load_settings
    for content in ('{"enabled": null, "custom": 5}', "[]", '{"enabled": {"youtube": "yes"}}'):
        p = tmp_path / "s.json"
        p.write_text(content)
        settings, first_run = load_settings(p)
        assert settings == default_settings() and not first_run
