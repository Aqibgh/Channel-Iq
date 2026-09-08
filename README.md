# Channel IQ

Channel IQ is a React and Django application for analyzing YouTube videos, generating SEO metadata and reports, and producing short-form video clips.

The repository includes a lightweight Docker demo that starts without external API credentials. Optional Firebase, YouTube, OpenAI, AWS S3, email, and full media-processing integrations can be enabled through environment variables.

> The Docker demo is intended for local evaluation and development. It is not a production deployment configuration.

## What it does

- Fetches YouTube video metadata and downloads source videos.
- Generates SEO metadata and video analysis reports.
- Creates short-form clips from longer videos.
- Supports optional video upscaling, noise reduction, and caption processing.
- Supports optional YouTube OAuth for uploading videos and updating metadata.
- Provides a React interface and a Django API with JWT and CSRF support.

## Architecture

| Component | Location | Responsibility |
| --- | --- | --- |
| React client | [frontend/](frontend/) | UI, authentication flow, API requests, video workflows |
| Django API | [backend/](backend/) | Authentication, YouTube integration, reports, processing orchestration |
| View modules | [backend/app/views/](backend/app/views/) | Focused API handlers for processing, videos, YouTube, auth, reports, and CSRF |
| Database | SQLite by default | Local users, YouTube credentials, and application records |
| Object storage | Optional AWS S3 | Uploaded and processed video files |
| Local orchestration | [docker-compose.yml](docker-compose.yml) | Demo backend and frontend services |

The API is mounted at `/api/`. The Django health endpoint is available at `/health/`.

## Quick start with Docker

### Requirements

- Docker Desktop with Docker Compose v2.
- Git LFS if you need the optional LFS-managed Windows media binaries.

### Start the demo

From the repository root:

~~~powershell
Copy-Item .env.example .env
docker compose up --build
~~~

On macOS or Linux:

~~~bash
cp .env.example .env
docker compose up --build
~~~

The backend entrypoint runs migrations and creates a local Django signing key in the named `backend_data` volume when `DJANGO_SECRET_KEY` is empty.

Open:

- Frontend: <http://localhost:3000>
- Backend root: <http://localhost:8000>
- Backend health: <http://localhost:8000/health/>

The UI shell and health endpoint work without Firebase, YouTube, OpenAI, AWS, email, or Google OAuth credentials. Feature-specific actions return configuration errors until their required integrations are configured.

Stop the demo with:

~~~powershell
docker compose down
~~~

If ports `3000` or `8000` are already in use, set alternate values in `.env` and keep the frontend/API origins aligned:

~~~dotenv
BACKEND_PORT=8010
FRONTEND_PORT=3010
REACT_APP_API_BASE_URL=http://localhost:8010/api/
CORS_ALLOWED_ORIGINS=http://localhost:3010
CSRF_TRUSTED_ORIGINS=http://localhost:3010
~~~

## Configuration

Use the root [`.env.example`](.env.example) for Docker. For direct service development, use [`backend/.env.example`](backend/.env.example) and [`frontend/.env.example`](frontend/.env.example) as references.

Never commit `.env`, OAuth client secrets, Firebase service-account files, YouTube cookies, AWS credentials, or private keys.

### Core settings

| Variable | Purpose |
| --- | --- |
| DJANGO_SECRET_KEY | Django signing key; required for non-demo deployments |
| DEBUG | Enables local debug behavior; keep False for deployments |
| SECURE_COOKIES | Controls secure session and CSRF cookies |
| ALLOWED_HOSTS | Comma-separated Django hosts |
| CORS_ALLOWED_ORIGINS | Comma-separated frontend origins |
| CSRF_TRUSTED_ORIGINS | Comma-separated trusted frontend origins |
| REACT_APP_API_BASE_URL | Frontend base URL for the Django API |
| REACT_APP_API_TIMEOUT_MS | Frontend request timeout; defaults to 30 minutes |

### Optional integrations

| Integration | Variables |
| --- | --- |
| YouTube Data API | YOUTUBE_API_KEY |
| YouTube OAuth | GOOGLE_CLIENT_SECRETS_FILE |
| Firebase authentication | REACT_APP_FIREBASE_*, FIREBASE_SERVICE_ACCOUNT_KEY_PATH |
| OpenAI reports | OPENAI_API_KEY |
| AWS S3 | AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME |
| SMTP email | EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL |

