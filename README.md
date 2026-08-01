# Open MAS

Open MAS is an open-source management accounting system for small businesses.

The project is focused on importing bank transactions, classifying cash movements, and building practical management reports without relying on cloud accounting platforms. By default, all financial data is stored locally in SQLite.

> Open MAS is currently an early-stage MVP. The interface and the first supported bank statement format are focused on Russian users and T-Business.

## Features

- Import and validate CSV statements exported from T-Business
- Prevent duplicate bank transactions
- Track imported statement files and safely delete individual import batches
- Manually classify transactions for P&L and Cash Flow
- Create priority-based automatic classification rules
- Export and import classification rules as versioned JSON
- Build cash-based P&L and Cash Flow reports
- Compare reporting periods and review financial KPIs
- Analyze unclassified transactions
- Maintain a payment calendar
- Build a daily cash balance forecast
- Calculate unit economics and pricing scenarios
- Manage all bank data locally
- Visualize reports with interactive Plotly charts

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

1. Open the **Импорт выписки** tab.
2. Upload a CSV statement exported from T-Business.
3. Review validation warnings and the transaction preview.
4. Save the new transactions to the local database.

Open MAS calculates a content hash for every transaction and skips duplicates.

### Classify transactions

Use the **Классификация** tab to decide whether each transaction should be:

- included in P&L;
- excluded from P&L;
- included in Cash Flow;
- excluded from Cash Flow.

P&L and Cash Flow decisions are independent.

### Create automatic rules

Use the **Правила** tab to create priority-based classification rules.

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
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
├── src/
│   ├── bank_import.py
│   ├── categories.py
│   ├── classification_summary.py
│   ├── database.py
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

- Only T-Business CSV statements are supported
- The interface is currently in Russian
- SQLite is the only configured database
- The application is designed primarily for local single-user operation
- P&L is cash-based rather than accrual-based
- Automated test coverage is still under development

## Roadmap

- Refactor the Streamlit interface into separate UI modules
- Add automated tests
- Improve the visual theme and navigation
- Support additional bank statement formats
- Add PostgreSQL support
- Add Docker configuration
- Introduce an API layer
- Expand multi-user and role-based functionality

## Contributing

The project is under active development.

Issues, bug reports, improvement proposals, and pull requests are welcome. Do not include confidential or real financial data in issues, tests, or pull requests.

## License

This project is licensed under the [MIT License](LICENSE).

## Author

[swgplaya](https://github.com/swgplaya)