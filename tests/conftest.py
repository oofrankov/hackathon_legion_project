"""Tests never touch the real user data dir."""
import os
import tempfile

os.environ.setdefault("FOCUSCHECK_DATA_DIR", tempfile.mkdtemp(prefix="focuscheck-test-"))
