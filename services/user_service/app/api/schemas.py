from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from shared.enums import AccountStatus, Role


def _password_rules(v: str) -> str:
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("password must contain letters and numbers")
    return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    account_status: AccountStatus = AccountStatus.ACTIVE


class StaffOnboardRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=500)
    phone: str = Field(min_length=8, max_length=20, pattern=r"^[0-9+\-()\s]+$")
    aadhar: str = Field(min_length=12, max_length=12, pattern=r"^\d{12}$")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _password_rules(v)


class ResidentOnboardRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=8, max_length=20, pattern=r"^[0-9+\-()\s]+$")
    aadhar: str = Field(min_length=12, max_length=12, pattern=r"^\d{12}$")
    family_members: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _password_rules(v)

    @field_validator("family_members")
    @classmethod
    def trim_members(cls, v: list[str]) -> list[str]:
        out = [m.strip() for m in v if m and m.strip()]
        for m in out:
            if len(m) > 200:
                raise ValueError("family member name too long")
        return out


class StaffUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=500)
    phone: str = Field(min_length=8, max_length=20, pattern=r"^[0-9+\-()\s]+$")
    aadhar: str | None = Field(
        default=None,
        min_length=12,
        max_length=12,
        pattern=r"^\d{12}$",
    )
    password: str | None = Field(default=None, min_length=10, max_length=128)

    @field_validator("aadhar", mode="before")
    @classmethod
    def normalize_aadhar(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @field_validator("password", mode="before")
    @classmethod
    def normalize_password(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @field_validator("password")
    @classmethod
    def password_strength_opt(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _password_rules(v)


class ResidentUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=8, max_length=20, pattern=r"^[0-9+\-()\s]+$")
    aadhar: str | None = Field(
        default=None,
        min_length=12,
        max_length=12,
        pattern=r"^\d{12}$",
    )
    family_members: list[str] = Field(default_factory=list, max_length=30)
    password: str | None = Field(default=None, min_length=10, max_length=128)

    @field_validator("aadhar", mode="before")
    @classmethod
    def normalize_aadhar(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @field_validator("password", mode="before")
    @classmethod
    def normalize_password(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @field_validator("password")
    @classmethod
    def password_strength_opt(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _password_rules(v)

    @field_validator("family_members")
    @classmethod
    def trim_members(cls, v: list[str]) -> list[str]:
        out = [m.strip() for m in v if m and m.strip()]
        for m in out:
            if len(m) > 200:
                raise ValueError("family member name too long")
        return out


class AdminUserRow(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    account_status: AccountStatus
    phone: str | None = None
    address: str | None = None
    aadhar_masked: str | None = None
    family_members: list[str] = Field(default_factory=list)
