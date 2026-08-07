#!/usr/bin/env python
"""
Discover cameras for any environment.

Usage:
    python tools/discover_cameras.py              # Uses ENV variable
    python tools/discover_cameras.py --env qa
    python tools/discover_cameras.py --env staging --site 120
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_clients.auth_helper import AuthHelper
from api_clients.base_api_client import BaseAPIClient
from api_clients.discovery_helper import DiscoveryHelper


def main():
    parser = argparse.ArgumentParser(description="Discover cameras in environment")
    parser.add_argument("--env", default=os.getenv("ENV", "qa"), help="Environment (qa/staging/prod)")
    parser.add_argument("--site", type=int, help="Specific site ID (optional)")
    args = parser.parse_args()

    os.environ["ENV"] = args.env

    # Load config and authenticate. Credentials come from QA_USER/QA_PASSWORD
    # in .env, same as the test suite (see conftest.py).
    from dotenv import load_dotenv
    load_dotenv()
    from config.base_config import load_config
    config = load_config()

    user = os.environ.get("QA_USER")
    password = os.environ.get("QA_PASSWORD")
    if not user or not password:
        sys.exit("QA_USER and QA_PASSWORD must be set in .env")

    auth = AuthHelper(config.get("api_base_url", config["base_url"]))
    token = auth.login(user, password)

    client = BaseAPIClient(config.get("api_base_url", config["base_url"]), token)
    discovery = DiscoveryHelper(client)

    # If site specified, just show that site
    if args.site:
        info = discovery.discover_all(args.site)
        print_site_info(info)
    else:
        site_id = int(os.environ.get("TEST_SITE_ID", "17"))
        info = discovery.discover_all(site_id)
        print_site_info(info)


def print_site_info(info):
    print(f"\n=== Site {info['site_id']} ===")
    print(f"Total channels: {info['total_channels']}")
    print(f"\n{'ID':<6} {'Name':<40} {'Model':<15} {'Snapshot'}")
    print("-" * 70)
    for ch in info["channels"]:
        snap = "YES" if ch["has_snapshot"] else "NO"
        print(f"{ch['id']:<6} {str(ch.get('name') or '')[:40]:<40} {ch.get('model') or ''!s:<15} {snap}")


if __name__ == "__main__":
    main()
