from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    RESIDENT = "resident"
    MAINTENANCE_STAFF = "maintenance_staff"
    ADMIN = "admin"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    RESIGNED = "resigned"


class ComplaintStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    COMPLETED = "completed"


class Category(str, Enum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    CLEANING = "cleaning"
    APPLIANCE = "appliance"
    OTHER = "other"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
