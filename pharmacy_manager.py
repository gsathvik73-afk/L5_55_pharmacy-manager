"""Validated pharmacy stock demo for SE Lab 5, PES2UG24CS430.

Run with Python 3.10 or newer. Stock is stored as JSON. Set the
PHARMACY_PASSWORD environment variable to enable the login demonstration.
"""

import ast
import hashlib
import json
import logging
import math
import operator
import os
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

medicines = {}
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _validate_name(name):
    """Return a nonempty, trimmed name or reject the input."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Medicine name must be a nonempty string.")
    return name.strip()


def _validate_quantity(qty, allow_zero=False):
    """Require whole units; dispensing and stocking require positive units."""
    minimum = 0 if allow_zero else 1
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < minimum:
        raise ValueError(f"Quantity must be an integer of at least {minimum}.")


def _validate_price(price):
    """Require a finite, nonnegative numeric unit price."""
    if type(price) not in (int, float):
        raise ValueError("Price must be a number.")
    try:
        finite = math.isfinite(price)
    except OverflowError as error:
        raise ValueError("Price is outside the supported range.") from error
    if not finite or price < 0:
        raise ValueError("Price must be finite and nonnegative.")


def _validate_expiry(expiry):
    """Require an actual calendar date written as YYYY-MM-DD."""
    if not isinstance(expiry, str):
        raise ValueError("Expiry must use YYYY-MM-DD.")
    parsed = date.fromisoformat(expiry)
    if parsed.isoformat() != expiry:
        raise ValueError("Expiry must use YYYY-MM-DD.")
    return parsed


def add_medicine(name, qty=1, price=0.0, expiry="2099-12-31", audit=None):
    """Add validated stock, keeping audit lists independent across calls."""
    name = _validate_name(name)
    _validate_quantity(qty)
    _validate_price(price)
    _validate_expiry(expiry)
    if audit is None:
        audit = []
    if not isinstance(audit, list):
        raise ValueError("Audit must be a list.")
    if name in medicines:
        current = medicines[name]
        if current["price"] != price or current["expiry"] != expiry:
            raise ValueError("Different stock batches need distinct names.")
    else:
        medicines[name] = {"qty": 0, "price": price, "expiry": expiry}
    medicines[name]["qty"] += qty
    timestamp = datetime.now().isoformat()
    audit.append(f"{timestamp}: Stocked {qty} units of {name}")
    return audit


def _sale_stock(name, qty):
    """Check availability and expiry before billing or changing stock."""
    _validate_quantity(qty)
    stock = medicines[name]
    if is_expired(name):
        raise ValueError(f"Cannot dispense expired medicine: {name}.")
    if qty > stock["qty"]:
        raise ValueError(f"Insufficient stock for {name}.")
    return stock


def dispense_medicine(name, qty):
    """Dispense available, unexpired stock; reject invalid requests."""
    name = _validate_name(name)
    stock = _sale_stock(name, qty)
    stock["qty"] -= qty
    if stock["qty"] == 0:
        del medicines[name]


def get_quantity(name):
    """Return available units, raising KeyError for an unknown medicine."""
    return medicines[_validate_name(name)]["qty"]


def is_expired(name):
    """Treat stock as expired after its expiry date has passed."""
    expiry = medicines[_validate_name(name)]["expiry"]
    return _validate_expiry(expiry) < date.today()


def bill_amount(prescription):
    """Quote valid stock without dispensing; combine duplicate line items."""
    quantities = {}
    for name, qty in prescription:
        name = _validate_name(name)
        _validate_quantity(qty)
        quantities[name] = quantities.get(name, 0) + qty
    amounts = []
    for name, qty in quantities.items():
        stock = _sale_stock(name, qty)
        amounts.append(stock["price"] * qty)
    return round(math.fsum(amounts), 2)


def _evaluate_arithmetic(node):
    """Evaluate only numeric literals, four arithmetic operators and signs."""
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left = _evaluate_arithmetic(node.left)
        right = _evaluate_arithmetic(node.right)
        value = _OPERATORS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        value = _evaluate_arithmetic(node.operand)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = -_evaluate_arithmetic(node.operand)
    else:
        raise ValueError("Only numbers and +, -, *, / are allowed.")
    if abs(value) > 1_000_000_000 or not math.isfinite(value):
        raise ValueError("Arithmetic result is outside the supported range.")
    return value


def calculate_dosage(formula):
    """Evaluate bounded arithmetic, never Python code or clinical rules."""
    if not isinstance(formula, str) or not 0 < len(formula) <= 200:
        raise ValueError("Formula must contain 1 to 200 characters.")
    try:
        expression = ast.parse(formula.strip(), mode="eval")
        if sum(1 for _ in ast.walk(expression)) > 64:
            raise ValueError("Formula is too complex.")
        result = _evaluate_arithmetic(expression.body)
    except (SyntaxError, ZeroDivisionError, OverflowError) as error:
        raise ValueError("Formula is not valid bounded arithmetic.") from error
    if result <= 0:
        raise ValueError("Dosage must be positive.")
    return result


def patient_id(name, phone):
    """Hash unambiguous fields; this identifier does not anonymize patients."""
    if not all(isinstance(value, str) and value.strip()
               for value in (name, phone)):
        raise ValueError("Patient name and phone must be nonempty strings.")
    payload = json.dumps([name.strip(), phone.strip()]).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def generate_rx_number():
    """Generate a random 128-bit prescription reference."""
    return f"RX-{secrets.token_hex(16).upper()}"


def save_stock(filename="pharmacy.json"):
    """Write stock as data using a file that closes on success or failure."""
    with Path(filename).open("w", encoding="utf-8") as stock_file:
        json.dump(medicines, stock_file, indent=2, allow_nan=False)


def load_stock(filename="pharmacy.json"):
    """Validate a complete JSON file before replacing current stock."""
    with Path(filename).open("r", encoding="utf-8") as stock_file:
        loaded = json.load(stock_file)
    if not isinstance(loaded, dict):
        raise ValueError("Stock file must contain a JSON object.")
    validated = {}
    for raw_name, stock in loaded.items():
        name = _validate_name(raw_name)
        if name in validated:
            raise ValueError("Stock file contains duplicate normalized names.")
        if not isinstance(stock, dict):
            raise ValueError("Each medicine must contain a stock object.")
        if set(stock) != {"qty", "price", "expiry"}:
            raise ValueError("Stock requires qty, price and expiry fields.")
        _validate_quantity(stock["qty"], allow_zero=True)
        _validate_price(stock["price"])
        _validate_expiry(stock["expiry"])
        validated[name] = stock.copy()
    medicines.clear()
    medicines.update(validated)


def print_label(name):
    """Print a label directly, without constructing a shell command."""
    print(f"Dispensing label: {_validate_name(name)}")


def expiring_soon(days=30):
    """List unexpired stock expiring within an inclusive number of days."""
    _validate_quantity(days, allow_zero=True)
    today = date.today()
    return [
        name for name, stock in medicines.items()
        if 0 <= (_validate_expiry(stock["expiry"]) - today).days <= days
    ]


def pharmacist_login(password):
    """Compare with external configuration; deny login when unset."""
    expected = os.environ.get("PHARMACY_PASSWORD")
    if not expected or not isinstance(password, str):
        return False
    return secrets.compare_digest(
        password.encode("utf-8"), expected.encode("utf-8")
    )


def print_stock():
    """Print quantities, unit prices and expiry dates for all stock."""
    print("===== Pharmacy Stock Report =====")
    for name, stock in medicines.items():
        print(f"{name} -> {stock['qty']} units, Rs. {stock['price']:.2f}, "
              f"exp {stock['expiry']}")


def main():
    """Run a short, noninteractive demo with valid and rejected inputs."""
    medicines.clear()
    future = (date.today() + timedelta(days=90)).isoformat()
    past = (date.today() - timedelta(days=1)).isoformat()
    add_medicine("Paracetamol 500mg", 200, 1.5, future)
    add_medicine("Amoxicillin 250mg", 40, 6.0, past)
    for name, qty in (("Cetirizine 10mg", -10), (404, 25)):
        try:
            add_medicine(name, qty)
        except ValueError as error:
            logging.warning("Rejected stock: %s", error)
    dispense_medicine("Paracetamol 500mg", 30)
    try:
        dispense_medicine("Insulin", 2)
    except KeyError as error:
        logging.warning("Unknown medicine: %s", error)
    print("Paracetamol stock:", get_quantity("Paracetamol 500mg"))
    print("Amoxicillin expired?", is_expired("Amoxicillin 250mg"))
    print("Bill:", bill_amount([("Paracetamol 500mg", 10)]))
    print("Dosage arithmetic (250 * 2):",
          calculate_dosage("250 * 2"))
    print("Patient ID:", patient_id("Demo Patient", "0000000000"))
    print("Rx number:", generate_rx_number())
    print("Login with empty password:", pharmacist_login(""))
    print_label("Paracetamol 500mg")
    print("Expiring within 30 days:", expiring_soon())
    save_stock()
    load_stock()
    print_stock()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s: %(message)s"
    )
    main()
