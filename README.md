# Holotes

[![Tests](https://github.com/swgplaya/holotes/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/swgplaya/holotes/actions/workflows/tests.yml)

Holotes is an open-source, local-first management accounting system for small businesses.

The name comes from the Greek *holótēs* — wholeness: separate financial data brought together into one coherent system.

Holotes imports bank transactions, helps classify cash movements, builds management reports, plans future cash flows, calculates unit economics, creates local database backups, and can provide read-only financial summaries through a Telegram bot.

Financial data is stored locally in SQLite by default. The interface is available in Russian, English, and Simplified Chinese and supports light and dark themes.

> **Release status:** This README describes `v0.2.3`, the current Holotes release. It supports local Python installation and owner-operated Docker deployment for an always-on instance, and adds an MTProto/Telethon Telegram transport with MTProxy support. It remains a single-company, single-user system and must not be exposed directly to the public Internet without an appropriate protected deployment layer.

## Contents

- [Features](#features)
- [Important note](#important-note)
- [Technology stack](#technology-stack)
- [Installation](#installation)
- [Docker deployment](#docker-deployment)
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
- Calculate a balance from the complete set of imported cash movements

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
- Use exact, contains, and starts-with text matching modes
- Add optional numeric amount conditions using `>`, `>=`, `<`, `<=`, `=`, or an inclusive range
- Combine direction, amount, and text conditions in the same rule
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

- Use either the Telegram Bot API or the MTProto transport
- Run MTProto through Telethon, with MTProxy support for restricted networks
- Store the bot token and MTProto credentials in `.env` without displaying saved secrets
- Persist the Telethon MTProto session in the `data/` directory
- Restrict access by Telegram user ID and chat ID
- Configure the default summary period
- Select and persist the summary language separately for each Telegram chat
- Use Russian, English, and Simplified Chinese responses
- Request read-only financial summaries
- Include the calculated balance from all imported transactions in financial summaries
- Request a summary for a specific month
- Retrieve user and chat IDs for access configuration
- Keep MTProto replies in the same Telegram forum topic where the command was received

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

The Telegram bot in `v0.2.3` exposes financial data only through read-only summary commands. The `/language` command changes only the response-language preference for the current chat. Configure the allowed users and chats carefully and do not share the bot token, Telegram API credentials, MTProxy secret, or Telethon session file.

The calculated balance shown in Holotes is derived from the sum of all imported cash movements. It may differ from the actual bank balance if the imported history is incomplete or does not begin from a zero balance.

## Technology stack

- Python 3.12
- Streamlit
- pandas
- SQLAlchemy
- SQLite
- Alembic
- Plotly
- Docker and Docker Compose
- Telethon
- pytest
- GitHub Actions

## Installation

Python 3.12 is recommended.

### Installation modes

`v0.2.3` supports two installation modes:

- a local Python environment on Windows, Linux, or macOS;
- an owner-operated Docker deployment for an always-on Holotes instance on a trusted machine or server.

Public Internet deployment, full user authentication, multi-user accounts, and role-based access control are not part of the current architecture.

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

## Docker deployment

Docker deployment is officially supported in `v0.2.3` for owner-operated, always-on Holotes installations.

It is intended for an always-on, owner-operated Holotes instance. The default Compose configuration exposes the Streamlit interface only on the Docker host itself:

```text
127.0.0.1:8501
```

It does not publish port `8501` to the LAN or public Internet by default.

### Requirements

For production deployment, install Docker Engine with the Docker Compose plugin on Linux. Docker Desktop on Windows is suitable for development and testing, but the production deployment path documented here assumes Linux.

Verify the installation:

```bash
docker --version
docker compose version
```

### 1. Clone Holotes

```bash
git clone https://github.com/swgplaya/holotes.git
cd holotes
```

### 2. Create the environment file

```bash
cp .env.example .env
```

Edit `.env` if Telegram integration or another supported setting is required. Do not commit `.env`.

### 3. Build and start Holotes

```bash
docker compose up -d --build
```

Check container status:

```bash
docker compose ps
```

A healthy installation should report the Holotes service as `healthy`. The local web interface is available at `http://127.0.0.1:8501`.

### Linux server operations

For a production-style Linux installation, Holotes includes small operational scripts in:

```text
scripts/server/
├── start.sh
├── stop.sh
├── restart.sh
├── status.sh
├── logs.sh
├── health.sh
└── update.sh
```

Make sure Docker Engine starts automatically with the operating system. On a systemd-based Linux distribution:

```bash
sudo systemctl enable --now docker
```

Verify it with:

```bash
systemctl is-enabled docker
systemctl is-active docker
```

After Holotes has been created once with Docker Compose, the Compose setting:

```text
restart: unless-stopped
```

allows the Holotes container to start again automatically after the Docker daemon or server restarts.

An intentionally stopped container remains stopped. Start it again with:

```bash
./scripts/server/start.sh
```

Common administration commands:

```bash
./scripts/server/status.sh
./scripts/server/health.sh
./scripts/server/logs.sh
./scripts/server/restart.sh
./scripts/server/stop.sh
```

`logs.sh` shows the latest 100 lines by default. A different initial line count can be supplied:

```bash
./scripts/server/logs.sh 250
```

Production installations should remain pinned to release tags rather than following the development branch directly.

To upgrade to a specific release, first create and download a database backup from Holotes **Settings**, then run:

```bash
./scripts/server/update.sh v0.2.3
```

The update script fetches Git tags, verifies that the requested release exists, switches the production checkout to that exact tag, rebuilds the Docker image, and recreates the Holotes service.

Do not use an unversioned `git pull` as the normal production upgrade procedure.

### Persistent data

Compose bind-mounts two host locations into the container:

```text
./data  -> /app/data
./.env  -> /app/.env
```

The `data` directory contains the SQLite database and built-in database backups. Because it is stored on the host, deleting or recreating the container does not delete the Holotes database.

The `.env` file is also stored on the host, so Telegram settings saved through Holotes survive container recreation.

Typical persistent files include:

```text
data/
├── finance.db
├── finance.db-wal
├── finance.db-shm
├── telegram_mtproto.session
└── backups/
```

Do not delete `data/` or `.env` during a normal container upgrade.

### Health check

The Docker image checks the built-in Streamlit endpoint `http://127.0.0.1:8501/_stcore/health`.

Inspect current health with:

```bash
docker compose ps
```

The exact generated container name can vary. `docker compose ps` is the preferred way to inspect the service.

### Logs

```bash
docker compose logs -f holotes
```

Recent logs only:

```bash
docker compose logs --tail=100 holotes
```

### Stop and start

Stop without deleting the container:

```bash
docker compose stop
```

Start it again:

```bash
docker compose start
```

Holotes handles Docker's normal termination signal and shuts down the Streamlit and Telegram child processes before the container exits.

Remove and recreate the container:

```bash
docker compose down
docker compose up -d
```

Persistent data in `./data` and `.env` remains on the host.

### Upgrade an existing Docker installation

Before upgrading, create and download a Holotes database backup from **Settings** and keep a copy outside the project directory.

Production installations should upgrade to an explicit release tag rather than following `main` directly. For example:

```bash
./scripts/server/update.sh v0.2.3
```

The update script fetches tags, validates the requested release, switches the checkout to that exact tag, rebuilds the image, and recreates the service. Database migrations run automatically when Holotes starts.

After the upgrade, confirm the service is healthy:

```bash
./scripts/server/status.sh
./scripts/server/health.sh
```

Use `./scripts/server/logs.sh` if startup diagnostics are needed.

### Network access

The default Compose configuration binds the web port to `127.0.0.1:8501`. This is deliberate because Holotes does not yet provide application-level login or role-based authorization.

The bind address can be changed in `.env`:

```dotenv
HOLOTES_BIND_ADDRESS=0.0.0.0
```

Only do this inside a trusted LAN, VPN, or another appropriately protected environment. Do not expose the current Streamlit interface directly to the public Internet.

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

Higher-priority rules are evaluated before lower-priority rules. Amount conditions are optional; when configured, they are evaluated together with direction and text conditions. Transaction amounts are compared by absolute value, while direction remains a separate rule condition.

Rule configurations can be exported as versioned JSON and restored in another Holotes installation. `v0.2.3` exports rule configuration schema version 2 while continuing to accept version 1 configurations created before amount conditions were added.

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

The Telegram integration provides read-only financial summaries, access restrictions, and per-chat language preferences.

Holotes supports two Telegram transports:

- **Bot API** — the traditional HTTPS Telegram Bot API transport;
- **MTProto** — a Telethon-based transport that can use MTProxy.

Both transports share the same commands, access-control rules, summary settings, and financial-summary logic.

### Configure the bot token

1. Create a bot through Telegram's BotFather.
2. Start the Holotes web interface.
3. Open **Settings → Telegram**.
4. Enter the bot token.
5. Save it through the interface.

The full saved token is not displayed after saving.

### Choose the Telegram transport

By default Holotes uses the HTTPS Bot API:

```dotenv
TELEGRAM_TRANSPORT=bot_api
```

For MTProto, select **MTProto** in **Settings → Telegram** and configure:

```dotenv
TELEGRAM_TRANSPORT=mtproto
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_MTPROXY_URL=
```

`TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are Telegram application credentials from `my.telegram.org`.

`TELEGRAM_MTPROXY_URL` accepts Telegram proxy deep links in either form:

```text
tg://proxy?server=host&port=443&secret=...
https://t.me/proxy?server=host&port=443&secret=...
```

The Settings interface stores these values in `.env`. Saved secret values such as API Hash and the MTProxy link are not displayed back to the user.

The **Check connection** action follows the selected transport. In MTProto mode, token validation and connectivity checks are performed through Telethon and the configured MTProxy instead of the HTTPS Bot API.

### Russia-hosted servers and Telegram availability

The Holotes web interface does not depend on Telegram connectivity. If Telegram is restricted or unreachable from the server's network, the web application continues to work normally.

For servers physically hosted in Russia, direct Telegram connectivity may be unavailable or unstable because of current network restrictions. In that case, the Telegram bot may require the MTProto transport with a working MTProxy or another suitable network route. Holotes applies the proxy only to its Telegram transport and does not change the server's system-wide networking.

For servers hosted in countries and networks where Telegram is reachable normally, the Bot API or direct MTProto transport should work without these additional routing measures.

### MTProto session persistence

Telethon stores its authorization session under:

```text
data/telegram_mtproto.session
```

An accompanying SQLite journal file may temporarily exist while the process is running.

The Docker deployment bind-mounts `./data` to `/app/data`, so the MTProto session survives normal container restarts, rebuilds, and recreation. Treat the session file as a secret and do not commit or share it.

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

Telegram summaries show the calculated balance from the complete imported transaction history even when the requested P&L and Cash Flow period is narrower, such as a specific month.

When a command is sent inside a Telegram forum topic, Holotes keeps the response in that same topic. The MTProto transport handles both topic-root messages and replies within a topic.

## Backup and restore

Database backup and restoration controls are available in **Settings**.

Recommended procedure before upgrades or major data changes:

1. create a backup;
2. download the backup file;
3. store a copy outside the project directory;
4. verify that the backup opens in the restoration preview;
5. only then continue with the upgrade or restoration.

Before restoring an uploaded database, Holotes creates an additional safety backup of the current database.

When using Docker, the database and built-in backups remain in the host `data/` directory and survive container recreation. Before a Docker upgrade, keep an additional downloaded backup outside the project directory.

Holotes uses SQLite's backup mechanism when creating and restoring database snapshots so committed data remains consistent when WAL mode is enabled.

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
- `run_holotes.py` initializes the database, launches Streamlit and the Telegram bot together, and coordinates graceful shutdown.
- `start_holotes.bat` provides a Windows launcher for both services or either service separately.
- `Dockerfile` defines the Linux container image used for always-on deployment.
- `compose.yaml` configures persistent host data, health checks, restart behavior, and local port publishing.
- `scripts/server/` provides Linux operational wrappers for start, stop, restart, status, health, logs, and release-tag upgrades.

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

SQLite connections enable foreign-key enforcement, WAL journaling, and a busy timeout for safer long-running web and Telegram access.

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

- `src/telegram_bot.py` contains the shared command dispatcher and the legacy Bot API runtime.
- `src/telegram_mtproto.py` implements the Telethon MTProto runtime, MTProxy parsing, MTProto message adaptation, and sending.
- `src/telegram_transport_config.py` manages Telegram transport configuration in `.env`.
- `src/telegram_settings.py` stores bot behavior, access restrictions, and per-chat preferences.
- `src/telegram_token.py` manages bot-token persistence and Bot API token validation.
- `src/telegram_summary.py` builds transport-independent read-only financial summaries.

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

Holotes `v0.2.3` is designed primarily for trusted owner-operated use by one person, either as a local Python installation or an always-on Docker deployment.

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

The current local-first architecture reduces external exposure, but it must not be treated as a production security boundary.

Docker deployment binds Streamlit to `127.0.0.1` on the host by default. Do not expose the current Streamlit port directly to the public Internet.

Trusted-LAN or VPN access can be enabled deliberately, but Holotes still has no application login, user accounts, or role-based access control. Public deployment requires stronger authentication, authorization, HTTPS, secret management, hardened sessions, audit logging, and other controls planned for later versions.

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
├── scripts/
│   └── server/
│       ├── health.sh
│       ├── logs.sh
│       ├── restart.sh
│       ├── start.sh
│       ├── status.sh
│       ├── stop.sh
│       └── update.sh
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
│   ├── telegram_mtproto.py
│   ├── telegram_settings.py
│   ├── telegram_summary.py
│   ├── telegram_token.py
│   ├── telegram_transport_config.py
│   ├── transaction_repository.py
│   ├── unit_economics.py
│   └── version.py
├── tests/
│   ├── browser/
│   │   └── test_smoke.py
│   └── test_*.py
├── .dockerignore
├── alembic.ini
├── app.py
├── compose.yaml
├── Dockerfile
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
- The application remains owner-operated and single-user
- There is no application login, user account system, or role-based access control
- Docker deployment is intended for localhost, trusted LAN, VPN, or another protected environment rather than direct public Internet exposure
- The Streamlit interface is an MVP and may be replaced or supplemented by a more suitable frontend
- The Telegram bot supports a limited command set; access to financial data is read-only
- Telegram availability depends on the server network; Russia-hosted servers may require MTProto through MTProxy or another suitable route
- P&L is cash-based rather than accrual-based
- Built-in report category labels are localized, but custom categories and other user-entered content are not automatically translated
- Some low-level validation and repository errors may not yet be localized
- Large transaction histories still require further query, caching, and pagination optimization
- The calculated balance is derived from imported transaction history and is not a direct bank balance
- `v0.2.3` is an owner-operated single-user release with Docker deployment; it is not a production-ready multi-user system

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

This patch release focused on usability and regression fixes:

- restore the saved rules list in the Rules interface;
- add report period presets for month, year, last 30 days, all time, and custom dates;
- keep P&L and Cash Flow period selection synchronized;
- use calendar-aware previous-period comparisons for month and year presets;
- allow current partial month and year periods even when no transactions exist yet for the current calendar period;
- adapt Operations and Classification table height to the number of displayed rows;
- keep release validation reproducible with development dependency auditing.

### `v0.1.2` — rule amount conditions and calculated balance

The current patch release adds small accounting-workflow improvements without changing the local single-user architecture:

- add optional numeric amount conditions to automatic classification rules;
- support greater-than, greater-than-or-equal, less-than, less-than-or-equal, exact-value, and inclusive range comparisons;
- keep legacy rule configurations compatible while exporting the new rule configuration schema;
- add a calculated balance based on the complete imported transaction history;
- show the calculated balance separately in the Operations interface;
- include the calculated balance in Telegram financial summaries;
- make the web interface explicitly explain that the calculated balance can differ from the actual bank balance when imported history is incomplete or starts from a non-zero balance.

### `v0.2.0` — always-on Docker deployment

This release focuses deliberately on deployment rather than expanding the accounting model or adding multi-company architecture:

- documented Docker and Docker Compose deployment;
- a reproducible Linux container image;
- automatic database initialization and migrations before service startup;
- graceful container shutdown through `SIGTERM`;
- automatic restart through Compose;
- Streamlit health checks;
- persistent SQLite database and built-in backups through the host `data/` directory;
- persistent `.env` configuration outside the image;
- SQLite WAL mode and a busy timeout for safer long-running web and Telegram access;
- localhost-only host port binding by default;
- documented start, stop, logs, upgrade, backup, and container-recreation procedures.
- Linux server administration scripts for common operations and release-tag upgrades.

`v0.2.0` provides a stable owner-operated Holotes node that can run continuously on a PC, home server, VPS behind appropriate protection, or another trusted Linux/Docker host.

Multi-company support, user accounts, roles, PostgreSQL, and direct public Internet deployment are intentionally outside the scope of `v0.2.0`.

### `v0.2.1` — Telegram MTProto transport

This patch release improves Telegram connectivity without changing the accounting or deployment architecture:

- retain the existing Bot API transport;
- add a Telethon-based MTProto transport;
- support MTProxy deep links for restricted networks;
- share commands, access controls, language settings, and financial-summary logic between transports;
- configure MTProto credentials from the Settings interface;
- persist Telethon authorization state in the existing host-mounted `data/` directory.

The MTProxy configuration applies only to Telegram traffic and does not modify server-wide networking.

### `v0.2.2` — Docker environment persistence hotfix

This patch release fixes Telegram and transport settings persistence in Docker deployments that bind-mount `.env` into the container:

- preserve the normal atomic `.env` replacement path where supported;
- fall back to rewriting the existing bind-mounted file when Docker prevents inode replacement;
- keep Telegram transport and bot-token settings writable from the web interface in Docker deployments.

### `v0.2.3` — MTProto forum-topic routing fix

This patch release restores correct Telegram forum-topic behavior for the MTProto transport:

- detect forum topics when Telegram provides the topic root through `reply_to_msg_id` without `reply_to_top_id`;
- preserve the original topic when replying to commands sent in a forum topic;
- keep replies inside the same topic both for topic-root commands and replies to messages within that topic;
- add regression coverage for topic-root messages, replies inside topics, and ordinary non-topic replies.

### `v0.3.0` — planned multi-company foundation

The following larger milestone is planned to introduce multiple isolated companies or financial workspaces in one Holotes installation:

- separate company/workspace data boundaries;
- company creation and management;
- persistent company selection in the web interface;
- company-aware Telegram summaries and settings;
- safe migration of an existing single-company installation into the multi-company model.

The exact design will be finalized after the `v0.2.0` deployment architecture has been used and validated in practice.

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
