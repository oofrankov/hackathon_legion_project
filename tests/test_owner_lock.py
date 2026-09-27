"""OwnerLock on synthetic face boxes (no camera). Frames come at ~12 fps."""
import config
from tracker.owner_lock import FaceBox, OwnerLock

FPS = 12
OWNER = FaceBox(0.5, 0.5, 0.30)          # big face in the middle = person at the desk
BEHIND = FaceBox(0.85, 0.35, 0.10)       # small face on the side = someone in the back


def locked(now=0.0):
    lock = OwnerLock(aspect=0.75)
    lock.set_anchor((OWNER.cx, OWNER.cy), OWNER.size, now)
    return lock


def run(lock, faces_at, start, seconds):
    """Feed frames for `seconds`; faces_at(t) -> list of boxes. Returns last result."""
    result, t = None, start
    for i in range(int(seconds * FPS)):
        t = start + i / FPS
        result = lock.select(faces_at(t), t)
    return result, t


def test_single_face_at_owner_place_is_owner():
    lock = locked()
    assert lock.select([OWNER], 0.1) is OWNER
    assert lock.others_count == 0


def test_owner_plus_small_face_behind():
    lock = locked()
    faces = [BEHIND, OWNER]
    assert lock.select(faces, 0.1) is OWNER
    assert lock.others_count == 1


def test_owner_gone_other_face_stays_is_none_without_jump():
    lock = locked()
    lock.select([OWNER], 0.1)
    result, _ = run(lock, lambda t: [BEHIND], 0.2, 10)
    assert result is None
    assert lock.others_count == 1
    assert abs(lock.last.cx - OWNER.cx) < 1e-9     # last position did not drift to the other face


def test_passer_by_through_owner_zone_is_not_accepted():
    lock = locked()
    lock.select([OWNER], 0.0)
    gone_until = config.NO_FACE_SEC + 1
    run(lock, lambda t: [], 0.1, gone_until)
    # someone crosses the owner's zone for 1 s (< OWNER_RETURN_HOLD_SEC)
    result, t = run(lock, lambda t: [FaceBox(0.52, 0.5, 0.28)], gone_until, 1.0)
    assert result is None
    result, _ = run(lock, lambda t: [], t + 0.1, 0.5)
    assert result is None


def test_owner_returns_and_holds_is_accepted_again():
    lock = locked()
    lock.select([OWNER], 0.0)
    gone_until = config.NO_FACE_SEC + 1
    run(lock, lambda t: [], 0.1, gone_until)
    back = FaceBox(0.55, 0.52, 0.29)
    result, t = run(lock, lambda t: [back, BEHIND], gone_until, config.OWNER_RETURN_HOLD_SEC + 0.3)
    assert result is back
    assert lock.others_count == 1
    assert not lock.recalibration_suggested      # short absence: no recalibration


def test_owner_moving_smoothly_is_followed():
    lock = locked()
    # drifts 0.05 of the frame width per second for 4 s
    result, _ = run(lock, lambda t: [FaceBox(0.5 + 0.05 * t, 0.5, 0.30), BEHIND], 0.0, 4)
    assert result is not None and result.cx > 0.68
    assert lock.others_count == 1


def test_sudden_jump_to_another_place_is_not_followed():
    lock = locked()
    lock.select([OWNER], 0.0)
    assert lock.select([FaceBox(0.1, 0.5, 0.30)], 0.1) is None


def test_different_size_at_owner_place_is_rejected():
    lock = locked()
    assert lock.select([FaceBox(0.5, 0.5, 0.12)], 0.1) is None   # far person behind the desk


def test_long_absence_suggests_recalibration():
    lock = locked()
    lock.select([OWNER], 0.0)
    start = config.OWNER_RECALIBRATE_AFTER_SEC + 10
    result, _ = run(lock, lambda t: [OWNER], start, config.OWNER_RETURN_HOLD_SEC + 0.3)
    assert result is OWNER and lock.recalibration_suggested


def test_touch_after_pause_keeps_following():
    lock = locked()
    lock.select([OWNER], 0.0)
    lock.touch(600.0)                               # resumed after a 10-min pause
    assert lock.select([OWNER], 600.1) is OWNER
    assert not lock.recalibration_suggested


def test_clear_forgets_everything():
    lock = locked()
    lock.clear()
    assert not lock.has_anchor and lock.last is None
    assert lock.select([OWNER], 1.0) is None


# --- calibration: exactly one person, anchor = average position/size -------
def _signals(frame_id, faces, box=None):
    from tracker.face import FaceSignals
    return FaceSignals(frame_id=frame_id, face_present=faces == 1, faces_count=faces,
                       calib_box=box if faces == 1 else None, yaw=0.0, pitch=0.0)


def test_calibration_with_two_people_must_be_repeated():
    from tracker.calibration import Calibrator
    cal = Calibrator()
    for i in range(1, 60):
        cal.add(_signals(i, 2 if i % 3 == 0 else 1, (0.5, 0.5, 0.3)))
    assert cal.multi_face and not cal.ok()


def test_calibration_anchor_is_average_of_single_face():
    from tracker.calibration import Calibrator
    cal = Calibrator()
    for i in range(1, 41):
        cal.add(_signals(i, 1, (0.4 if i % 2 else 0.6, 0.5, 0.3)), point=(i - 1) // 8)
    assert cal.ok() and not cal.multi_face
    (cx, cy), size = cal.anchor()
    assert abs(cx - 0.5) < 1e-9 and abs(cy - 0.5) < 1e-9 and abs(size - 0.3) < 1e-9


def test_calibration_fails_if_camera_stops_after_a_few_frames():
    """Five good frames at the first dot, then nothing: not a valid calibration."""
    from tracker.calibration import Calibrator
    cal = Calibrator()
    for i in range(1, 6):
        cal.add(_signals(i, 1, (0.5, 0.5, 0.3)), point=0)
    assert not cal.points_covered and not cal.ok()
