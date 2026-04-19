from __future__ import annotations

import re

from app.application.complaint_service import generate_public_id


def test_public_id_format():
    pid = generate_public_id(2026)
    assert re.match(r"^CMP-2026-[A-F0-9]{6}$", pid)
