# Django Sales & Purchases Dashboard

A skeleton Django application for uploading, querying, and viewing aggregated sales and purchase data. Runs via Docker with PostgreSQL.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed

### Setup

1. Copy the environment file:

   ```bash
   cp .env.example .env
   ```

2. Start the application:

   ```bash
   docker-compose up --build
   ```

3. In a separate terminal, run migrations and create a superuser:

   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

4. Access the application:
   - **Main Dashboard:** http://localhost:8000/
   - **Django Admin:** http://localhost:8000/admin/

> **Note:** When using `docker-compose up` the web service automatically runs migrations on startup, so step 3's migrate command is only needed if you want to run it manually or if the automatic migration didn't complete.

## Uploading CSV Data

1. Log in to the Django Admin at http://localhost:8000/admin/
2. Navigate to **CSV Uploads > Add CSV Upload**
3. Select the record type (Sales or Purchase)
4. Upload a CSV file
5. The system will parse, validate, and import the records

### CSV Format

The CSV must include a header row with these columns:

| Column | Required | Description |
|---|---|---|
| `date` | Yes | Date in `YYYY-MM-DD`, `DD/MM/YYYY`, or `MM/DD/YYYY` format |
| `item_name` | Yes | Name of the item |
| `quantity` | Yes | Positive integer |
| `unit_price` | Yes | Decimal number |
| `total_price` | Yes | Decimal number |
| `shipping_cost` | Yes | Decimal number |
| `post_code` | Yes | Postal/ZIP code |
| `currency` | No | 3-letter currency code (defaults to GBP) |

Sample CSV files are provided in the `sample_data/` directory.

## Main Dashboard

The dashboard at http://localhost:8000/ allows you to:

- Select a date range using the start and end date pickers
- View a summary showing total sales, total purchases, and net profit
- Browse individual sales and purchase records in tables

## Local Development (without Docker)

You can run the application locally using SQLite instead of PostgreSQL. This is convenient for development and does not require Docker.

> **Note:** This setup is for development only. Production deployments should use PostgreSQL via Docker.

### Prerequisites

- Python 3.x installed
- Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```

### Run Migrations

```bash
python manage.py migrate --settings=config.settings_local
```

### Create a Superuser

```bash
python manage.py createsuperuser --settings=config.settings_local
```

### Start the Development Server

```bash
python manage.py runserver --settings=config.settings_local
```

The application will be available at http://localhost:8000/.

## Running Tests

Tests use Django's built-in test framework. A dedicated test settings file (`config/settings_test.py`) uses an in-memory SQLite database so tests can run without PostgreSQL.

```bash
# Via Docker (uses PostgreSQL)
docker-compose exec web python manage.py test

# Locally without PostgreSQL (uses SQLite in-memory)
python manage.py test --settings=config.settings_test
```

## Project Structure

```
django-client/
├── config/                  # Django project configuration
│   ├── settings.py          # Settings (DB, apps, middleware)
│   ├── settings_local.py    # Local dev settings (SQLite)
│   ├── settings_test.py     # Test settings (in-memory SQLite)
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI entry point
├── apps/
│   └── records/             # Main application
│       ├── models.py        # SalesRecord, PurchaseRecord, CSVUpload
│       ├── admin.py         # Admin with CSV upload processing
│       ├── views.py         # Dashboard view
│       ├── urls.py          # App URL routes
│       ├── services/        # Business logic layer
│       │   ├── csv_parser.py    # CSV parsing (strategy pattern)
│       │   └── aggregation.py   # Data aggregation service
│       ├── templates/       # App-specific templates
│       └── tests/           # Automated tests
├── templates/               # Base templates
├── static/css/              # Stylesheets
├── sample_data/             # Example CSV files
├── Dockerfile               # Container definition
├── docker-compose.yml       # Multi-service orchestration
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── manage.py                # Django management script
```

## Design Decisions

### CSV Extensibility

CSV parsing uses the **Strategy pattern** via the abstract `CSVParser` base class in `apps/records/services/csv_parser.py`. The current `DefaultCSVParser` handles the fixed schema. To add new formats:

1. Create a new class extending `CSVParser`
2. Implement the `parse()` method with the new mapping logic
3. Register it in the admin or add a format selector to the upload form

### Future Charting

The aggregation logic is isolated in `AggregationService` (`apps/records/services/aggregation.py`), separate from views. This makes it straightforward to:

- Add new endpoints returning JSON for chart libraries
- Extend the summary with additional metrics
- Plug in any JavaScript charting library on the frontend

### Separation of Concerns

- **Models** (`models.py`): Data persistence only
- **Services** (`services/`): Business logic (parsing, aggregation)
- **Views** (`views.py`): HTTP request handling, delegates to services
- **Admin** (`admin.py`): Admin interface, delegates CSV processing to services
