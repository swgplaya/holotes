# Contributing to Open MAS

Thank you for your interest in Open MAS.

Open MAS is an early-stage open-source management accounting system. Bug reports, feature proposals, documentation improvements, and pull requests are welcome.

## Before contributing

Please do not include any confidential or real financial data in:

- issues;
- screenshots;
- example files;
- tests;
- commits;
- pull requests.

Bank statements, personal data, credentials, API tokens, and production databases must never be committed to the repository.

## Development setup

Python 3.12 is recommended.

Clone the repository:

```bash
git clone https://github.com/swgplaya/open-mas.git
cd open-mas
```

Create a virtual environment:

```bash
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

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the application:

```bash
python -m streamlit run app.py
```

## Making changes

Before starting a larger change:

1. Check existing issues and pull requests.
2. Open an issue describing the proposed change.
3. Keep each pull request focused on one feature or problem.
4. Avoid unrelated formatting or refactoring.
5. Preserve backward compatibility with existing local databases when possible.

## Code guidelines

- Keep business logic outside the Streamlit interface where practical.
- Use explicit and descriptive names.
- Validate external input before writing it to the database.
- Use database transactions for multi-step mutations.
- Do not silently overwrite manually classified financial data.
- Keep P&L and Cash Flow decisions independent.
- Add tests for new business logic when possible.

## Checks

Before submitting a pull request, run:

```bash
python -m compileall app.py src
git diff --check
```

Also start the Streamlit application and manually verify the changed workflow.

## Commit messages

Use short imperative commit messages, for example:

```text
Add transaction import validation
Fix duplicate rule detection
Refactor payment calendar repository
```

## Reporting bugs

A useful bug report should include:

- the expected behavior;
- the actual behavior;
- reproduction steps;
- the Python version;
- the operating system;
- the relevant traceback.

Remove all confidential information before publishing logs or screenshots.

## License

By contributing to Open MAS, you agree that your contributions will be licensed under the MIT License.