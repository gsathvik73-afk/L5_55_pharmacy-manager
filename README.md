# Software Engineering Lab 5

Sai Sathvik Gullipalli | PES2UG24CS430 | Section G

Individual submission: Static Code Analysis of the Pharmacy Management System.

## Required deliverables

- `pharmacy_manager.py`: cleaned application.
- `issues.md`: 19 documented groups of findings and their fixes.
- `reflection.md`: answers to all four supplied reflection questions.

## Results

Pylint: **10.00/10**, zero messages. Bandit: **zero findings**.
Flake8: **zero violations**. Regression tests: **27 passed**.
All three analysis commands, the tests and the demo returned exit code 0.
The submitted application contains no warning-suppression comments.

## Run

Use Python 3.10 or newer. The application uses only the standard library.

```sh
python pharmacy_manager.py
```

The demo is noninteractive and saves `pharmacy.json` in its working directory.
It intentionally prints warnings when rejecting the original invalid inputs.
The login function reads `PHARMACY_PASSWORD` from the environment and returns
False if it is unset. No credential is supplied in this submission.
The demo attempts login with an empty password to demonstrate denial.

## Reproduce the checks

The recorded run used Python 3.11.9, Pylint 4.1.3, Bandit 1.9.4 and Flake8 7.4.1.
The following commands use a virtual environment; activate its Windows
equivalent when working on Windows.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pylint --persistent=n pharmacy_manager.py
python -m bandit -r pharmacy_manager.py
python -m flake8 pharmacy_manager.py
python -m unittest -v test_pharmacy_manager
```

The target is `pharmacy_manager.py`, as named in the assigned repository.
The handout's `inventory_system.py` is a generic example filename.
The empty final `flake8_report.txt` is the successful raw output.
`verification.json` records commands, exit codes and the final source hash.

## Evidence

For the form field asking for a PDF with the output of all three tools, upload
`PES2UG24CS430_Lab5_Three_Tools_Output.pdf`. It reproduces the final captured
Pylint, Bandit and Flake8 output with commands and exit codes. Flake8 is silent
on success, so its zero-byte report and exit code 0 are stated explicitly.
`tool_output_capture.json` retains stdout and stderr separately.

`reports/before/` contains the unchanged original script, README, demo output
and original analysis reports. Those files retain the original defects as
evidence. The corrected application is at the submission root.
Final reports, demo output and test output are also at the root.
Tool versions are pinned in `requirements-dev.txt`.

## Behavior changes

Function names now use snake_case. Invalid operations raise specific exceptions.
Quantities must be positive integers for stocking, dispensing and billing;
zero is allowed for loaded inventory records and the expiry window.
Expired stock remains visible for tracking but cannot be billed or dispensed.
An expiry date is valid through that date; the soon-to-expire range includes
today and its last day. Different prices or expiry dates require distinct
batch names. Billing is a quote and does not change stock.

Persistence now uses validated JSON and does not load legacy pickle files.
Prescription references use 128 random bits, with no database uniqueness
guarantee. The patient hash is a deterministic identifier, not anonymization.
The arithmetic helper accepts numbers, signs and +, -, *, / with parentheses;
function calls, attributes and exponentiation are rejected.

## Assignment sources

- Assigned public repository: https://github.com/SETAPESU26/L5_55_pharmacy-manager
- Original commit: `ff16b8303037de5c50851ccb75916cf5870026b7`
- Mapping: `5G_Lab-5-Repo-Assignemnt.xlsx`, Sheet1 row 55, B55:D55.
- Requirements: `Lab_5_Static_Code_Analysis_Student_handout.docx`.
- Reflection questions: `reflection_lab5.txt`.

This package contains the individual lab work for PES2UG24CS430.
