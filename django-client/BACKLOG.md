## ✅ Epics Overview

- [ ]  **Backup & Recovery**
- [ ]  **Advanced Table Tools**
- [ ]  **Flexible CSV Import System**
- [ ]  **Record Enhancements**
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

- [ ]  Backend/API pagination implemented
- [ ]  Page size selectable (25/50/100)
- [ ]  Pagination preserves active sorting and filters

---

### Story: Add Sorting & Filters

**As a** user  
**I want** sortable columns and multi-field filtering  
**So that** I can analyse my data efficiently

**Acceptance Criteria**

- [ ]  All visible columns are sortable
- [ ]  Filters: date range, item name, price range, postcode, notes
- [ ]  Filters can be combined
- [ ]  Works with pagination and maintains state on page change/refresh

---

### Story: Global Search

**As a** user  
**I want** a global search box  
**So that** I can quickly find matching records

**Acceptance Criteria**

- [ ]  Full-text search across item name, notes, postcode, currency
- [ ]  Search narrows results in the current view
- [ ]  Works alongside filters, sorting, and pagination

---

# Epic: Flexible CSV Import System

_Configurable CSV formats + wizard-based import flow._

---

### Story: CSV Format Profile Manager

**As an** admin  
**I want** to create and manage CSV format profiles  
**So that** users can import differently structured CSVs

**Acceptance Criteria**

- [ ]  Define profiles with: delimiter, header→field mappings, date format
- [ ]  Validation ensures required internal fields are mapped
- [ ]  Profiles stored in the database
- [ ]  UI to create, edit, duplicate, and delete profiles

---

### Story: Select Format During Upload

**As a** user  
**I want** to choose a CSV format before uploading  
**So that** the file is parsed correctly

**Acceptance Criteria**

- [ ]  Upload page includes a dropdown of saved CSV profiles
- [ ]  Backend parsing applies the selected mapping and delimiter
- [ ]  Friendly error messages for missing columns or bad data types

---

### Story: CSV Import Wizard with Auto‑Detection

**As a** user  
**I want** a wizard-style guided import  
**So that** the system helps me interpret files

**Acceptance Criteria**

- [ ]  Step 1: Upload file
- [ ]  Step 2: Auto-detect separator, date format, and column candidates
- [ ]  Step 3: Let user confirm/adjust column→field mappings (with preview rows)
- [ ]  Step 4: Option to save the configuration as a new CSV profile

---

# Epic: Record Enhancements

_Unique IDs, notes field, and inline editing support._

---

### Story: Add Unique IDs to Records

**As a** developer  
**I want** each record to have a unique identifier  
**So that** I can reference entries reliably

**Acceptance Criteria**

- [ ]  Add UUID primary key (or ensure stable unique ID)
- [ ]  Migration safely updates existing data
- [ ]  ID shown in UI (compact styling)

---

### Story: Add Notes to Entries

**As a** user  
**I want** to add notes to sales/purchase entries  
**So that** I can annotate unusual or important items

**Acceptance Criteria**

- [ ]  Notes field added to model
- [ ]  UI to edit notes inline or via modal
- [ ]  Notes included in search/filtering

---

### Story: Inline Editing (Selected Fields)

**As a** user  
**I want** to edit certain fields inline  
**So that** I can correct small errors quickly

**Acceptance Criteria**

- [ ]  Editable fields: notes, item name, date
- [ ]  Optional: change history/audit trail retained

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

### Story: Scheduled Report Emails

**As a** user  
**I want** reports emailed automatically  
**So that** I don’t have to remember to generate them

**Acceptance Criteria**

- [ ]  Scheduled job (cron/Celery beat) generates PDFs using presets
- [ ]  Emails PDF to configured address(es)
- [ ]  Visible status/history of last scheduled run

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
