"""Print the cameras of a site on the QA server.

Use it to fill test_site_name and test_camera_name in config/env/qa.py on
a new server: the first call lists the sites the account sees, the second
lists the cameras of one site.

Usage:
    python tools/discover_cameras.py                # first site the account sees
    python tools/discover_cameras.py --site 16      # one site by id
    python tools/discover_cameras.py --env other    # config/env/other.py

Credentials come from QA_USER/QA_PASSWORD in .env, same as the test suite.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_clients.auth_helper import AuthHelper
from api_clients.base_api_client import BaseAPIClient
from api_clients.discovery_helper import DiscoveryHelper
from api_clients.site_discovery import SiteDiscovery


def main():
    parser = argparse.ArgumentParser(description="List the sites and cameras the account sees")
    parser.add_argument("--env", default=os.getenv("ENV", "qa"), help="config/env/<ENV>.py (default qa)")
    parser.add_argument("--site", type=int, help="Site id. Default: the first site the account sees")
    args = parser.parse_args()

    os.environ["ENV"] = args.env

    from dotenv import load_dotenv
    load_dotenv()
    from config.base_config import get_credentials, load_config
    config = load_config()

    creds = get_credentials()
    if not creds["email"] or not creds["password"]:
        sys.exit("QA_USER and QA_PASSWORD must be set in .env")

    api_base_url = config.get("api_base_url", config["base_url"])
    auth = AuthHelper(api_base_url)
    token = auth.login(creds["email"], creds["password"])

    client = BaseAPIClient(api_base_url, token)
    discovery = DiscoveryHelper(client)

    site_id = args.site
    if site_id is None:
        sites = SiteDiscovery(api_base_url, token).get_user_sites(creds["email"])
        if not sites:
            sys.exit(f"The account {creds['email']} sees no sites on {api_base_url}")
        print_sites(sites)
        site_id = int(sites[0]["siteId"])

    print_site_info(discovery.discover_all(site_id))


def print_sites(sites):
    print(f"\n{'ID':<6} Site")
    print("-" * 50)
    for site in sites:
        print(f"{site.get('siteId', ''):<6} {site.get('name') or ''}")


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
