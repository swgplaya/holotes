# Holotes

[![Tests](https://github.com/swgplaya/holotes/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/swgplaya/holotes/actions/workflows/tests.yml)

Holotes is an open-source, local-first management accounting system for small businesses.

The name comes from the Greek *holótēs* — wholeness: separate financial data brought together into one coherent system.

Holotes imports bank transactions, helps classify cash movements, builds management reports, plans future cash flows, calculates unit economics, creates local database backups, and can provide read-only financial summaries through a Telegram bot.

Financial data is stored locally in SQLite by default. The interface is available in Russian, English, and Simplified Chinese and supports light and dark themes.

> **Development status:** Holotes is preparing for its first tagged release, `v0.1.0`. This release is intended primarily for personal, local, single-user use. It is not yet designed for public server deployment or production multi-user access.

## Contents

- [Features](#features)
- [Important note](#important-note)
- [Technology stack](#technology-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Telegram bot](#telegram-bot)
- [Backup and restore](#backup-and-restore)
- [Testing and CI](#testing-and-ci)
- [Architecture](#architecture)
- [Local data, privacy, and security](#local-data-privacy-and-security)
- [Project structure](#project-structure)
- [Current limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Help add support for more banks](#help-add-support-for-more-banks)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

## Features

### Bank data

- Import and validate CSV statements exported from T-Business
- Normalize imported transactions before saving
- Prevent duplicate transactions using stable content hashes
- Track import batches and their source files
- Review transactions linked to a particular import
- Safely delete an import batch without removing transactions shared with another batch
- Delete old untracked transactions separately
- Use the included anonymized demonstration statement for testing
- Keep the application database local

### Classification

- Classify transactions independently for P&L and Cash Flow
- Include or exclude each transaction from either report
- Assign separate P&L and Cash Flow categories
- Track unclassified, partially classified, and fully classified transactions
- Preserve manual classification when automatic rules are applied
- Add comments to transaction classifications

### Automatic rules

- Create priority-based classification rules
- Filter rules by transaction direction
- Match all text fields or a selected field
- Use exact, contains, starts-with, and other supported matching modes
- Apply different actions to P&L and Cash Flow
- Enable, disable, and delete rules
- Export rules as versioned JSON
- Preview JSON imports before saving
- Import rules in merge or replace mode
- Detect duplicates inside a configuration file and against the database

### Reporting

- Build a cash-based P&L report
- Build a Cash Flow report
- Filter reports by period
- Compare with the previous period or the previous year
- Review inflows, outflows, net results, and category breakdowns
- Open transaction-level report details
- Visualize reports with interactive Plotly charts

### Payment calendar

- Create one-time, monthly, and yearly planned cash flows
- Plan future inflows and outflows
- Define categories, counterparties, comments, and recurrence end dates
- Activate, deactivate, and delete planned cash flows
- Expand recurring plans into dated occurrences
- Build a daily cash balance forecast
- Identify potential cash gaps

### Unit economics

- Manage products and cost items
- Configure planned sales volume
- Use manual price, markup, or target-margin pricing
- Add fixed costs per unit
- Add fixed costs per period
- Add percentage-based costs
- Round calculated prices upward to a selected step
- Calculate revenue, total cost, profit per unit, margin, operating result, and break-even volume
- Activate, deactivate, and delete products and costs

### Local operations

- Create downloadable SQLite database backups from the interface
- Preview uploaded backups before restoration
- Create a safety backup automatically before restoring a database
- Apply Alembic database migrations
- Launch the web interface and Telegram bot together
- Use a Windows `.bat` launcher without opening an IDE

### Telegram bot

- Run locally using long polling
- Store the bot token in `.env` without displaying the full saved token
- Restrict access by Telegram user ID and chat ID
- Configure the default summary period
- Use Russian, English, and Simplified Chinese responses
- Request read-only financial summaries
- Request a summary for a specific month
- Retrieve user and chat IDs for access configuration

### Interface

- Russian, English, and Simplified Chinese localization
- Light and dark themes
- Lazy rendering of the active tab
- Separate UI modules for the main application sections
- Interactive tables, forms, metrics, and charts

## Important note

The P&L report currently uses bank transactions and the cash method.

Holotes is a management reporting tool. It is not statutory accounting, tax, payroll, banking, audit, or regulatory reporting software. Calculations should be reviewed before they are used for business decisions.

The Telegram bot in `v0.1.0` is read-only, but it still exposes financial summaries to authorized Telegram accounts. Configure the allowed users and chats carefully and do not share the bot token.

## Technology stack

- Python 3.12
- Streamlit
- pandas
- SQLAlchemy
- SQLite
- Alembic
- Plotly
- pytest
- GitHub Actions

## Installation

Python 3.12 is recommended.

### Supported installation mode: local computer

The supported `v0.1.0` installation mode is a local Python environment on Windows, Linux, or macOS.

Docker images, server deployment instructions, authentication, and production multi-user configuration are planned for the next development cycle and are not part of the first release.

### 1. Clone the repository

```powershell
git clone https://github.com/swgplaya/holotes.git
cd holotes
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

### 3. Install application dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Run Holotes

#### Windows launcher

The easiest Windows option is:

```powershell
.\start_holotes.bat
```

The launcher supports three modes:

- press `Enter` or pass no argument — start the web interface and Telegram bot;
- enter `1` or run `start_holotes.bat 1` — start only the web interface;
- enter `2` or run `start_holotes.bat 2` — start only the Telegram bot.

The launcher uses the Python executable from `.venv` automatically.

#### Run both services with Python

```powershell
python run_holotes.py
```

#### Run only the web interface

```powershell
python -m streamlit run app.py
```

#### Run only the Telegram bot

```powershell
python -m src.telegram_bot
```

Streamlit prints the local application URL in the terminal. The SQLite database is created locally when the application starts.

## Usage

### Try the demonstration data

The repository includes an anonymized T-Business demonstration statement:

```text
demo_data/tbank_demo_statement.csv
```

Use it to test the import, classification, reporting, payment calendar, backup, and Telegram summary workflows without uploading real financial data.

### Import bank transactions

1. Open the **Import statement** tab.
2. Upload a CSV statement exported from T-Business, or use the demonstration CSV.
3. Review validation warnings and the transaction preview.
4. Save the transactions to the local database.
5. Use the import journal to inspect or safely remove a previous import batch.

Holotes calculates a stable content hash for every transaction and skips duplicates.

### Classify transactions

Open the **Classification** tab and decide independently whether each transaction should be:

- included in P&L;
- excluded from P&L;
- included in Cash Flow;
- excluded from Cash Flow.

P&L and Cash Flow decisions are independent. A transaction can be included in one report and excluded from the other.

When an operation is included in a report, a corresponding category is required.

### Create automatic rules

Open the **Rules** tab to create priority-based classification rules.

Rules can match:

- all text fields;
- counterparty name;
- counterparty INN;
- bank category;
- transaction description;
- payment purpose;
- MCC;
- tax code.

Higher-priority rules are evaluated before lower-priority rules.

Rule configurations can be exported as JSON and restored in another Holotes installation.

### Build reports

Open the reporting tabs to review:

- cash-based P&L;
- Cash Flow;
- period comparisons;
- financial KPIs;
- category breakdowns;
- transaction-level report details.

### Plan cash flows

Open the **Payment calendar** tab to create planned inflows and outflows, expand recurring plans, and calculate the expected daily cash balance.

### Calculate unit economics

Open the **Unit economics** tab to:

1. create a product;
2. set planned sales volume;
3. configure the pricing method;
4. add fixed and percentage-based cost items;
5. review price, cost, profit, margin, operating result, and break-even volume.

## Telegram bot

The current bot is designed for local, read-only access to financial summaries.

### Configure the token

1. Create a bot through Telegram's BotFather.
2. Start the Holotes web interface.
3. Open **Settings**.
4. Enter and validate the Telegram bot token.
5. Save it to `.env` through the interface.

The full saved token is not displayed after saving.

### Restrict access

Use the bot commands:

```text
/myid
/chatid
```

Add the required user IDs and chat IDs in the Holotes settings. Keep access restricted to trusted accounts.

### Available commands

```text
/help
/myid
/chatid
/summary
/summary YYYY-MM
```

Examples:

```text
/summary
/summary 2026-07
```

## Backup and restore

Database backup and restoration controls are available in **Settings**.

Recommended procedure before upgrades or major data changes:

1. create a backup;
2. download the backup file;
3. store a copy outside the project directory;
4. verify that the backup opens in the restoration preview;
5. only then continue with the upgrade or restoration.

Before restoring an uploaded database, Holotes creates an additional safety backup of the current database.

Real database backups contain financial data and must not be committed to Git or shared publicly.

## Testing and CI

Development dependencies are stored separately from application dependencies.

Install them with:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the complete test suite:

```powershell
python -m pytest -q
```

Run tests with detailed output:

```powershell
python -m pytest -v
```

Run a specific test file:

```powershell
python -m pytest tests/test_reporting.py -v
```

The automated suite covers:

- report calculations and period comparisons;
- classification summaries;
- payment calendar recurrence and balance forecasts;
- unit economics calculations and pricing validation;
- rule configuration JSON parsing and validation;
- SQLite repository CRUD operations;
- duplicate transaction imports;
- import-batch deletion and shared transaction preservation;
- manual classification and transaction rollback;
- rule priority, merge, replace, and automatic classification;
- database backup and restoration;
- Alembic migrations;
- demonstration data stability;
- Telegram token storage, settings, authorization, bot behavior, and financial summaries;
- application service launcher behavior;
- browser smoke tests.

Repository tests use isolated temporary SQLite databases. They do not modify the local application database.

GitHub Actions automatically runs checks after every push and pull request. The workflow is stored in:

```text
.github/workflows/tests.yml
```

Before a release or pull request, run:

```powershell
python -m compileall -q app.py src
python -m pytest -q
```

## Architecture

Holotes separates the application into several layers.

### Application entry points

- `app.py` configures Streamlit, initializes the database, manages top-level navigation, and delegates each section to a UI renderer.
- `run_holotes.py` launches Streamlit and the Telegram bot together.
- `start_holotes.bat` provides a Windows launcher for both services or either service separately.

### UI layer

`src/ui/` contains Streamlit renderers for:

- operations;
- transaction views;
- classification;
- rules;
- reports;
- imports;
- payment calendar;
- unit economics;
- settings;
- option formatting and UI data caching.

UI modules do not import `app.py`.

### Business logic

Pure or mostly pure calculation modules include:

- `src/reporting.py`;
- `src/classification_summary.py`;
- `src/payment_calendar.py`;
- `src/unit_economics.py`;
- `src/rule_config.py`;
- `src/telegram_summary.py`.

### Persistence and schema management

SQLAlchemy models and repository operations are implemented in:

- `src/models.py`;
- `src/database.py`;
- `src/transaction_repository.py`;
- `src/rule_repository.py`;
- repository functions in the payment calendar and unit economics modules.

Database migrations are managed through Alembic:

```text
migrations/
alembic.ini
```

### Backup, revisions, and caching

- `src/database_backup.py` handles database backup validation, creation, and restoration.
- `src/data_revision.py` tracks data changes for safe cache invalidation.
- `src/ui/data_cache.py` centralizes cached UI data access.

### Telegram integration

- `src/telegram_bot.py` implements long polling and command handling.
- `src/telegram_settings.py` stores bot settings and access restrictions.
- `src/telegram_token.py` manages the token in `.env`.
- `src/telegram_summary.py` builds read-only financial summaries.

### Localization

Translations are currently maintained in:

```text
src/i18n.py
```

Translation dictionaries are expected to contain the same set of keys for every supported language.

Check translation consistency with:

```powershell
python -c "from src.i18n import find_translation_issues; print(find_translation_issues())"
```

A successful check returns:

```text
()
```

User-entered data, imported descriptions, rule names, counterparties, and category names are preserved exactly as stored and are not automatically translated.

## Local data, privacy, and security

Holotes `v0.1.0` is designed primarily for trusted local use by one person.

The following files and directories should remain outside version control:

- `.env`;
- `data/`;
- `imports/`;
- `backups/`;
- SQLite databases;
- CSV and Excel statements;
- backups containing real financial data.

Do not commit real bank statements, credentials, API tokens, personal information, customer data, or production databases.

Before opening an issue or pull request, remove confidential information from logs, screenshots, sample files, and test data.

The current local-first architecture reduces external exposure, but it must not be treated as a production security boundary. Do not expose the Streamlit port directly to the public internet. Server deployment will require authentication, authorization, HTTPS, secure secret storage, hardened sessions, audit logging, and other controls planned for later versions.

## Project structure

```text
holotes/
├── .github/
│   └── workflows/
│       └── tests.yml
├── .streamlit/
│   └── config.toml
├── assets/
│   └── styles.css
├── demo_data/
│   └── tbank_demo_statement.csv
├── migrations/
│   └── versions/
├── src/
│   ├── ui/
│   │   ├── classification.py
│   │   ├── data_cache.py
│   │   ├── imports.py
│   │   ├── operations.py
│   │   ├── option_formatting.py
│   │   ├── payment_calendar.py
│   │   ├── reports.py
│   │   ├── rules.py
│   │   ├── settings.py
│   │   ├── transaction_views.py
│   │   └── unit_economics.py
│   ├── bank_import.py
│   ├── categories.py
│   ├── classification_summary.py
│   ├── data_revision.py
│   ├── database.py
│   ├── database_backup.py
│   ├── i18n.py
│   ├── models.py
│   ├── payment_calendar.py
│   ├── reporting.py
│   ├── rule_config.py
│   ├── rule_repository.py
│   ├── telegram_bot.py
│   ├── telegram_settings.py
│   ├── telegram_summary.py
│   ├── telegram_token.py
│   ├── transaction_repository.py
│   └── unit_economics.py
├── tests/
│   ├── browser/
│   │   └── test_smoke.py
│   └── test_*.py
├── alembic.ini
├── app.py
├── run_holotes.py
├── start_holotes.bat
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

## Current limitations

- Only T-Business CSV statements are currently supported
- Direct T-Business API synchronization is not implemented yet
- Imported banking data and monetary formatting are currently focused on Russian business workflows and RUB
- SQLite is the only configured database
- One Holotes installation currently represents one company or one financial workspace
- The application is designed for local single-user operation
- There is no application login, user account system, or role-based access control
- Docker and supported server deployment are not available yet
- The Streamlit interface is an MVP and may be replaced or supplemented by a more suitable frontend
- The Telegram bot is read-only and supports a limited command set
- P&L is cash-based rather than accrual-based
- User-entered data and financial category names are not automatically translated
- Some low-level validation and repository errors may not yet be localized
- Large transaction histories still require further query, caching, and pagination optimization
- `v0.1.0` is a personal/local milestone, not a production-ready multi-user release

## Roadmap

The roadmap describes direction rather than a fixed promise. Large items may be split across several `0.2.x` releases so that each release remains testable and usable.

### `v0.1.0` — personal local release

The first release focuses on a complete local workflow for one user:

- T-Business CSV import and deduplication;
- transaction classification and automatic rules;
- P&L and Cash Flow reporting;
- payment calendar and cash-gap forecasting;
- unit economics;
- local backup and restore;
- database migrations;
- read-only Telegram summaries;
- demonstration data;
- automated tests and a Windows launcher;
- release documentation and changelog.

A logo and interface screenshots are intentionally postponed until the next development cycle.

### Next development cycle — deployment and multi-user foundations

#### Installation and deployment modes

- Add Docker and Docker Compose configuration
- Provide a documented local installation mode
- Provide a documented server installation mode
- Add environment-specific configuration for local and server deployments
- Add health checks, persistent volumes, upgrade procedures, and backup guidance
- Evaluate PostgreSQL as the primary server database while retaining a simple local mode
- Document reverse proxy and HTTPS deployment

#### Company profiles and workspaces

- Allow one installation to contain multiple isolated company profiles or workspaces
- Let one person manage two or more companies on the same computer
- Separate transactions, categories, rules, reports, plans, products, and settings by company
- Add explicit company switching and safe backup/export per workspace

#### Users, roles, and permissions

- Add user accounts and authentication
- Support several people in one installation
- Introduce role-based permissions, such as owner, administrator, accountant, analyst, and read-only viewer
- Define access separately for each company or workspace
- Add audit history for important data and configuration changes

#### Security hardening

- Replace local trust assumptions with a documented security model
- Improve secret storage and token rotation
- Add secure password hashing and session management
- Add server-side authorization checks
- Add rate limiting and protection against common web attacks
- Add HTTPS deployment guidance and secure defaults
- Add audit logging and security-relevant event history
- Add dependency and vulnerability scanning
- Review backup, restore, export, and file-upload security

#### API and bank integrations

- Introduce a documented application API
- Add direct T-Business API integration where technically and legally practical
- Expand support for statement formats from other banks
- Create a reusable importer interface and test fixtures for each supported bank
- Improve currency and regional formatting support

#### Telegram bot

- Expand the command set beyond read-only monthly summaries
- Add configurable alerts and scheduled reports
- Add payment-calendar and cash-gap notifications
- Add company/workspace selection
- Apply the same role and permission model as the main application
- Improve bot administration, diagnostics, and secure deployment

#### Frontend and product presentation

- Evaluate whether Streamlit remains suitable for the next stage
- If necessary, introduce a dedicated frontend and API-backed architecture
- Improve navigation and workflows for multi-company and multi-user use
- Add the Holotes logo and current interface screenshots
- Improve first-run onboarding and deployment documentation

### Longer-term ideas

- Additional report types and accrual-based accounting options
- Configurable currencies and number formats
- More advanced planning, budgeting, and scenario analysis
- External integrations and webhooks
- Import/export integrations with accounting and ERP systems
- Production monitoring, observability, and administration tools

## Help add support for more banks

Holotes currently supports T-Business CSV statements because that is the format available for development and testing.

Support for additional banks requires examples of their exported statement structure. Real personal or business data is **not** required.

Useful contributions include:

1. a list of column names and file format details;
2. an empty template exported by the bank;
3. a few completely synthetic rows that preserve the original structure;
4. an anonymized statement with all names, account numbers, identifiers, payment purposes, and amounts safely replaced;
5. notes about encoding, delimiter, date formats, decimal separators, currencies, and unusual transaction types.

Never send an unredacted bank statement or credentials.

To help add a bank format, open a GitHub issue or contact:

**swgplaya@gmail.com**

## Contributing

The project is under active development.

Issues, bug reports, improvement proposals, bank statement format descriptions, and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

Before submitting a change:

```powershell
python -m pip install -r requirements-dev.txt
python -m compileall -q app.py src
python -m pytest -q
```

Do not include confidential or real financial data in issues, tests, screenshots, or pull requests.

## License

This project is licensed under the [MIT License](LICENSE).

## Author

[swgplaya](https://github.com/swgplaya)

Contact: **swgplaya@gmail.com**
