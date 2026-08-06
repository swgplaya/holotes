# Holotes

[![Tests](https://github.com/swgplaya/holotes/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/swgplaya/holotes/actions/workflows/tests.yml)

Holotes is an open-source, local-first management accounting system for small businesses.

The name comes from the Greek *holótēs* — wholeness: separate financial data brought together into one coherent system.

It imports bank transactions, helps classify cash movements, builds management reports, plans future cash flows, and calculates unit economics without requiring a cloud accounting platform. Financial data is stored locally in SQLite by default.

The application interface is available in Russian, English, and Simplified Chinese and supports light and dark themes.

> Holotes is currently an early-stage MVP. The first supported bank statement format is focused on Russian T-Business users. The interface itself is multilingual.

## Contents

- [Features](#features)
- [Important note](#important-note)
- [Technology stack](#technology-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Testing and CI](#testing-and-ci)
- [Architecture](#architecture)
- [Local data and privacy](#local-data-and-privacy)
- [Project structure](#project-structure)
- [Current limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

### Bank data

- Import and validate CSV statements exported from T-Business
- Normalize imported transactions before saving
- Prevent duplicate transactions using stable content hashes
- Track import batches and their source files
- Review transactions linked to a particular import
- Safely delete an import batch without removing transactions shared with another batch
- Delete old untracked transactions separately
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

### Interface

- Russian, English, and Simplified Chinese localization
- Light and dark themes
- Lazy rendering of the active tab
- Separate UI modules for the main application sections
- Interactive tables, forms, metrics, and charts

## Important note

The P&L report currently uses bank transactions and the cash method.

Holotes is a management reporting tool. It is not statutory accounting, tax, payroll, banking, audit, or regulatory reporting software. Calculations should be reviewed before they are used for business decisions.

## Technology stack

- Python 3.12
- Streamlit
- pandas
- SQLAlchemy
- SQLite
- Plotly
- pytest
- GitHub Actions

## Installation

Python 3.12 is recommended.

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

### 4. Run the application

```powershell
python -m streamlit run app.py
```

Streamlit prints the local application URL in the terminal.

The SQLite database is created locally when the application starts.

## Usage

### Import bank transactions

1. Open the **Import statement** tab.
2. Upload a CSV statement exported from T-Business.
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

The project has **more than 100 automated tests** covering its core calculations and SQLite repositories.

The suite covers:

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
- planned cash-flow repository operations;
- product and cost repository operations;
- foreign-key and cascade-deletion behavior.

Repository tests use isolated temporary SQLite databases. They do not modify the local application database.

GitHub Actions automatically runs the following checks after every push and pull request:

1. create a clean Ubuntu environment;
2. install Python 3.12;
3. install project and development dependencies;
4. check dependency consistency;
5. compile the Python modules;
6. run the complete pytest suite.

The workflow is stored in:

```text
.github/workflows/tests.yml
```

## Architecture

Holotes separates the application into several layers.

### Application entry point

`app.py` configures Streamlit, initializes the database, manages top-level navigation, and delegates each section to a UI renderer.

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
- option formatting.

UI modules do not import `app.py`.

### Business logic

Pure or mostly pure calculation modules include:

- `src/reporting.py`;
- `src/classification_summary.py`;
- `src/payment_calendar.py`;
- `src/unit_economics.py`;
- `src/rule_config.py`.

### Persistence layer

SQLAlchemy models and repository operations are implemented in:

- `src/models.py`;
- `src/database.py`;
- `src/transaction_repository.py`;
- `src/rule_repository.py`;
- repository functions in the payment calendar and unit economics modules.

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

## Local data and privacy

Holotes is designed primarily for local operation.

The following files and directories should remain outside version control:

- `.env`;
- `data/`;
- `imports/`;
- `demo_data/`;
- SQLite databases;
- CSV and Excel statements;
- backups containing real financial data.

Do not commit real bank statements, credentials, API tokens, personal information, customer data, or production databases.

Before opening an issue or pull request, remove confidential information from logs, screenshots, sample files, and test data.

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
├── src/
│   ├── ui/
│   │   ├── classification.py
│   │   ├── imports.py
│   │   ├── operations.py
│   │   ├── option_formatting.py
│   │   ├── payment_calendar.py
│   │   ├── reports.py
│   │   ├── rules.py
│   │   ├── transaction_views.py
│   │   └── unit_economics.py
│   ├── bank_import.py
│   ├── categories.py
│   ├── classification_summary.py
│   ├── database.py
│   ├── i18n.py
│   ├── models.py
│   ├── payment_calendar.py
│   ├── reporting.py
│   ├── rule_config.py
│   ├── rule_repository.py
│   ├── transaction_repository.py
│   └── unit_economics.py
├── tests/
│   ├── conftest.py
│   ├── test_classification_summary.py
│   ├── test_payment_calendar.py
│   ├── test_payment_calendar_repository.py
│   ├── test_reporting.py
│   ├── test_rule_config.py
│   ├── test_rule_repository.py
│   ├── test_transaction_repository.py
│   ├── test_unit_economics.py
│   └── test_unit_economics_repository.py
├── app.py
├── run_holotes.py
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

## Current limitations

- Only T-Business CSV statements are currently supported
- Imported banking data and monetary formatting are currently focused on Russian business workflows and RUB
- SQLite is the only configured database
- The application is designed primarily for local single-user operation
- P&L is cash-based rather than accrual-based
- User-entered data and financial category names are not automatically translated
- Some low-level validation and repository errors may not yet be localized
- Database schema migrations are not implemented yet
- Browser-level and visual end-to-end tests are not implemented yet
- Large transaction histories still require further query, caching, and pagination optimization
- The project is an early-stage MVP and has not yet reached a stable production release

## Roadmap

### Near-term

- Add period-limited transaction queries
- Reduce repeated SQLite reads during Streamlit reruns
- Introduce safe Streamlit caching and explicit cache invalidation
- Add pagination for large transaction tables
- Use Streamlit fragments where they reduce unnecessary reruns
- Add database schema migrations
- Add browser-level smoke tests
- Prepare demo data and first-launch onboarding
- Add Docker configuration
- Complete final manual release testing
- Publish the first tagged release

### Later

- Move localization into smaller domain-specific modules
- Localize remaining low-level validation and repository errors
- Support additional bank statement formats
- Add configurable currencies and number formatting
- Add PostgreSQL support
- Introduce an API layer
- Expand multi-user and role-based functionality

## Contributing

The project is under active development.

Issues, bug reports, improvement proposals, and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

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
