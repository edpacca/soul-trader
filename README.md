<h3 style="color:goldenrod;">
Agentic assisted work disclosure
</h3>

_I initially developed this mini project in order to explore and investigate what it is like to develop whilst leaning heavily on agentic AI tooling. This work was done mostly with Devin session and batch modes. Although this application works and has more features than I would be able to produce manually in the same timeframe, I remain skeptical of the efficacy of producing large bodies of development work. In particular, the readability and composition of this application started to get out of hand - I am learning though, and I can see the power of such tooling. I think if one slowed just a little bit, planned properly and made use of PR reviewing tools then there is certainly potential for a lone developer to achieve quite a lot. Overall I'm fairly impressed, a little concerned and mildy baffled. I may come back and try a refactor at some point, either manually or with an agent. With that being said, have a nice day and continue..._

# Sales & Purchases Dashboard

A Django web application for managing sales and purchases records for a small business. Import data via CSV, filter and browse records, generate PDF reports, and track profitability — all through a simple web interface backed by PostgreSQL.

## Key Features

- **Configurable CSV import** — define format profiles with custom delimiters, date formats, and column mappings to import CSVs from any source
- **Dashboard** — view total sales, total purchases, and net profit across a configurable date range
- **Filtering & sorting** — filter by date, item name, price range, post code, source, and notes; sort by any column
- **PDF reports** — export sales, purchases, or a combined business report as a PDF; reports respect active filters and date ranges
- **Report presets** — save named presets (e.g. "This Month – Sales") and run them in one click
- **CSV & database export** — export records as CSV or take a full PostgreSQL dump for backup and restore
- **Notes** — add inline notes to individual records; browse all notes from a dedicated page
- **Sources** — tag records with a named source for grouping and filtering

## Quick Start

### Prerequisites

- Docker and Docker Compose installed

### Setup

1. Start the application:
   ```bash
   docker compose up --build
   ```

2. In a separate terminal, create a superuser:
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```
   Migrations run automatically on startup.

3. Access the application:
   - Dashboard: http://localhost:8000/
   - Django Admin: http://localhost:8000/admin/

## Importing CSV Data

CSV imports are managed through the Django Admin:

1. Log in at http://localhost:8000/admin/
2. Create a CSV Format Profile under Records > CSV Format Profiles, specifying the delimiter, date format, and a mapping of column index to field name
3. Navigate to CSV Uploads > Add CSV Upload, select the record type, choose the format profile, and upload the file
4. The system validates, deduplicates (by UUID), and imports the records

Sample CSV files are provided in the `sample_data/` directory.

## Application Pages

| URL | Description |
|-----|-------------|
| `/` | Dashboard — summary and date-range filter |
| `/sales/` | Sales records — filter, sort, paginate, export |
| `/purchases/` | Purchase records — filter, sort, paginate, export |
| `/notes/` | All annotated records |
| `/reports/` | Saved report presets |
| `/admin/` | Django admin — import, manage records, export data |

## Local Development (without Docker)

Requires Python 3.x. Uses SQLite instead of PostgreSQL.

```bash
pip install -r requirements.txt
python manage.py migrate --settings=config.settings_local
python manage.py createsuperuser --settings=config.settings_local
python manage.py runserver --settings=config.settings_local
```

The application will be available at http://localhost:8000/.

## Running Tests

```bash
# Via Docker
docker compose exec web python manage.py test

# Locally (uses in-memory SQLite)
python manage.py test --settings=config.settings_test
```

## Project Structure

```
django-client/
├── config/                  # Django project configuration
│   ├── settings.py          # Production settings (PostgreSQL)
│   ├── settings_local.py    # Local dev settings (SQLite)
│   ├── settings_test.py     # Test settings (in-memory SQLite)
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI entry point
├── apps/
│   └── records/             # Main application
│       ├── models.py        # SalesRecord, PurchaseRecord, CSVUpload, CSVFormatProfile, ReportPreset, Source
│       ├── admin.py         # Admin: CSV upload processing, format profiles, DB export
│       ├── forms.py         # CSVUploadForm, CSVFormatProfileForm
│       ├── views.py         # Dashboard, detail, notes, presets, PDF and CSV export
│       ├── urls.py          # App URL routes
│       ├── services/
│       │   ├── csv_parser.py      # Profile-driven CSV parsing
│       │   ├── aggregation.py     # Filtering, sorting, totals
│       │   ├── export_service.py  # CSV and PostgreSQL dump export
│       │   └── presets.py         # Time-window resolution for report presets
│       ├── templatetags/    # Custom template tags
│       ├── templates/       # App-specific templates
│       └── tests/           # Automated tests
├── templates/               # Base templates
├── static/css/              # Stylesheets
├── sample_data/             # Example CSV files
├── Dockerfile               # Container definition
├── docker-compose.yml       # Multi-service orchestration
└── manage.py                # Django management script
```

## Restoring from a Database Dump

Requires Docker. The dump must have been created using the DB Dump export in the Admin.

```bash
# Start the database only
docker compose up -d db

# Drop and recreate the database
docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS django_client; CREATE DATABASE django_client;"

# Restore the dump
cat db_dump_YYYY-MM-DD.sql | docker compose exec -T db psql -U postgres -d django_client

# Start the web service
docker compose up web
```

The dump includes all Django tables, so migrations are not required after restore. Create a new superuser if the original is not included in the dump.

## Notes

- The **root `README.md`** (`/README.md`) currently describes an entirely unrelated blockchain data platform and should be replaced or removed — it will mislead anyone landing on the repository.
- The `.env.example` file referenced in the current README does not exist in the repository. The proposed README above removes that step since the `docker-compose.yml` uses environment variables with sensible defaults for local use. If specific environment variables need to be documented, a small table could be added.
- PDF generation uses [WeasyPrint](https://weasyprint.org/) and only activates when `DEBUG=False` (i.e. inside Docker). In local dev mode it renders as HTML instead.
