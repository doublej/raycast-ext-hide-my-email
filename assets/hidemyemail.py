#!/usr/bin/env -S /opt/homebrew/bin/uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyicloud"]
# ///

"""Generate + reserve an iCloud Hide My Email alias, copy it to the clipboard.

Talks to Apple's real /v1/hme API via pyicloud. Auth is a keyring-stored password
plus a trust token in ~/.config/hidemyemail/session, so 2FA is asked once and the
session then works headlessly until Apple invalidates it (~30 days).

    ./hidemyemail.py --login     one-time interactive auth (password + 2FA)
    ./hidemyemail.py --check     verify the session without creating anything
    ./hidemyemail.py [label]     generate an alias
"""

import datetime
import getpass
import os
import subprocess
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "hidemyemail"
APPLE_ID_FILE = CONFIG_DIR / "appleid"
SESSION_DIR = CONFIG_DIR / "session"
# Raycast runs a bundled copy of this file, so point re-login at the repo, not __file__.
SOURCE = Path.home() / "Documents/development/raycast/raycast-ext-hide-my-email/assets/hidemyemail.py"
RELOGIN = f"Run in a terminal:  {SOURCE} --login"


def readAppleId() -> str:
    stored = APPLE_ID_FILE.read_text().strip() if APPLE_ID_FILE.exists() else ""
    apple_id = os.environ.get("ICLOUD_APPLE_ID", "") or stored
    if not apple_id:
        sys.exit(f"No Apple ID configured. {RELOGIN}")
    return apple_id


def connect(apple_id: str, password: str | None = None):
    from pyicloud import PyiCloudService

    return PyiCloudService(apple_id, password, cookie_directory=str(SESSION_DIR))


def runLogin() -> None:
    from pyicloud.utils import store_password_in_keyring

    apple_id = input("Apple ID: ").strip()
    password = getpass.getpass("Password (not stored by this script — goes to your Keychain): ")

    api = connect(apple_id, password)
    if api.requires_2fa:
        api.validate_2fa_code(input("Two-factor code: ").strip())
    if not api.is_trusted_session:
        api.trust_session()

    store_password_in_keyring(apple_id, password)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    APPLE_ID_FILE.write_text(apple_id + "\n")
    APPLE_ID_FILE.chmod(0o600)
    print(f"Signed in as {apple_id}. Session trusted — no 2FA needed from now on.")


def openSession():
    api = connect(readAppleId())
    if api.requires_2fa:
        sys.exit(f"iCloud session expired. {RELOGIN}")
    return api


def runCheck() -> None:
    aliases = list(openSession().hidemyemail)
    print(f"Session OK — {len(aliases)} existing aliases, nothing created.")


def generateAlias(label: str) -> None:
    from pyicloud.exceptions import PyiCloudAPIResponseException

    hme = openSession().hidemyemail
    email = hme.generate()
    if not email:
        sys.exit("Apple returned no address (usually the 5-per-30-minutes rate limit).")
    try:
        hme.reserve(email, label)
    except PyiCloudAPIResponseException as err:
        sys.exit(f"Could not reserve {email}: {err}")

    subprocess.run(["pbcopy"], input=email, text=True, check=True)
    print(f"{email}  ✓ copied  ({label})")


def main() -> None:
    arg = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    if arg == "--login":
        return runLogin()
    if arg == "--check":
        return runCheck()
    generateAlias(arg or datetime.date.today().isoformat())


if __name__ == "__main__":
    main()
