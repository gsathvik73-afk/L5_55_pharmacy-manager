# Lab 5 Reflection

Sai Sathvik Gullipalli | PES2UG24CS430 | Section G

Individual submission | Software Engineering Lab 5 | 21 October 2026

## 1. Which issues were the easiest to fix, and which were the hardest? Why?

The easiest changes were removing the unused sys import, adding blank lines and docstrings, and replacing audit=[] with audit=None. Their causes and fixes were local and easy to verify. The hardest change was removing eval while preserving arithmetic such as 250 * 2. I used an AST allowlist for numeric literals, arithmetic operators and unary signs, with size and result limits. I tested valid formulas as well as calls, attributes, invalid syntax and division by zero. Replacing pickle also required care: the entire JSON file must pass validation before it can replace the current stock.

## 2. Did the static analysis tools report any false positives? If so, describe one example.

I did not establish a definite false positive that justified suppressing a warning. Bandit's B311 warning on random.randint is context-dependent: the prescription number was a reference, not an authentication token, so the security severity depends on how that reference is used. I still replaced it with secrets.token_hex and a larger identifier space. Similarly, the MD5 patient identifier was not a password hash; I replaced it with SHA-256 and unambiguous field encoding without claiming that hashing anonymizes patient information. Every reported warning was addressed, with no suppression comments.

## 3. How would you integrate static analysis tools into your actual software development workflow?

I would install pinned versions in a project virtual environment and run Flake8, Pylint and Bandit before committing. In continuous integration, I would run the same commands on each pull request and require the regression tests to pass. I would review high and medium severity security findings first, then correctness and style warnings. Any proposed suppression would need a documented reason and review. I would keep the tool output as evidence and use tests alongside analysis, because a clean static report does not prove that stock handling or expiry rules are correct.

## 4. What tangible improvements did you observe in code quality, readability, or potential robustness after applying the fixes?

Pylint improved from 4.83/10 with 45 messages to 10.00/10 with no messages. Bandit dropped from eight findings, including two high and two medium severity findings, to zero. Flake8 dropped from 22 violations to zero. The corrected demo rejects negative stock, numeric medicine names and unknown dispensing requests. The 27 passing regression tests cover audit isolation, expiry boundaries, billing, safe arithmetic, literal label printing, JSON loading, login behavior and import safety. Function names and docstrings now make the operations easier to follow, and specific exceptions make failures visible.
