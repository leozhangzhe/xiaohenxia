"""Explicit, password-free-on-the-command-line authentication setup."""
import argparse
import logging
import os
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spiderfoot.auth_mysql import AuthConfigurationError, AuthDatabaseUnavailable, MySQLAuthStore


def main():
    parser = argparse.ArgumentParser(description="Check or initialize MySQL authentication using SF_AUTH_* environment variables.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Read-only authentication readiness check (default).")
    action.add_argument("--initialize", action="store_true", help="Create missing auth schema/admin, or explicitly reset the configured admin.")
    args = parser.parse_args()
    try:
        if not os.getenv("SF_AUTH_MYSQL_USER", "").strip():
            raise AuthConfigurationError("Set SF_AUTH_MYSQL_USER explicitly.")
        if not os.getenv("SF_AUTH_MYSQL_PASSWORD"):
            raise AuthConfigurationError("Set SF_AUTH_MYSQL_PASSWORD to the database account password.")
        store = MySQLAuthStore(logging.getLogger("spiderfoot.auth_setup"))
        if args.initialize:
            store.initialize()
        else:
            store.check_ready()
    except (AuthConfigurationError, AuthDatabaseUnavailable) as exc:
        print(f"Authentication setup failed: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("Authentication setup failed; check server permissions and configuration.", file=sys.stderr)
        return 2
    print("Authentication initialization completed." if args.initialize else "Authentication readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
