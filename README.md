# Open MAS

Open MAS is an open-source, local-first management accounting system for small businesses.

The project is focused on importing bank transactions, classifying cash movements, building management reports, planning cash flows, and calculating unit economics without relying on cloud accounting platforms. By default, all financial data is stored locally in SQLite.

The application interface is available in Russian, English, and Simplified Chinese and includes light and dark visual themes.

> Open MAS is currently an early-stage MVP. The first supported bank statement format is focused on Russian T-Business users, while the application interface itself is multilingual.

## Features

- Import and validate CSV statements exported from T-Business
- Prevent duplicate bank transactions using stable content hashes
- Track imported statement files and safely delete individual import batches
- Manually classify transactions independently for P&L and Cash Flow
- Create priority-based automatic classification rules
- Export and import classification rules as versioned JSON
- Build cash-based P&L and Cash Flow reports
- Compare reporting periods and review financial KPIs
- Analyze unclassified and partially classified transactions
- Maintain a payment calendar for future inflows and outflows
- Build a daily cash balance forecast and identify potential cash gaps
- Calculate unit economics, pricing scenarios, margins, and break-even points
- Manage products and cost items
- Visualize reports with interactive Plotly charts
- Switch between Russian, English, and Simplified Chinese
- Use light and dark application themes
- Keep financial data locally in SQLite

## Important note

The P&L report currently uses bank transactions and the cash method.

Open MAS is a management reporting tool. It is not statutory accounting, tax, payroll, or audit software.

## Technology stack

- Python
- Streamlit
- pandas
- SQLAlchemy
- SQLite
- Plotly

## Installation

Python 3.12 is recommended.

### 1. Clone the repository

```powershell
git clone https://github.com/swgplaya/open-mas.git
cd open-mas
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Linux or macOS:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the application

```powershell
python -m streamlit run app.py
```

Streamlit will display the local application URL in the terminal.

The SQLite database is created locally when the application starts.

## Usage

### Import bank transactions

1. Open the **Import statement** tab. Its name is translated according to the selected interface language.
2. Upload a CSV statement exported from T-Business.
3. Review validation warnings and the transaction preview.
4. Save the new transactions to the local database.

Open MAS calculates a content hash for every transaction and skips duplicates.

### Classify transactions

Use the **Classification** tab to decide independently whether each transaction should be:

- included in P&L;
- excluded from P&L;
- included in Cash Flow;
- excluded from Cash Flow.

P&L and Cash Flow decisions are independent.

### Create automatic rules

Use the **Rules** tab to create priority-based classification rules.

Rules can match:

- all text fields;
- counterparty name;
- counterparty INN;
- bank category;
- transaction description;
- payment purpose;
- MCC;
- tax code.

Rule configurations can be exported to JSON and restored in another Open MAS installation.

### Build reports

The application currently provides:

- cash-based P&L;
- Cash Flow;
- period comparisons;
- financial KPIs;
- category breakdowns;
- transaction-level report details;
- unit economics;
- payment calendar and cash forecast.

## Interface languages and themes

Open MAS currently supports the following interface languages:

- Russian
- English
- Simplified Chinese

The language can be changed directly in the application. The selected language affects tabs, forms, reports, tables, buttons, validation messages, payment calendar views, unit economics, and bank import screens.

User-entered data, imported transaction descriptions, rule names, counterparties, and financial category names are preserved exactly as stored and are not automatically translated.

The application also supports light and dark visual themes. Theme selection is stored in the Streamlit session and does not affect financial data.

Translations are maintained in `src/i18n.py`. Translation dictionaries are expected to contain the same set of keys for every supported language.

Translation consistency can be checked with:

```powershell
python -c "from src.i18n import find_translation_issues; print(find_translation_issues())"
```

A successful check returns:

```text
()
```

## Local data and privacy

The following files and directories are excluded from Git:

- `.env`
- `data/`
- `imports/`
- `demo_data/`
- SQLite databases
- CSV and Excel files

Do not commit real bank statements, credentials, API tokens, personal information, or production databases.

## Project structure

```text
open-mas/
├── .streamlit/
│   └── config.toml
├── assets/
│   └── styles.css
├── app.py
├── requirements.txt
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── src/
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
└── tests/
```

## Current limitations

- Only T-Business CSV statements are currently supported
- Imported bank data and monetary formatting are currently focused on Russian business workflows and RUB
- SQLite is the only configured database
- The application is designed primarily for local single-user operation
- P&L is cash-based rather than accrual-based
- User-entered data and financial category names are not automatically translated
- Some low-level validation errors originating from internal modules may not yet be localized
- Automated test coverage is still under development

## Roadmap

- Refactor the Streamlit interface into separate UI modules
- Expand automated test coverage
- Move localization into smaller domain-specific translation modules
- Localize low-level validation and repository error messages
- Support additional bank statement formats
- Add configurable currencies and number formatting
- Add PostgreSQL support
- Add Docker configuration
- Introduce an API layer
- Expand multi-user and role-based functionality

## Contributing

The project is under active development.

Issues, bug reports, improvement proposals, and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

Do not include confidential or real financial data in issues, tests, screenshots, or pull requests.

## License

This project is licensed under the [MIT License](LICENSE).

## Author

[swgplaya](https://github.com/swgplaya)