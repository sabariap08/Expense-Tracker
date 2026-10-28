# Expense Tracker

A single-user personal expense tracker built with Flask, MongoDB Atlas, Jinja templates, and ReportLab. It records credit and debit transactions, calculates statistics from the stored data, supports search/filter/edit/delete, and generates printer-friendly PDF reports on the server.

This is a personal records tool. The "net balance" is calculated from the transactions recorded in the app; it is not a verified bank balance.

## Features

- Single authorized user configured through environment variables.
- Session-based login, CSRF protection, secure cookie settings, and no public registration.
- Add and edit credit/debit transactions with radio buttons, a date defaulting to today, categories, payment method, and notes.
- Server-side validation for type, title, amount, date, category, and field lengths.
- Persistent MongoDB Atlas storage with `Decimal128` monetary values.
- Dashboard totals: all-time credits, debits, net balance, transaction count, and current-month equivalents.
- Six-month credit/debit trend, debit spending by category, and recent transactions.
- Transaction table with keyword search, type/category/date filters, date sorting, and pagination.
- PDF reports filtered by date range, type, category, and keyword. Reports include every matching transaction, totals, repeating headers across pages, and a fixed filename format.
- Responsive, plain interface with no registration, multi-user, AI, or marketing features.

## Technology

- Python 3.11+ / Flask 3
- MongoDB Atlas via PyMongo
- Jinja2 server-rendered templates
- Vanilla JavaScript and Chart.js loaded from a CDN for the dashboard charts
- ReportLab for PDF generation
- Flask-WTF for CSRF protection
- Werkzeug password hashing
- Gunicorn for production

## Project structure

```text
expense-tracker/
├── app.py                     # Application factory, security headers, error handlers
├── wsgi.py                    # WSGI entry point and local server runner
├── config.py                  # Environment-based configuration
├── database.py                # MongoDB connection and indexes
├── auth.py                    # Login, logout, login_required
├── dashboard.py               # Dashboard statistics and charts
├── transactions.py            # Transaction CRUD, search, filters, pagination
├── reports.py                 # Report filters and PDF download
├── utils/
│   ├── categories.py
│   ├── dates.py
│   ├── filters.py
│   ├── money.py
│   ├── pdf.py
│   ├── stats.py
│   ├── validation.py
│   └── generate_password_hash.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── transactions.html
│   ├── transaction_form.html
│   ├── transaction_detail.html
│   ├── reports.html
│   └── error.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_transactions.py
│   └── test_reports.py
├── requirements.txt
├── requirements-dev.txt
├── Procfile
├── .env.example
├── .gitignore
└── README.md
```

## Configuration

Create `.env` from `.env.example` and fill in your own values. Never commit `.env`.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Long random value used to sign sessions and CSRF tokens. Generate a new one for production. |
| `MONGODB_URI` | MongoDB Atlas connection string, including the database user password. |
| `MONGODB_DATABASE` | Database name. Recommended: `expense_tracker`. |
| `APP_USERNAME` | Your single login username/email. |
| `APP_PASSWORD` | Plain password for login (easier for testing). OR use `APP_PASSWORD_HASH`. |
| `APP_PASSWORD_HASH` | Werkzeug hash of your password (more secure). Keep it in single quotes because the hash contains `$` characters. |
| `FLASK_DEBUG` | `False` in production. |
| `APP_TIMEZONE` | Calendar timezone for "today" and "current month", e.g. `Asia/Kolkata` or `UTC`. |
| `SESSION_COOKIE_SECURE` | `True` for HTTPS. Set to `False` only for local plain HTTP development. |
| `SESSION_LIFETIME_HOURS` | Session and CSRF lifetime in hours. Default `12`. |

Generate a secret key (the app refuses to start if it is missing, still the placeholder, or shorter than 32 characters):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Generate the password hash from the project root:

```bash
python utils/generate_password_hash.py
```

Copy the printed `APP_PASSWORD_HASH='...'` line into `.env`, including the single quotes. The quotes prevent the `$` characters in the hash from being treated as environment-variable expansion. The utility uses Werkzeug's `generate_password_hash`, and login verifies it with `check_password_hash`. Passwords are never stored in the database or written to logs.

> **Local HTTP note:** if you open the app at `http://127.0.0.1:5000` and the login appears to succeed but you are returned to the login page, set `SESSION_COOKIE_SECURE=False` in `.env`. Secure cookies are only sent over HTTPS. Set it back to `True` for deployment.

## MongoDB Atlas setup

1. Create a free MongoDB Atlas cluster and project.
2. Create a database user under **Database Access**. Give it read/write access to the `expense_tracker` database, or use a comparable least-privilege role for personal use.
3. Under **Network Access**, add the IP address of your development machine. Add the outbound IP range used by your hosting provider for production. If your host does not offer static egress IPs, you may need to allow `0.0.0.0/0`; in that case use a strong unique database password and never publish the URI.
4. Click **Connect > Drivers** and copy the connection string. Replace `<password>` with the database user's password. URL-encode special characters in the password if needed.
5. Set `MONGODB_URI` and `MONGODB_DATABASE=expense_tracker` in `.env`.
6. Start the app. The `transactions` collection and indexes are created automatically on first successful connection. Existing data is never erased.

Indexes are created on `date`, `type`, `category`, `date + type`, and `date + category`.

## Local development

