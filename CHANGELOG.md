# Changelog

All notable changes to Holotes will be documented in this file.

The project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
