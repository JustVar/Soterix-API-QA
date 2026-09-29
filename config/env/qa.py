"""The QA server. A new server edits this file and .env, nothing else.

Keys a new server needs: base_url, api_base_url, integration_api_base_url,
test_site_name, test_camera_name. The account comes from QA_USER and
QA_PASSWORD in .env. A second server is a copy of this file under
config/env/<name>.py, selected with ENV=<name>.
"""
import os

config = {
    "base_url": "https://qa.example.invalid",          # the QA server
    "api_base_url": "https://qa.example.invalid/v-apiserver",

    # Third-party surface. Static key auth via VSAAS_INTEGRATION_KEY in .env.
    # Set None on a server that does not deploy it: the integration suite
    # then skips instead of failing.
    "integration_api_base_url": "https://qa.example.invalid/v-integration-api",

    # Safety flags. Tests that create data run only when both are True
    # (fixture data_write_gate), because a test that creates must also
    # remove.
    "allow_write": True,
    "allow_delete": True,

    # Test data. Tests that write data resolve the site by this name
    # (fixture data_site_id) and the camera by name inside that site
    # (fixture data_channel_id), never by a number. Set these to a site
    # and a camera the QA_USER account can see. If a lookup fails, the
    # skip message lists the names the account sees: fix the name here.
    "test_site_name": "Newtown Action Area",
    "test_camera_name": "main gate",
}


def get_credentials():
    """The account from .env. Empty strings when the keys are unset."""
    return {
        "email": os.environ.get("QA_USER", ""),
        "password": os.environ.get("QA_PASSWORD", ""),
    }
