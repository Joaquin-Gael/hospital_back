# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project summary
- Backend service for Hospital-SDLG built with FastAPI, SQLModel/SQLAlchemy, and Alembic. Real-time via WebSocket, payments via Stripe, simple JSON-based local storage for tokens/rate-limits, and an AI Assistant module.
- Root docs to reference: README.md (project intro), DOCUMENTACION_FUNCIONES.md (API/domain details), AI_ASSISTANT_README.md (AI module).

Common commands (Windows PowerShell shown; adapt for your shell)

Environment setup
- Python: requires >= 3.12
- Create and activate a virtual environment:
  - py -3.12 -m venv .venv
  - .\.venv\Scripts\Activate.ps1
- Install dependencies:
  - pip install -r requirements.txt

Environment variables (required at runtime)
Set these in a .env file at the project root (loaded by python-dotenv) or in your shell environment before running the app. Do not hardcode secrets in commands.
- DEBUG: 1 for development to enable docs and extra logging
- DB_URL: SQLAlchemy URL to your database (e.g., SQLite or Postgres)
- DOMINIO: External base URL for redirects (used by Stripe success/cancel)
- TOKEN_KEY: JWT signing secret
- ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL: seeded superuser (must match tests: ADMIN_EMAIL=admin@admin.com and ADMIN_PASSWORD=12345678)
- Stripe: STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY
- Google OAuth: CLIENT_ID_GOOGLE, CLIENT_SECRET_GOOGLE, OAUTH_GOOGLE_URL, OAUTH_GOOGLE_TOKEN_URL, OAUTH_GOOGLE_USERINFO_URL
- Email: EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS (0/1), EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

Run the API server
- Start with auto-reload in development:
  - python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
- Health check: GET /_health_check/ is mounted under a dynamic prefix (see “Dynamic API prefix”).
- API docs (Scalar) in DEBUG=1: GET /{id_prefix}/scalar

Dynamic API prefix (critical for local usage and tests)
- All API routes are mounted under a randomly generated UUID prefix at startup, taken from app.config.id_prefix.
- Retrieve it at runtime:
  - GET /id_prefix_api_secret/
- Example: if id_prefix = 3b9d6d90-..., then health check is at /3b9d6d90-.../_health_check/

Database migrations (Alembic)
Alembic configuration lives in app/alembic.ini and app/migrations/.
- Upgrade to latest:
  - alembic -c app/alembic.ini upgrade head
- Create a new autogeneration revision:
  - alembic -c app/alembic.ini revision --autogenerate -m "your message"
Notes
- The application startup (lifespan) also attempts to run migrations; when invoking Alembic manually, always point -c app/alembic.ini.

Testing
Integration tests expect a running server on localhost:8000 and use the dynamic API prefix.
- Terminal 1: start server (see “Run the API server”). Ensure ADMIN_EMAIL=admin@admin.com and ADMIN_PASSWORD=12345678 are set so login tests pass.
- Terminal 2: run the tests:
  - pytest -m integration
- Run a single test file:
  - pytest -m integration test/test_http_client.py
- Run a single test function:
  - pytest -m integration test/test_http_client.py::test_fetch_health_check_success
- Run WebSocket tests only:
  - pytest -m integration test/test_ws_client.py
Pytest config: see pytest.ini (adds --rich --verbose and defines marker: integration).

Lint/format
- No linter/formatter is configured in this repo (e.g., ruff/flake8/black are not declared). Skip lint commands unless tooling is added.

Local storage utilities (optional during dev)
The project includes a lightweight JSON-backed storage used for tokens, timeouts, etc. Utilities are provided via Click.
- Create a storage table (examples used at startup: ban-token, google-user-data, recovery-codes, ip-time-out):
  - python -m app.storage.command.main create_table "ban-token"
- List values in a table:
  - python -m app.storage.command.main list_values "ban-token"
- Get/Set/Delete entries:
  - python -m app.storage.command.main get <key> "ban-token"
  - python -m app.storage.command.main set <key> <json_or_text_value> "ban-token"
  - python -m app.storage.command.main delete <key> "ban-token"

High-level architecture and structure
Big picture
- Entry point: app/main.py defines FastAPI app, CORS, routers, and lifespan startup tasks (init_db, Alembic migrate, seed admin, create storage tables). It mounts static assets and an Admin SPA. All API routes are under a dynamic UUID prefix.
- API layer: app/api/* exposes domain endpoints. Routers are included under main_router (users, medic_area, auth, cashes, ai_assistant) and an OAuth router.
- Domain models: app/models.py contains SQLModel entities, enums (DoctorStates, DayOfWeek, TurnsState), and helpers (password hashing, media handling). Alembic migrations are generated from SQLModel metadata.
- Persistence: app/db/main.py creates the engine from DB_URL, provides a request-scoped Session dependency, simple DB health testing, and admin seeding.
- Auth and security: app/core/auth.py (referenced in DOCUMENTACION_FUNCIONES.md) implements JWT bearer and WebSocket auth, token generation/validation, rate limiting via local storage, and logout token ban lists. Endpoints live in app/api/auth.py (including Google OAuth flow and refresh).
- Storage layer: app/storage/ provides a JSON file-based key-value store with TTL, caching, and auto-flush. It’s used for rate limiting, recovery codes, and banned tokens.
- Payments: app/core/services/stripe_payment.py integrates Stripe Checkout for turn/service payments, applying health insurance discounts and recording cash details.
- Medical domain: app/api/medic_area.py manages departments, specialties, schedules, doctors, turns, appointments, locations, and chats (WebSocket). Business rules include availability calculation, state transitions for turns, and hierarchical location data.
- Cashes: app/api/cashes.py exposes transaction/cash endpoints and payment success/cancel redirects.
- AI Assistant: app/core/interfaces/ai_assistant.py (interface), app/core/services/ai_assistant_service.py (service), app/api/ai_assistant.py (endpoints), and app/schemas/ai_assistant.py (DTOs). See AI_ASSISTANT_README.md for full module description: NLP request routing, workflows (smart_appointment_booking, doctor_recommendation, schedule_optimization), and capability discovery.
- Docs/UI: Scalar docs mounted at /{id_prefix}/scalar in DEBUG. An Admin SPA is mounted under /admin serving from app/templates/admin.

Key development notes
- Dynamic prefix: Always fetch /id_prefix_api_secret/ before calling any protected route locally or in scripts.
- Startup side-effects: In dev, lifespan creates storage tables and seeds an admin if missing; in DEBUG, it prints a Scalar docs URL.
- Migrations location: Alembic config is under app/; pass -c app/alembic.ini for CLI operations.
- Tests assume admin@admin.com/12345678; set ADMIN_EMAIL and ADMIN_PASSWORD accordingly.

Important references (do not duplicate here)
- README.md: Project intro, badges, and high-level endpoints.
- DOCUMENTACION_FUNCIONES.md: Detailed endpoint and domain behavior across users, auth, medic area, turns, cashes, and core.
- AI_ASSISTANT_README.md: AI module design, endpoints, extension patterns, and testing examples.
