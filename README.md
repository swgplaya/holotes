# Holotes

[![Tests](https://github.com/swgplaya/holotes/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/swgplaya/holotes/actions/workflows/tests.yml)

Holotes is an open-source, local-first management accounting system for small businesses.

The name comes from the Greek *holótēs* — wholeness: separate financial data brought together into one coherent system.

Holotes imports bank transactions, helps classify cash movements, builds management reports, plans future cash flows, calculates unit economics, creates local database backups, and can provide read-only financial summaries through a Telegram bot.

Financial data is stored locally in SQLite by default. The interface is available in Russian, English, and Simplified Chinese and supports light and dark themes.

> **Release status:** This README describes `v0.1.1`, the current tagged Holotes release. It is intended primarily for personal, local, single-user use and is not designed for public server deployment or production multi-user access.

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
- Select report periods using month, year, last 30 days, all time, or custom dates
- Include the current partial month and current partial year in calendar presets
- Keep the selected period synchronized between P&L and Cash Flow
- Compare with the previous period or the previous year using calendar-aware comparisons where applicable
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
- Select and persist the summary language separately for each Telegram chat
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
- Automatically size Operations and Classification tables to the number of displayed rows

## Important note

The P&L report currently uses bank transactions and the cash method.

Holotes is a management reporting tool. It is not statutory accounting, tax, payroll, banking, audit, or regulatory reporting software. Calculations should be reviewed before they are used for business decisions.

The Telegram bot in `v0.1.1` exposes financial data only through read-only summary commands. The `/language` command changes only the response-language preference for the current chat. Configure the allowed users and chats carefully and do not share the bot token.

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

The supported `v0.1.1` installation mode is a local Python environment on Windows, Linux, or macOS.

Docker images and supported server deployment are planned for later milestones. Public deployment, full authentication, and production multi-user configuration are not part of `v0.1.1`.

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
- period presets for month, year, last 30 days, all time, and custom dates;
- period comparisons;
- synchronized P&L and Cash Flow period selection;
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

The current bot is designed for local access to read-only financial summaries and per-chat language preferences.

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
/language
/language ru
/language en
/language zh-CN
/summary
/summary YYYY-MM
```

Examples:

```text
/language
/language en
/summary
/summary 2026-07
```

The selected language is stored separately for each Telegram chat. In a group, Telegram may send the command in the form `/language@BotUsername en`.

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
- demonstration data safety, stability, and built-in report category localization;
- Telegram token storage, settings, authorization, per-chat language selection, bot behavior, and financial summaries;
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
python -m pytest tests/browser/test_smoke.py -m browser -q
python -m pip_audit
```

`pip-audit` is included in the development requirements. Release validation also includes a Gitleaks scan of the Git history when the separately installed Gitleaks binary is available.

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

Changing the interface language never rewrites stored values. Built-in P&L and Cash Flow category labels are translated for presentation in reports, while custom category names, imported descriptions, rule names, counterparties, and other user-entered content are displayed exactly as stored.

## Local data, privacy, and security

Holotes `v0.1.1` is designed primarily for trusted local use by one person.

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
│   │   ├── table_height.py
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
│   ├── unit_economics.py
│   └── version.py
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
- The Telegram bot supports a limited command set; access to financial data is read-only
- P&L is cash-based rather than accrual-based
- Built-in report category labels are localized, but custom categories and other user-entered content are not automatically translated
- Some low-level validation and repository errors may not yet be localized
- Large transaction histories still require further query, caching, and pagination optimization
- `v0.1.1` is a personal/local release, not a production-ready multi-user release

## Roadmap

The roadmap describes direction rather than a fixed promise. Patch releases stay focused on small, testable improvements; larger architecture changes are reserved for later milestones.

### `v0.1.0` — personal local release

The first release established a complete local workflow for one user:

- T-Business CSV import and deduplication;
- transaction classification and automatic rules;
- P&L and Cash Flow reporting;
- payment calendar and cash-gap forecasting;
- unit economics;
- local backup and restore;
- database migrations;
- read-only Telegram financial summaries with per-chat language selection;
- demonstration data;
- automated tests and a Windows launcher.

### `v0.1.1` — reporting and interface refinement

The current patch release focuses on usability and regression fixes:

- restore the saved rules list in the Rules interface;
- add report period presets for month, year, last 30 days, all time, and custom dates;
- keep P&L and Cash Flow period selection synchronized;
- use calendar-aware previous-period comparisons for month and year presets;
- allow current partial month and year periods even when no transactions exist yet for the current calendar period;
- adapt Operations and Classification table height to the number of displayed rows;
- keep release validation reproducible with development dependency auditing.

### `v0.1.2` — planned incremental improvements

The next patch cycle is expected to focus on small accounting workflow improvements:

- add numeric amount conditions to automatic rules;
- add a calculated balance based on imported operations;
- expose that calculated balance in Telegram summaries with an explicit scope caveat.

### `v0.2.0` — planned local-network node and multi-company foundation

The next larger milestone is intended to keep Holotes owner-operated while making it practical as an always-on node inside a trusted local network:

- documented always-on deployment with Docker/Docker Compose or an equivalent Linux service mode;
- automatic start/restart, health checks, persistent storage, logs, upgrades, and backups;
- access from the owner's devices inside a trusted LAN;
- multiple isolated companies/workspaces in one installation;
- persistent company switching in the web interface and Telegram bot;
- continued use of SQLite with a single Holotes server process and safer concurrency settings;
- basic protection for LAN access and improved mobile usability of the main screens.

Full multi-user accounts and roles, PostgreSQL, public Internet deployment, a separate API/frontend architecture, and other SaaS-style capabilities are intentionally deferred beyond `v0.2.0`.

### Longer-term ideas

- additional report types and accrual-based accounting options;
- configurable currencies and number formats;
- more advanced planning, budgeting, and scenario analysis;
- additional bank importers and direct bank integrations where practical;
- user accounts, roles, audit history, and stronger authorization;
- PostgreSQL and protected public-server deployment;
- a documented application API and, if justified, a dedicated frontend;
- external integrations, webhooks, monitoring, and administration tools.

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
