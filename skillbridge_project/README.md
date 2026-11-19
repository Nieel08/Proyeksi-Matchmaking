# SkillBridge accounts

The `accounts` app owns registration, campus-email OTP verification, session login,
profile updates, and user skill tags. The profile and authentication routes are
JSON endpoints protected by Django sessions and CSRF middleware. `Project`,
`ProjectRole`, `Invitation`, and `Collaboration` are schema-only models; no
matchmaking, project, invitation, or collaboration workflows are implemented.

NPM is stored as a unique string (8-15 ASCII digits). OTP verifies control of the
provided email; verifying that an NPM belongs to a student requires an
institutional registry/integration that is not present here. Set
`CAMPUS_EMAIL_DOMAIN` to restrict registration to the known campus email domain.

## Run locally

From this directory in the VS Code terminal:

1. Activate the existing virtual environment: `.\venv\Scripts\Activate.ps1`
2. Set `DJANGO_SECRET_KEY` in the terminal environment (or VS Code launch
   environment). Keep `.env` local; Django does not read `.env` automatically.
   `DJANGO_DEBUG` defaults to true for local development.
3. Generate and apply migrations:

   ```powershell
   python manage.py makemigrations accounts
   python manage.py migrate
   ```

4. Start the server with `python manage.py runserver`. The development email
   backend prints OTP messages in the terminal.
5. Run checks/tests with `python manage.py check` and `python manage.py test accounts`.

Before pushing, keep `.env`, `db.sqlite3`, and `venv/` out of Git (covered by
`.gitignore`). For deployment, provide a strong `DJANGO_SECRET_KEY`, turn
`DJANGO_DEBUG` off, configure allowed hosts and SMTP, and use HTTPS.

The existing local `db.sqlite3` in this checkout predates the custom user model
and has built-in admin/auth migrations recorded already. Django reports an
inconsistent migration history for that file; it was left unchanged. A fresh
checkout (without a local database file) can use the commands above directly.
To preserve this existing file and work against a fresh database instead, set
`$env:DB_NAME = "$PWD\skillbridge-fresh.sqlite3"` in PowerShell before running
migrations and the server.

## API outline

All paths are prefixed with `/api/`. Fetch `/api/csrf/` first and send its
`csrfToken` as `X-CSRFToken` on unsafe requests. Fetch it again after login,
which rotates the CSRF token. JSON request bodies are used below; browser form
POSTs are also accepted where applicable.

- `POST auth/register/`: `full_name`, `gender`, `admission_year`, `npm`, `email`,
  `password`; sends an OTP and never returns it.
- `POST auth/verify-email/`: `email`, `code`.
- `POST auth/login/`: `email`, `password`; creates a session only after verification.
- `POST auth/logout/`.
- `GET profile/` and `PUT`/`PATCH profile/update/`: profile name, gender,
  admission year, GitHub profile URL, and `ready`/`busy` availability.
- `POST profile/skills/` with `name`; `PUT`/`PATCH profile/skills/<id>/` with
  `name`; `DELETE profile/skills/<id>/delete/`.

Profile and skill routes require an authenticated, verified account. OTP values
are hashed at rest, expire after 10 minutes, and are limited to five attempts.
