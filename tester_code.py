#!/usr/bin/env python3
"""Sets the tester code: the one that shows the products marked "unreleased" in products.json.

    python3 tester_code.py 'the code'
    python3 build.py

Only a salted SHA-256 of the code goes into products.json; the code itself is never stored.
Changing it locks out every tester until they enter the new one. This hides products from the
public pages; it does not protect them (the site is static and its repository public).
"""
import hashlib, json, secrets, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        sys.exit(__doc__)
    code = sys.argv[1].strip()
    salt = secrets.token_hex(8)
    cat = json.loads((HERE / "products.json").read_text())
    cat["tester"] = {"salt": salt, "hash": hashlib.sha256((salt + code).encode()).hexdigest()}
    (HERE / "products.json").write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    print("tester code set; run build.py, then commit and push")

if __name__ == "__main__":
    main()
