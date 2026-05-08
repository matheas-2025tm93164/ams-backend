# Smart Apartment Maintenance System -- Backend

Microservices monorepo powering the Apartment Maintenance & Complaint Management System. Three services work together: **API Gateway** (single entry point), **User Service** (authentication, user management), and **Complaint Service** (complaints, reviews, analytics, file uploads).

## Prerequisites

- Python 3.9+
- MongoDB 6+ running on `localhost:27017`
- (Optional) Docker Desktop for containerized setup

## Quick Start (Local)

From the **project root** (parent folder), one command starts MongoDB check, all three API services, and the Vite frontend:

```bash
./scripts/dev-local.sh
```

Stop all services including MongoDB:

```bash
./scripts/stop-dev-local.sh
```

## Manual Setup

```bash
cd ams-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Start each service in a separate terminal:

```bash
# Terminal 1: User Service (port 8001)
export PYTHONPATH=packages/shared/src:services/user_service
uvicorn app.main:app --reload --port 8001 --app-dir services/user_service

# Terminal 2: Complaint Service (port 8002)
export PYTHONPATH=packages/shared/src:services/complaint_service
uvicorn app.main:app --reload --port 8002 --app-dir services/complaint_service

# Terminal 3: API Gateway (port 8000)
export PYTHONPATH=packages/shared/src:services/gateway
uvicorn app.main:app --reload --port 8000 --app-dir services/gateway
```

## Environment Variables

Reference: `.env.example`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | Yes | - | Signing key for JWT tokens (min 32 chars) |
| `MONGO_URI` | No | `mongodb://localhost:27017` | MongoDB connection string |
| `USER_SERVICE_URL` | No | `http://localhost:8001` | User Service base URL (for Gateway) |
| `COMPLAINT_SERVICE_URL` | No | `http://localhost:8002` | Complaint Service base URL (for Gateway) |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Allowed frontend origins (comma-separated) |
| `SEED_DEMO_USERS` | No | `0` | Set to `1` to seed admin and staff on startup |
| `SEED_ADMIN_EMAIL` | No | `admin@example.com` | Seeded admin email |
| `SEED_ADMIN_PASSWORD` | No | `Admin123!pass` | Seeded admin password |

## Seeded Demo Accounts

When `SEED_DEMO_USERS=1` (set in `.env`), these accounts are created on first startup:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@example.com` | `Admin123!pass` |
| Staff | `staff@example.com` | `Staff123!pass` |

Residents are onboarded by Admin through the UI (no self-registration).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│               API Gateway (port 8000)                   │
│  /auth/*        → User Service                          │
│  /complaints/*  → Complaint Service                     │
│  /reviews       → Complaint Service                     │
│  /analytics/*   → Complaint Service                     │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
             ▼                            ▼
┌────────────────────────┐   ┌───────────────────────────┐
│ User Service (8001)    │   │ Complaint Service (8002)  │
│ - Login / JWT          │   │ - CRUD complaints         │
│ - Onboard staff/res    │   │ - File uploads            │
│ - Activate/Deactivate  │   │ - Reviews & ratings       │
│ - Internal user lookup │   │ - Analytics               │
│                        │◄──│ (internal HTTP calls)     │
│ DB: users_db           │   │ DB: complaints_db         │
└────────────────────────┘   └───────────────────────────┘
```

## Databases (MongoDB)

| Database | Service | Collection | Description |
|----------|---------|------------|-------------|
| `users_db` | User Service | `users` | All user accounts (admin, staff, residents) |
| `complaints_db` | Complaint Service | `complaints` | Complaints, attachments, reviews |

## API Endpoints

### Authentication (`/auth`)

| Method | Path | Access | Purpose |
|--------|------|--------|---------|
| POST | `/auth/login` | Public | Login, returns JWT |
| GET | `/auth/me` | Authenticated | Current user profile |
| GET | `/auth/maintenance-staff` | Admin | Active staff list |

### Admin User Management (`/auth/admin`)

