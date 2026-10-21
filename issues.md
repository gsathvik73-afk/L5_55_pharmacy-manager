# Static Code Analysis Issue Table

Sai Sathvik Gullipalli | PES2UG24CS430 | Section G

Individual submission | Software Engineering Lab 5 | 21 October 2026

Assigned repository: https://github.com/SETAPESU26/L5_55_pharmacy-manager

Original commit: `ff16b8303037de5c50851ccb75916cf5870026b7`

Line numbers below refer to `reports/before/pharmacy_manager.py`. Repeated diagnostics are grouped by root cause. Bandit severity labels are the tool's reported ratings; the behavior rows are additional findings from running and reviewing the program.

| Issue | Type | Line(s) | Description | Fix Approach |
|---|---|---|---|---|
| Shell command injection | Security: High: Bandit B605 | 68 | os.system concatenated a medicine name into a shell command. | print_label prints the text directly; shell syntax remains literal. |
| Weak MD5 hash | Security: High: Bandit B324 | 50-51 | The patient identifier used MD5 and ambiguous name + phone concatenation. | Hash a JSON array of the fields with SHA-256. This remains an identifier, not anonymization. |
| Unrestricted eval | Security: Medium: Bandit B307; Pylint W0123 | 46-48 | A formula could execute arbitrary Python code through eval. | Parse an AST; allow only numbers, signs and +, -, *, /. Bound input size, tree size and results. |
| Unsafe pickle loading | Security: Medium: B301; Low: B403 | 3, 56-65 | pickle.load can execute code from an untrusted stock file. | Use JSON and validate every record before replacing stock. Old pickle files are not loaded. |
| Embedded credential | Security: Low: Bandit B105 | 11, 78-82, 102 | The same source-code password was used for every installation. | Read PHARMACY_PASSWORD from the environment, deny login when unset and use compare_digest. |
| Predictable prescription reference | Security: Low: Bandit B311 | 53-54 | random.randint generated a predictable six-digit prescription reference. | Use secrets.token_hex(16) for a 128-bit reference. Randomness alone does not guarantee uniqueness. |
| Silently swallowed errors | Security: Low: B110; W0702; E722 | 22-28 | A bare except followed by pass hid missing medicines and other failures. | Raise KeyError or ValueError as appropriate. The demo catches specific failures and logs them. |
| Shared default audit list | Quality: Pylint W0102 | 13-20 | audit=[] was shared by calls that omitted the argument. | Use audit=None and create a fresh list per call; preserve an explicitly supplied audit list. |
| Manual file cleanup | Quality: Pylint R1732 | 56-65 | Manual open/close pairs could leave files open after an exception. | Use with blocks and explicit UTF-8 encoding for JSON files. |
| Global dictionary rebinding | Quality: Pylint W0603 | 61-65 | loadStock rebound the global medicines dictionary to unchecked input. | Validate into a temporary dictionary, then clear and update the existing dictionary only on success. |
| Inconsistent return behavior | Quality: Pylint R1710 | 13-20 | addMedicine returned None for an empty name and a list on success. | Invalid input raises ValueError. Successful add_medicine calls always return the audit list. |
| Redundant boolean branches | Quality: Pylint R1703, R1705 | 33-38, 78-82 | if/else branches returned True and False directly. | Return the expiry comparison and the credential comparison directly after validation. |
| Missing documentation and naming | Quality: Pylint C0114, C0116, C0103 | 1, 13-89 | The module/functions lacked docstrings and function names used camelCase. | Add concise docstrings and rename functions and their callers to snake_case. |
| Unused imports | Quality: Pylint W0611; Flake8 F401 | 2, 6 | sys and logging were imported without being used. | Remove sys. Use logging for rejected demo actions and configure it only in the main block. |
| Formatting and long lines | Quality: C0301, C0209; E302, E305, E501 | 13-108 | Definitions lacked blank lines; output lines were too long; an audit string used old formatting. | Use f-strings, two blank lines around top-level definitions and lines no longer than 79 characters. |
| Invalid stock and dispensing | Behavior: Manual review and regression tests | 13-24, 90-95 | The demo accepted negative quantities and a numeric name. Excess or negative dispensing could corrupt stock. | Validate names, integer quantities, finite prices and dates; reject unknown, expired or insufficient stock before mutation. |
| Mixed stock batches | Behavior: Manual review and regression tests | 16-18 | Restocking silently kept the first price and expiry even when the new batch differed. | Reject a changed price or expiry for an existing name; require a distinct name for a different batch. |
| Expiry and billing boundaries | Behavior: Manual review and regression tests | 40-44, 70-75 | expiringSoon included already expired stock and excluded the last day. Billing ignored expiry and repeated-item availability. | Use 0 <= days remaining <= window. Validate bill items, combine repeated quantities and block expired or unavailable stock. |
| Execution during import | Behavior: Manual review and regression tests | 108 | An unconditional main() printed output, changed stock and wrote a file whenever the module was imported. | Use the __name__ == '__main__' guard. Import now has no demo or file-writing side effects. |

## Verification

| Check | Before | After |
|---|---|---|
| Pylint | 4.83/10; 45 messages | 10.00/10; 0 messages |
| Bandit | 8 findings: 2 high, 2 medium, 4 low | 0 findings |
| Flake8 | 22 violations | 0 violations |
| Regression tests | Not supplied upstream | 27 passed |

Final tool runs and the demo returned exit code 0. The final `flake8_report.txt` is empty because Flake8 emits no output when there are no violations. Original output is preserved under `reports/before/`; final reports and `test_results.txt` are at the submission root. No warnings were disabled.
