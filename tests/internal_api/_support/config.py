"""Support config for the ported flow tests (endpoint sweep, e2e).

- The host comes from the active ENV (config/env/<ENV>.py), so these tests
  point at the same server as the rest of the suite.
- NO credentials here, on purpose: auth is the shared api_auth_token
  fixture (session login via AuthHelper).
- Tuning knobs (timeouts, export duration, the media-share recipient) read
  from the environment with safe defaults.
- Lives under tests/internal_api/_support so it cannot shadow the
  repo-root config/ package.

This module lives under tests/internal_api/_support so it never shadows the
repo-root config/ package the way the original top-level config.py did.
"""
import os

from config.base_config import config as _env

# Host without the /v-apiserver suffix (the prefixes below add it).
BASE_URL = _env.get("base_url", "")

API_PREFIX = "/v-apiserver/REST/central"
API_PREFIX_SITE = "/v-apiserver/REST/site"
API_PREFIX_ENTERPRISE = "/v-apiserver/REST/enterprise"
API_PREFIX_ROOT = "/v-apiserver/REST"

# Request timeout (seconds). Generous by default: snapshot/aggregation
# endpoints are known to be slow.
DEFAULT_TIMEOUT = int(os.getenv("API_TIMEOUT_SECONDS", "120"))

# How long an async clip/media export job may stay INPROGRESS before the
# e2e test fails it. Recon showed jobs still INPROGRESS past 5 minutes even
# for a real recorded clip, so this is deliberately shorter than that.
CLIP_EXPORT_TIMEOUT_SECONDS = int(os.getenv("CLIP_EXPORT_TIMEOUT_SECONDS", "120"))

# How much of the recorded window to request for export, in seconds. Clamped
# to whatever footage is actually available, so a short real clip still works.
CLIP_EXPORT_DURATION_SECONDS = int(os.getenv("CLIP_EXPORT_DURATION_SECONDS", "60"))

# Optional site/channel pin. Unset by default: discovery uses the first
# site/channel the account can see. The e2e tests resolve these through the
# shared fixtures, so setting these is only for targeting a specific camera.
TEST_SITE_ID = os.getenv("TEST_SITE_ID")
TEST_CHANNEL_ID = os.getenv("TEST_CHANNEL_ID")

# Recipient for the media-share step. Empty by default so the share test
# SKIPS instead of sending a real email. Set MEDIA_SHARE_TEST_EMAIL in .env
# to a recipient who agreed to receive it before running that test.
MEDIA_SHARE_TEST_EMAIL = os.getenv("MEDIA_SHARE_TEST_EMAIL", "")
