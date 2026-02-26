## ✅ Epics Overview

- [ ]  **Backup & Recovery**
- [x]  **Advanced Table Tools**
- [x]  **Flexible CSV Import System**
- [x]  **Record Enhancements**
- [ ]  **Reporting & PDF Generation**
- [ ]  **Usability & Deployment**

---

# Epic: Backup & Recovery

_Features enabling manual exports, automated scheduled backups, and remote cloud backup uploads._

---

### Story: Manual Database Export

**As a** user
**I want** to manually export the database
**So that** I can keep offline backups

**Acceptance Criteria**

- [ ]  User can trigger an export via UI
- [ ]  Supports DB dump **or** CSV/JSON export per table
- [ ]  Provides downloadable file/link
- [ ]  Displays a clear error if export fails

---

### Story: Automated Scheduled Backups

**As a** user
**I want** automatic scheduled backups
**So that** my data is preserved without manual intervention

**Acceptance Criteria**

- [ ]  Admin UI to configure frequency (daily/weekly/monthly)
- [ ]  Scheduled job (cron/Celery beat) generates backups
- [ ]  Backups stored locally (e.g., `/backups`)
- [ ]  Retention policy keeps last **N** backups

---

### Story: Remote Backup Destinations (Google Drive)

**As a** user
**I want** backups uploaded to Google Drive
**So that** backups are stored offsite

**Acceptance Criteria**

- [ ]  OAuth login/connection to Google Drive
- [ ]  Automatic upload after backup completes
- [ ]  UI shows status of last successful upload and timestamp
- [ ]  Retry on failure with error logs/alerts

---

# Epic: Advanced Table Tools

_Sorting, filtering, pagination, and global search to support large datasets._

---

### Story: Add Pagination

**As a** user
**I want** paginated tables
**So that** I can browse large datasets easily

**Acceptance Criteria**

- [x]  Backend/API pagination implemented
- [x]  Page size selectable (25/50/100)
- [x]  Pagination preserves active sorting and filters

---

### Story: Add Sorting & Filters

**As a** user
**I want** sortable columns and multi-field filtering
**So that** I can analyse my data efficiently

**Acceptance Criteria**

- [x]  All visible columns are sortable
- [x]  Filters: date range, item name, price range, postcode, notes
- [x]  Filters can be combined
- [x]  Works with pagination and maintains state on page change/refresh

---

# Epic: Flexible CSV Import System

_Configurable CSV formats + wizard-based import flow._

---

### Story: CSV Format Profile Manager

**As an** admin
**I want** to create and manage CSV format profiles
**So that** I can import differently structured CSVs and have them map to our internal model for the data

**Acceptance Criteria**

- [x]  Define profiles for either sales or purchases (the internal models are different)
- [x]  Define profiles with: delimiter, header→field mappings, date format
- [x]  Validation ensures required internal fields are mapped
- [x]  Profiles stored in the database

---

### Story: CSV Import

**As an** admin
**I want** to be able to select the format for my csv
**So that** the system correctly imports the data

**Acceptance Criteria**

- [x] admin can select the format from a dropdown
- [x] format comes from database of CSV format profiles

---

# Epic: Record Enhancements

_Unique IDs, notes field, and inline editing support._

---

### Story: Add Notes to Entries

**As a** user
**I want** to add notes to sales/purchase entries
**So that** I can annotate unusual or important items

**Acceptance Criteria**

- [x]  Notes field added to model
- [x]  UI to edit notes inline or via modal
- [x]  Notes included in search/filtering

---

# Epic: Reporting & PDF Generation

_PDF exports, report presets, scheduled reports._

---

### Story: PDF Export for Current View

**As a** user
**I want** to export the current table view as a PDF
**So that** I can share it with others

**Acceptance Criteria**

- [ ]  Export respects active filters, sorting, and columns
- [ ]  PDF includes totals (net, gross, profit) and date range metadata
- [ ]  Clean, printable layout (A4 portrait by default)

---

### Story: Saved Reporting Presets

**As a** user
**I want** to create report presets
**So that** I can run recurring reports quickly

**Acceptance Criteria**

- [ ]  Define preset name, time window (e.g., last 30 days, this month), and included fields
- [ ]  Presets saved to DB and listed in UI
- [ ]  One-click run generates report using current data

---

# Epic: Usability & Deployment

_UI polish and Docker improvements._

---

### Story: UI Refresh for Data Tables

**As a** user
**I want** a more usable table UI
**So that** I can work efficiently with long lists

**Acceptance Criteria**

- [ ]  Sticky table header
- [ ]  Scrollable table body
- [ ]  Responsive layout for small screens
- [ ]  Optional dark mode toggle

---

### Story: Improve Docker Deployment

**As a** developer
**I want** a production-ready container setup
**So that** deployment is reliable and repeatable

**Acceptance Criteria**

- [ ]  Multi-stage Dockerfile (small runtime image)
- [ ]  Healthcheck endpoint and container `HEALTHCHECK`
- [ ]  Persistent DB/data volume(s)
- [ ]  `.env` configuration support and documented environment variables
