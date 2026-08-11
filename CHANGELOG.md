# Changelog

All notable changes to Holotes will be documented in this file.

The project follows [Semantic Versioning](https://semver.org/).

## [0.2.3] - 2026-08-12

### Fixed

- restored Telegram forum-topic routing when using the MTProto transport;
- correctly detect a forum topic when Telegram provides the topic root through `reply_to_msg_id` without `reply_to_top_id`;
- keep Telegram bot responses in the same forum topic where the command was received;
- added regression coverage for forum-topic root messages, replies inside topics, and ordinary non-topic replies.

## [Unreleased]

## [0.2.2] - 2026-08-12

### Fixed

- Fixed Telegram configuration persistence when `.env` is bind-mounted into a Docker container.
- Added an in-place write fallback for Telegram transport settings and bot token storage when atomic file replacement is unavailable.
- Added regression coverage for Docker-style bind-mounted `.env` persistence.

## [0.2.1] - 2026-08-12

### Added

- Added an MTProto Telegram transport based on Telethon.
- Added MTProxy support for Telegram connectivity in restricted networks.
- Added support for Telegram MTProxy deep links.
- Added persistent Telethon session storage in the `data/` directory.
- Added Telegram transport selection and MTProto configuration to the Settings interface.
- Added MTProto connection and bot-token validation without relying on the HTTPS Bot API.
- Added configuration through:
  - `TELEGRAM_TRANSPORT`;
  - `TELEGRAM_API_ID`;
  - `TELEGRAM_API_HASH`;
  - `TELEGRAM_MTPROXY_URL`.

### Changed

- Telegram command handling is now shared between the Bot API and MTProto transports.
- The existing Bot API transport remains available as the default and backward-compatible option.
- Access restrictions, language preferences, commands, and financial-summary logic are transport-independent.
- Telegram connection checks now use the currently selected transport.
- Saved Telegram API Hash and MTProxy credentials are not displayed back in the Settings interface.
- `python-socks` is pinned to version `3.0.0` for reproducible MTProxy support.

### Reliability

- Telethon authorization state persists across Docker container restarts and recreation.
- MTProto connectivity was validated through the Docker runtime and a persistent session.
- MTProto token validation uses a temporary Telethon session so replacement credentials are validated independently of an existing authorized session.

### Notes

- Holotes does not modify system-wide proxy or VPN settings; MTProxy is used only by the Telegram MTProto transport.
- On servers where Telegram connectivity is restricted, including some networks in Russia, the Telegram bot may require MTProto through a working MTProxy or another suitable route.
- The Holotes web interface does not depend on Telegram connectivity and continues to operate normally when the Telegram bot cannot connect.
- On servers and networks where Telegram is reachable normally, the Bot API or direct MTProto connectivity can be used without additional routing.
- The Telegram bot remains read-only for financial data.
- `v0.2.1` remains an owner-operated, single-company, single-user release.


## [0.2.0] - 2026-08-11

### Added

- Added Docker and Docker Compose deployment for always-on Holotes installations.
- Added a reproducible Linux container image based on Python 3.12.
- Added a Streamlit Docker health check.
- Added persistent host-mounted storage for:
  - the SQLite database;
  - built-in database backups;
  - `.env` configuration.
- Added configurable Docker host binding through `HOLOTES_BIND_ADDRESS`.
- Added automatic web-only startup when the Telegram bot token is not configured.
- Added Linux server administration scripts for:
  - starting and stopping Holotes;
  - restarting the service;
  - checking status and health;
  - following logs;
  - upgrading production installations to an explicit release tag.

### Changed

- Holotes now initializes and migrates the database before starting the Streamlit and Telegram child processes.
- The combined service launcher now handles `SIGTERM` and shuts down child processes gracefully.
- Docker Compose restarts the Holotes container automatically unless it was explicitly stopped.
- Docker deployment binds the Streamlit port to `127.0.0.1` on the host by default.
- SQLite connections now use WAL journaling and a 30-second busy timeout for safer long-running web and Telegram access.
- Database backup and restoration now use WAL-safe SQLite snapshots.
- Docker deployment, upgrades, health checks, persistence, logs, shutdown, and network exposure are now documented in the README.
- The roadmap now separates always-on deployment in `v0.2.0` from the planned multi-company work in `v0.3.0`.

### Security

- Docker does not expose the Streamlit interface to LAN or public interfaces by default.
- `.env` is excluded from Docker image build context and remains host-mounted at runtime.
- Application data is excluded from Docker image build context and remains outside the container lifecycle.
- Public Internet exposure is still unsupported without an external protected deployment layer.

### Notes

- `v0.2.0` remains an owner-operated, single-company, single-user release.
- Telegram integration remains optional.
- SQLite remains the supported database backend.
- Multi-company support is planned for a later milestone.
- Full application authentication, user accounts, roles, PostgreSQL, and direct public Internet deployment remain outside the scope of this release.

## [0.1.2] - 2026-08-11

### Added

- Added optional numeric amount conditions to automatic classification rules:
  - greater than;
  - greater than or equal;
  - less than;
  - less than or equal;
  - exact amount;
  - inclusive amount range.
- Added a calculated balance based on the complete imported transaction history.
- Added the calculated balance to Telegram financial summaries.

### Changed

- Automatic rules can now combine transaction direction, absolute transaction amount, and text matching conditions.
- Rule configuration export now uses schema version 2 with amount-condition fields.
- Rule configuration schema version 1 remains supported for backward-compatible imports.
- The Operations interface now shows the calculated balance separately from inflow and outflow metrics.
- Telegram summaries show the calculated balance independently of the selected P&L and Cash Flow reporting period.

### Database

- Added amount-condition fields to classification rules:
  - `amount_operator`;
  - `amount_value_kopecks`;
  - `amount_value_to_kopecks`.
- Existing rules default to no amount restriction after migration.

### Notes

- The calculated balance is the sum of all imported signed cash movements.
- It may differ from the actual bank balance when imported history is incomplete or does not begin from a zero balance.

## [0.1.1] - 2026-08-11

### Fixed

- Fixed the saved rules list so it is always rendered and no longer depends on uploading a rule configuration file.

### Added

- Added report period presets for P&L and Cash Flow:
  - month;
  - year;
  - last 30 days;
  - all time;
  - custom period.
- Added support for the current incomplete month and current incomplete year.
- Added synchronized report period selection between P&L and Cash Flow.

### Changed

- Monthly and yearly comparisons now use calendar-aware previous periods.
- The last 30 days period is calculated relative to the current date.
- Report month and year selectors include the current calendar period even when no transactions have been imported for it yet.
- Operations and classification tables now adapt their height to the number of displayed rows.

## [0.1.0] - 2026-08-06
### Added

- Local-first management accounting application built with Streamlit.
- Import and validation of CSV bank statements exported from T-Business.
- Transaction normalization and stable hash-based duplicate prevention.
- Import journal with batch inspection and safe batch deletion.
- Independent transaction classification for P&L and Cash Flow.
- Priority-based automatic classification rules.
- Rule configuration export and import using versioned JSON.
- Cash-based P&L reporting with period comparisons and transaction details.
- Cash Flow reporting with inflow, outflow, and category analysis.
- Interactive Plotly charts for financial reports.
- Payment calendar with one-time, monthly, and yearly planned cash flows.
- Daily cash-balance forecasting and cash-gap detection.
- Unit economics calculations for products, pricing, costs, margins, operating results, and break-even volume.
- Local SQLite database backup, preview, and restoration.
- Automatic safety backup before database restoration.
- Alembic database migrations.
- Telegram bot with read-only financial summaries.
- Telegram bot access restrictions by user ID and chat ID.
- Per-chat Telegram summary language selection for Russian, English, and Simplified Chinese.
- Telegram bot token storage in `.env`.
- Russian, English, and Simplified Chinese interface localization.
- Light and dark interface themes.
- Anonymized demonstration data for testing the main workflow.
- Automated unit, repository, migration, Telegram, and browser smoke tests.
- GitHub Actions continuous integration.
- Windows launcher with separate modes for:
  - the web interface and Telegram bot;
  - the web interface only;
  - the Telegram bot only.

### Changed

- Renamed the project from Open MAS to Holotes.
- Renamed application entry points and internal technical identifiers to use the Holotes name.
- Updated the documentation for the local, single-user scope of the first release.
- Added a post-`0.1.0` roadmap covering Docker, server deployment, multiple companies, multiple users, roles, security, bank integrations, and possible frontend replacement.
- Moved the logo and interface screenshots to the next development cycle.

### Security

- Financial data is stored locally in SQLite by default.
- Telegram bot access can be restricted to explicitly allowed users and chats.
- The saved Telegram token is not displayed in full.
- Real databases, bank statements, backups, and secret files are excluded from version control.
- Database restoration creates a safety copy of the current database.

### Known limitations

- Only T-Business CSV statements are currently supported.
- The application is designed for trusted local single-user use.
- One installation currently represents one company.
- There are no application user accounts or role-based permissions.
- Docker and supported server deployment are not available yet.
- SQLite is the only configured database.
- The Telegram bot provides a limited command set; financial data access is read-only.
- P&L reporting uses the cash method.
- The application must not be exposed directly to the public internet.
- `v0.1.0` is a personal local milestone, not a production-ready multi-user release.
