"""Generate a password hash for APP_PASSWORD_HASH in the .env file.

Run from the project root:

    python utils/generate_password_hash.py
"""

import getpass
import sys

from werkzeug.security import generate_password_hash


def main():
    password = getpass.getpass("New password: ")
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        return 1
    if len(password) < 8:
        print("Use at least 8 characters.", file=sys.stderr)
        return 1

    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    print()
    print("Add this line to your .env file:")
    print(f"APP_PASSWORD_HASH='{generate_password_hash(password)}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