| Method | Path | Access | Purpose |
|--------|------|--------|---------|
| GET | `/auth/admin/staff` | Admin | All staff (incl. inactive) |
| GET | `/auth/admin/residents` | Admin | All residents (incl. inactive) |
| POST | `/auth/admin/staff/onboard` | Admin | Create staff account |
| POST | `/auth/admin/residents/onboard` | Admin | Create resident account |
| PATCH | `/auth/admin/staff/{id}` | Admin | Update staff details |
| PATCH | `/auth/admin/residents/{id}` | Admin | Update resident details |
| POST | `/auth/admin/users/{id}/activate` | Admin | Activate account |
| POST | `/auth/admin/users/{id}/deactivate` | Admin | Deactivate account |

### Complaints (`/complaints`)

| Method | Path | Access | Purpose |
|--------|------|--------|---------|
| POST | `/complaints` | Resident | Create complaint |
| GET | `/complaints` | Scoped | List (own/assigned/all) |
| GET | `/complaints/{id}` | Authorized | Get detail |
| PATCH | `/complaints/{id}` | Role-specific | Update (status, assign, edit) |
| DELETE | `/complaints/{id}` | Resident (pending) / Admin | Delete |
| POST | `/complaints/{id}/attachments` | Resident (pending) | Upload image |
| GET | `/complaints/{id}/attachments/{idx}/file` | Authorized | Download image |

### Reviews & Analytics

| Method | Path | Access | Purpose |
|--------|------|--------|---------|
| GET | `/reviews` | Admin / Staff | Completed complaint reviews |
| GET | `/analytics/summary` | Admin | Counts by category |

## Project Structure

```
ams-backend/
├── packages/
│   └── shared/src/shared/        # Shared library (enums, JWT utils)
│       ├── enums.py              # Role, Status, Category, Priority
│       └── jwt_tokens.py         # Token create/decode/verify
├── services/
│   ├── gateway/app/              # API Gateway
│   │   └── main.py              # HTTP proxy routing
│   ├── user_service/app/         # User management
│   │   ├── api/routes/
│   │   │   ├── auth.py          # Login, profile
│   │   │   ├── admin_users.py   # Staff/resident CRUD
│   │   │   └── internal.py      # Service-to-service
│   │   ├── application/
│   │   │   └── auth_service.py  # Business logic
│   │   ├── domain/models.py     # UserDocument
│   │   ├── infrastructure/
│   │   │   └── user_repository.py
│   │   └── seed.py              # Demo user seeding
│   └── complaint_service/app/    # Complaint management
│       ├── api/routes/
│       │   └── complaints.py    # All endpoints
│       ├── application/
│       │   └── complaint_service.py  # Business rules
│       ├── domain/models.py     # ComplaintDocument
│       └── infrastructure/
│           ├── complaint_repository.py
│           └── user_client.py   # Internal user lookups
├── requirements.txt
├── .env.example
└── tests/                        # pytest test suite
```

## Testing

```bash
source .venv/bin/activate
pytest --cov=services --cov-report=term-missing
```

| Test File | Coverage |
|-----------|----------|
| `tests/test_complaint_application.py` | Complaint business logic |
| `tests/test_complaint_patch_schema.py` | PATCH validation rules |
| `tests/test_public_id.py` | Complaint ID generation |
| `tests/test_admin_schemas.py` | Onboard/update schemas |
| `packages/shared/tests/test_jwt_roundtrip.py` | JWT encode/decode |

## Data Cleanup Scripts

From the project root:

```bash
# Wipe all data (drops both databases, clears uploads)
python3 scripts/mongo-wipe-all.py

# Reset data but keep the admin account
python3 scripts/mongo-fresh-keep-admin.py
```

## Key Configuration

| Setting | Default | Location |
|---------|---------|----------|
| Token expiry | 30 minutes | `services/user_service/app/config.py` |
| Password hashing | Argon2 | `services/user_service/app/application/auth_service.py` |
| JWT algorithm | HS256 | `services/user_service/app/config.py` |
| Max description | 8000 chars | `services/complaint_service/app/api/schemas.py` |
| Max feedback | 4000 chars | `services/complaint_service/app/api/schemas.py` |
| Aadhar validation | 12 digits | `services/user_service/app/api/schemas.py` |