Credential files must exist inside the environment where the backend runs. For Docker or hosted deployments, provide them through a secret or volume mechanism rather than committing them to the repository.

## Local development without Docker

The Docker path is the recommended first run. For direct development, install the lightweight backend dependencies and frontend dependencies separately.

### Backend

PowerShell:

~~~powershell
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r backend/requirement.demo.txt
$env:DJANGO_SECRET_KEY = "local-development-only"
python backend/manage.py check
python backend/manage.py test --noinput
python backend/manage.py runserver 8000
~~~

macOS or Linux:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirement.demo.txt
export DJANGO_SECRET_KEY=local-development-only
python backend/manage.py check
python backend/manage.py test --noinput
python backend/manage.py runserver 8000
~~~

The full media-processing stack is listed in [backend/requirement.txt](backend/requirement.txt). It may also require platform-specific system tools and substantially more disk space, memory, and installation time than the demo environment.

### Frontend

In a second terminal:

~~~powershell
cd frontend
npm ci
npm start
~~~

The frontend uses `REACT_APP_API_BASE_URL` to locate the backend. The default is `http://localhost:8000/api/`.

## API surface

Unless noted otherwise, processing and YouTube endpoints require an authenticated JWT request.

### Health and session

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /health/ | Database, cache, and memory health check |
| GET | /api/csrf/ | Bootstrap a CSRF cookie/token |
| POST | /api/auth/google-login/ | Exchange a Firebase token for application JWTs |

### Video and processing

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET / POST | /api/fetch-video/ | Fetch YouTube metadata |
| GET / POST | /api/download-video/ | Download a source video |
| POST | /api/fetch-data/ | Fetch extended video metadata |
| GET | /api/videos/<video_id>/ | Resolve a stored video URL |
| POST | /api/process_short_form_video/ | Generate short-form clips |
| POST | /api/seo/ | Run selected SEO, quality, or audio processing |
| POST | /api/optimize_shortform/ | Optimize a generated short-form clip |
| POST | /api/check-resolution/ | Inspect video resolution |
| POST | /api/generate-report/ | Generate an analysis report |

### YouTube integration

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/youtube/check-auth/ | Check stored YouTube authorization |
| GET | /api/youtube/authorize/ | Start YouTube OAuth |
| GET / POST | /api/youtube/callback/ | Receive the OAuth callback |
| GET | /api/youtube/get-auth-url/ | Generate an authorization URL |
| POST | /api/youtube/upload/ | Upload a processed video |
| POST | /api/youtube/update-seo/ | Update metadata on an owned video |

## Code quality and verification

Run the following checks before opening a pull request:

~~~powershell
docker compose config --quiet
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test --noinput
docker compose exec frontend npm run build
~~~

The backend view layer is split by responsibility instead of keeping all handlers in one module. The `app.views` facade preserves the existing route imports in [`backend/app/urls.py`](backend/app/urls.py).

## Project layout

~~~text
.
├── backend/                  # Django project, API, and processing code
├── frontend/                 # React application
├── requirements.txt          # repository-level dependency manifest
├── docker-compose.yml        # local demo orchestration
└── .env.example              # Docker configuration template
~~~

Dependency manifests:

- [backend/requirement.demo.txt](backend/requirement.demo.txt) — lightweight Docker demo dependencies.
- [backend/requirement.txt](backend/requirement.txt) — full backend and media-processing dependencies.
- [requirements.txt](requirements.txt) — repository-level development dependency manifest.

## Security and public-repository notes

- Do not use real credentials in `.env.example` or documentation.
- Keep `DEBUG=False` and secure cookies enabled outside local HTTP testing.
- Rotate any credential that appeared in previous private Git history before publishing the repository. Removing a secret from the current tree does not invalidate the old credential.
- The demo uses Django’s development server and local SQLite storage; use a production WSGI/ASGI server, managed database, secret manager, and proper object storage configuration for deployment.

## Contributing

Small fixes and documentation improvements are welcome. Before submitting a change:

1. Keep secrets and generated files out of Git.
2. Preserve existing API paths and response contracts unless the change explicitly updates the contract.
3. Run the backend checks and frontend build listed above.
4. Describe external services or credentials needed to exercise the change.

## License

No project license file is currently included. Until a license is added, treat the repository as source-available rather than assuming permission to reuse or redistribute it.
