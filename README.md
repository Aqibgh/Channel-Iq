# Channel IQ

Channel IQ is a React and Django application for YouTube video analysis, SEO generation, and video processing.

The application source lives under [`test3-main/`](test3-main/). The repository intentionally does not contain credentials, cookies, databases, TLS keys, generated build output, or dependency directories.

## Run the demo with Docker

Prerequisites: Docker Desktop with Compose v2 and, if the repository's LFS binaries are needed, Git LFS.

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

- Frontend: <http://localhost:3000>
- Backend health: <http://localhost:8000/health/>

The frontend shell renders without Firebase configuration. Google sign-in and Firebase-backed persistence require the `REACT_APP_FIREBASE_*` values in `.env`; the backend health endpoint and basic Docker startup do not require Firebase, YouTube, OpenAI, AWS, or Google OAuth credentials. Add those values only in local or deployment secret storage. Docker generates a local Django signing key in the named `backend_data` volume when `DJANGO_SECRET_KEY` is blank.

The default demo runs with `DEBUG=False` and secure cookies enabled. If you intentionally test authenticated flows over plain HTTP on localhost, set `DEBUG=True` and `SECURE_COOKIES=False` in `.env`; never use those settings for an internet-facing deployment.

To stop the demo:

```powershell
docker compose down
```

## Configuration

Use [`.env.example`](.env.example) as the Docker template. For direct local development, use [`backend/.env.example`](test3-main/backend/.env.example) and [`frontend/.env.example`](test3-main/frontend/.env.example). Never commit `.env` or credential JSON files.

The YouTube OAuth client secret and Firebase service-account JSON are supplied through `GOOGLE_CLIENT_SECRETS_FILE` and `FIREBASE_SERVICE_ACCOUNT_KEY_PATH`. YouTube cookies are optional and must be generated locally with the management command when needed.

Video-processing code prefers the bundled Windows executables when available, then falls back to `ffmpeg` and `exiftool` on PATH. The lightweight Docker demo keeps those full media dependencies out of the startup image; install the full backend requirements and system tools for processing deployments. The repository's current remote has Git LFS disabled, so the historical Windows executable objects may remain unavailable until the owner restores LFS storage. The demo's API timeout defaults to 30 minutes and can be changed with `REACT_APP_API_TIMEOUT_MS`.

## Project layout

```text
.
├── docker-compose.yml       # local demo stack
└── test3-main/
    ├── backend/             # Django API and processing pipeline
    └── frontend/            # React client
```

## Public-release note

Before changing the GitHub repository visibility, rotate any credentials that were ever stored in the old private history, including Google OAuth, Firebase service-account, YouTube, AWS, email, and TLS credentials. History cleanup is local and reversible until the rewritten branch is explicitly reviewed and pushed.