```bash
# from the project directory
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# edit .env with your values; use SESSION_COOKIE_SECURE=False for http://localhost
python utils/generate_password_hash.py
python wsgi.py
```

macOS / Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
# edit .env with your values; use SESSION_COOKIE_SECURE=False for http://localhost
python utils/generate_password_hash.py
python wsgi.py
```

Open `http://127.0.0.1:5000` and sign in with `APP_USERNAME` and the password you hashed.

The app binds to `127.0.0.1:5000` by default. You can override `HOST` and `PORT` environment variables when running `python wsgi.py`.

## Running tests

Tests use an in-memory `mongomock` database, so Atlas credentials are not required:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The test suite covers:

- Login page, correct and incorrect credentials, protected-route redirects, logout, and CSRF rejection.
- Credit/debit creation, today's default date, validation of amounts/dates/required fields, editing, deleting, and 404s.
- Search, filters, sorting, pagination, combined filters, and transaction isolation.
- Dashboard totals, current-month filtering, empty state, decimal precision, data persistence, and database-unavailable handling.
- PDF downloads with type/date/category/keyword filters, exact totals, all matching rows, multi-page output, and repeated table headers.

PDFs are parsed in tests with `pypdf` to verify their content.

**Not verified in this environment:** a live MongoDB Atlas connection, Atlas network-access configuration, and a deployed Gunicorn process. These require your credentials and hosting account. The application code paths are implemented and the database-dependent flows are tested with `mongomock`.

## Deployment (Render or similar)

1. Push the project to a Git repository. Confirm that `.env` is ignored and only `.env.example` is committed.
2. Create a **Web Service** on Render (or a similar Python host) from the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command (also provided in `Procfile`):
   ```bash
   gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
   ```
5. Add every environment variable in the hosting dashboard. The local `.env` file is **not** automatically uploaded or available in production:
   - `SECRET_KEY` (new production value)
   - `MONGODB_URI`
   - `MONGODB_DATABASE=expense_tracker`
   - `APP_USERNAME`
   - `APP_PASSWORD_HASH`
   - `FLASK_DEBUG=False`
   - `APP_TIMEZONE`
   - `SESSION_COOKIE_SECURE=True`
   - `SESSION_LIFETIME_HOURS=12`
6. Add the hosting provider's outbound IP range to MongoDB Atlas network access.
7. Deploy, open the URL, sign in, add a transaction, refresh, and download a PDF. Restart/redeploy and confirm the transaction is still present.

If the platform injects `PORT` differently, set the bind address to the value it provides. Gunicorn is Linux/Unix-oriented; on Windows use `python wsgi.py` locally instead.

## Data model

Transactions are stored in the `transactions` collection:

```text
{
  _id: ObjectId,
  type: "credit" | "debit",
  title: string,
  description: string,
  amount: Decimal128,
  date: datetime,          # calendar date stored as midnight UTC
  category: string,
  payment_method: string,
  notes: string,
  created_at: datetime,
  updated_at: datetime
}
```

Amounts are stored as MongoDB `Decimal128` and parsed/summed with Python `Decimal`; floating-point arithmetic is not used for totals. Chart values are converted to floats only for display. Dates are edited as `YYYY-MM-DD` and are interpreted as calendar dates. The configured `APP_TIMEZONE` determines today's default date and which calendar month is "current" on the dashboard.

## Security notes

- All private routes require an authenticated session.
- Passwords are verified against a Werkzeug hash from `APP_PASSWORD_HASH`; plaintext passwords are never stored.
- State-changing forms use CSRF tokens from Flask-WTF.
- Session cookies are HTTP-only, SameSite=Lax, and Secure by default for production; sessions expire after the configured lifetime.
- Inputs are validated server-side, trimmed, and length-limited.
- Search terms are regex-escaped; type/category/sort values are checked against fixed allowlists.
- Jinja autoescaping is used for all rendered values.
- Security headers include CSP, `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.
- Database connection errors are shown as generic error pages. Connection strings, passwords, and database identifiers are never rendered or logged.
- No registration, password recovery, multi-user management, or database reset endpoint exists.
- The app never seeds fake transactions.

## PDF reports

The Reports page posts the selected filters to the Flask backend. The backend re-validates the filters, fetches **all** matching transactions from MongoDB, calculates totals, and builds the PDF with ReportLab. Nothing is generated in the browser.

- Title: **Expense tracker**
- Columns: `S.No.`, `Date`, `Type (Credit/Debit)`, `Title`, `Description`, `Amount`
- Landscape A4, black text on white, light-gray header, thin gray borders
- Header repeats on every page
- Long descriptions wrap inside cells
- Amounts use two decimal places
- Summary: total credits, total debits, net balance, and transaction count
- Filename: `expense_tracker_report_YYYY-MM-DD.pdf`
- If no transactions match, the app shows a message instead of creating an empty/misleading report

## Troubleshooting

- **Login loops locally:** `SESSION_COOKIE_SECURE` must be `False` when using plain `http://localhost`. Return it to `True` in production.
- **"Database unavailable":** check `MONGODB_URI`, the database user's password, and MongoDB Atlas network access. Restart the app after fixing configuration.
- **Atlas authentication failure:** URL-encode special characters in the password inside the URI.
- **Charts not visible:** Chart.js is loaded from jsDelivr. The rest of the application works if the CDN is unavailable.
- **PDF header wraps unexpectedly:** the layout is tuned for the standard fonts; keep ReportLab at the pinned version unless you re-check column widths.
