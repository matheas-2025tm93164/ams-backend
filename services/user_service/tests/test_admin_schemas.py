from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import ResidentOnboardRequest, StaffOnboardRequest, StaffUpdateRequest


def test_staff_onboard_aadhar_requires_twelve_digits() -> None:
    StaffOnboardRequest(
        email="a@example.com",
        password="Abcd1234!xy",
        full_name="Name",
        address="Addr",
        phone="12345678",
        aadhar="123456789012",
    )


def test_staff_onboard_aadhar_rejects_eleven_digits() -> None:
    with pytest.raises(ValidationError):
        StaffOnboardRequest(
            email="a@example.com",
            password="Abcd1234!xy",
            full_name="Name",
            address="Addr",
            phone="12345678",
            aadhar="12345678901",
        )


def test_resident_onboard_aadhar_twelve_digits() -> None:
    ResidentOnboardRequest(
        email="b@example.com",
        password="Abcd1234!xy",
        full_name="Name",
        phone="12345678",
        aadhar="987654321098",
        family_members=[],
    )


def test_staff_update_optional_aadhar_twelve_digits() -> None:
    StaffUpdateRequest(
        full_name="Name",
        address="Addr",
        phone="12345678",
        aadhar="111122223333",
    )


def test_staff_update_aadhar_empty_normalized() -> None:
    m = StaffUpdateRequest(
        full_name="Name",
        address="Addr",
        phone="12345678",
        aadhar="",
    )
    assert m.aadhar is None
