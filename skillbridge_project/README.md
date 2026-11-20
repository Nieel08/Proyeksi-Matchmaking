# SkillBridge accounts

The `accounts` app owns registration, campus-email OTP verification, session login,
profile updates, and user skill tags. The profile and authentication routes are
JSON endpoints protected by Django sessions and CSRF middleware. The root page
is an information-rich public landing page and searchable directory for verified
student and lecturer profiles, with availability and skill filters. Verified,
logged-in users can invite a candidate to a role in one of their own projects;
sent invitations and their statuses are shown on the same page.

Student NPM is stored as a unique string (8-15 ASCII digits); lecturer profiles
do not require an NPM or student admission year. OTP verifies control of the
provided email; verifying that an NPM belongs to a student requires an
institutional registry/integration that is not present here. Set
`CAMPUS_EMAIL_DOMAIN` to restrict registration to the known campus email domain.

## Run locally

From this directory in the VS Code terminal:

1. Activate the existing virtual environment: `.\venv\Scripts\Activate.ps1`
2. Set `DJANGO_SECRET_KEY` in the terminal environment (or VS Code launch
   environment). Keep `.env` local; Django does not read `.env` automatically.
   `DJANGO_DEBUG` defaults to true for local development.
3. Apply the existing migrations to create the database tables:

   ```powershell
   python manage.py migrate
   ```

   By default, the app uses `skillbridge.sqlite3`. This keeps the older
   `db.sqlite3` intact; it was created with Django's built-in user model and
   cannot be migrated safely to the current custom user model. To use a
   different database, set `DB_NAME` before running Django commands.
4. (Optional) add sample members, skills, and projects:

   ```powershell
   python manage.py seed_demo_data
   ```

   This command is safe to rerun. It creates 19 sample profiles, skill tags, and
   three example projects. Sample accounts are marked **Demo** and cannot log in.
5. Create an admin account with `python manage.py createsuperuser`. For gender,
   enter the displayed code: `male`, `female`, or `other` (not the Indonesian
   label or another term).
6. Start the server with `python manage.py runserver`. The development email
   backend prints OTP messages in the terminal.
7. Run checks/tests with `python manage.py check` and `python manage.py test accounts`.

Before pushing, keep `.env`, `db.sqlite3`, and `venv/` out of Git (covered by
`.gitignore`). For deployment, provide a strong `DJANGO_SECRET_KEY`, turn
`DJANGO_DEBUG` off, configure allowed hosts and SMTP, and use HTTPS.

The existing local `db.sqlite3` in this checkout predates the custom user model
and has built-in admin/auth migrations recorded already. Django reports an
inconsistent migration history for that file; it is left unchanged. The
default `skillbridge.sqlite3` database can be initialized with the commands
above and includes the custom `users` table and the related application tables.

## API outline

All paths are prefixed with `/api/`. Fetch `/api/csrf/` first and send its
`csrfToken` as `X-CSRFToken` on unsafe requests. Fetch it again after login,
which rotates the CSRF token. JSON request bodies are used below; browser form
POSTs are also accepted where applicable.

- `POST auth/register/`: `full_name`, `gender`, `email`, `password`, and optional
  `user_type` (`student` or `lecturer`) and `academic_program`. Students must
  provide `admission_year` and `npm`; lecturers do not. Sends an OTP and never
  returns it.
- `POST auth/verify-email/`: `email`, `code`.
- `POST auth/login/`: `email`, `password`; creates a session only after verification.
- `POST auth/logout/`.
- `GET profile/` and `PUT`/`PATCH profile/update/`: profile name, gender,
  admission year, academic program, GitHub profile URL, and `ready`/`busy`
  availability.
- `POST profile/skills/` with `name`; `PUT`/`PATCH profile/skills/<id>/` with
  `name`; `DELETE profile/skills/<id>/delete/`.

Profile and skill routes require an authenticated, verified account. OTP values
are hashed at rest, expire after 10 minutes, and are limited to five attempts.
