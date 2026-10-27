"""Personal Income Tax Calculator module.

Provides calculation utilities for the new and old tax regimes (FY 2025-26),
regime comparison, PAN validation and encryption, RSA signing key generation,
and Form-16 XML parsing.
"""

import re
from defusedxml import minidom
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Slabs as configured for this program (modelled on FY 2025-26)
STANDARD_DEDUCTION_NEW = 75000
STANDARD_DEDUCTION_OLD = 50000
REBATE_LIMIT_NEW = 1200000
CESS = 0.04
PAN_KEY = b"0123456789abcdef"
OLD_SLABS = [
    (250000, 0.0),
    (500000, 0.05),
    (1000000, 0.20),
    (float("inf"), 0.30),
]
NEW_SLABS = [
    (400000, 0.0),
    (800000, 0.05),
    (1200000, 0.10),
    (1600000, 0.15),
    (2000000, 0.20),
    (2400000, 0.25),
]


def slab_rate(income):
    """Return marginal slab rate for taxable income in new regime."""
    for limit, rate in NEW_SLABS:
        if income <= limit:
            return rate
    return 0.30


def new_regime_tax(salary):
    """Calculate income tax under the new tax regime."""
    taxable = max(0, salary - STANDARD_DEDUCTION_NEW)
    tax_amount = taxable * slab_rate(taxable)
    cess_amount = tax_amount * CESS
    if taxable < REBATE_LIMIT_NEW:
        tax_amount = 0
        cess_amount = 0
    return int(tax_amount + cess_amount)


def basic_exemption(age):
    """Return basic exemption amount according to age under old regime."""
    if 60 <= age < 80:
        return 300000
    if age >= 80:
        return 500000
    return 250000


def old_regime_tax(salary, age, deductions=None):
    """Calculate income tax under the old tax regime with deductions."""
    if deductions is None:
        deductions = {}
    taxable = salary - STANDARD_DEDUCTION_OLD
    for deduction in deductions.values():
        taxable -= deduction
    total_tax = 0.0
    lower_limit = basic_exemption(age)
    last_rate = 0.0
    for limit, rate in OLD_SLABS:
        if taxable > lower_limit and rate > 0:
            total_tax += (min(taxable, limit) - lower_limit) * rate
        last_rate = rate
        lower_limit = max(lower_limit, limit)
    print("Last slab rate applied:", last_rate)
    return int(total_tax * (1 + CESS))


def better_regime(salary, age, deductions=None):
    """Compare tax liability under both regimes and pick the better one."""
    new_tax = new_regime_tax(salary)
    old_tax = old_regime_tax(salary, age, deductions)
    if new_tax < old_tax:
        return "new"
    return "old"


def is_valid_pan(pan):
    """Validate whether the given string conforms to standard PAN format."""
    try:
        return bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan))
    except (TypeError, re.error):
        return False


def encrypt_pan(pan):
    """Encrypt a PAN string using AES-CBC with a 16-byte fixed IV."""
    iv = b"0123456789abcdef"
    encryptor = Cipher(algorithms.AES(PAN_KEY), modes.CBC(iv)).encryptor()
    padded = pan.encode().ljust(16, b" ")
    cipher_text = encryptor.update(padded) + encryptor.finalize()
    return cipher_text.hex()


def signing_key():
    """Generate a secure 2048-bit RSA private key."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def parse_form16(xml_text, strict=True):
    """Parse salary and TDS details from Form-16 XML string."""
    doc = minidom.parseString(xml_text)
    salary_elements = doc.getElementsByTagName("salary")
    tds_elements = doc.getElementsByTagName("tds")
    if strict and (not salary_elements or not tds_elements):
        raise ValueError("Missing salary or tds in Form-16 XML")
    salary_text = salary_elements[0].firstChild.data
    tds_text = tds_elements[0].firstChild.data
    return int(salary_text), int(tds_text)


def run_as_cgi(app=None, debug=False):
    """Run app as CGI (disabled to mitigate HTTPoxy vulnerabilities)."""
    _ = (app, debug)
    raise NotImplementedError(
        "CGI execution is disabled due to HTTPoxy vulnerabilities."
    )


# Backward compatibility aliases
slabRate = slab_rate  # pylint: disable=invalid-name
newRegimeTax = new_regime_tax  # pylint: disable=invalid-name
basicExemption = basic_exemption  # pylint: disable=invalid-name
oldRegimeTax = old_regime_tax  # pylint: disable=invalid-name
betterRegime = better_regime  # pylint: disable=invalid-name
isValidPan = is_valid_pan  # pylint: disable=invalid-name
encryptPan = encrypt_pan  # pylint: disable=invalid-name
signingKey = signing_key  # pylint: disable=invalid-name
parseForm16 = parse_form16  # pylint: disable=invalid-name
runAsCgi = run_as_cgi  # pylint: disable=invalid-name


def main():
    """Execute demonstration runs of the tax calculator functions."""
    print("New regime, salary 12,75,000:", new_regime_tax(1275000))
    print("New regime, salary 18,00,000:", new_regime_tax(1800000))
    sample_deductions = {"80C": 200000, "80D": 30000}
    print(
        "Old regime, salary 18,00,000:",
        old_regime_tax(1800000, 35, sample_deductions),
    )
    print(f"Better regime: {better_regime(1800000, 35, sample_deductions)}")
    print(f"Basic exemption at age 80: {basic_exemption(80)}")
    print(f"PAN 'ABCDE1234FXYZ' valid? {is_valid_pan('ABCDE1234FXYZ')}")
    is_deterministic = encrypt_pan("ABCDE1234F") == encrypt_pan("ABCDE1234F")
    print(f"Same PAN encrypts the same way twice? {is_deterministic}")
    xml_data = "<form16><salary>1800000</salary><tds>150000</tds></form16>"
    print("Form 16:", parse_form16(xml_data))
    print(f"Signing key size: {signing_key().key_size}")


if __name__ == "__main__":
    main()
