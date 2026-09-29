"""Load the server config and the account for a run.

ENV selects config/env/<ENV>.py (default qa). That file holds the server
hosts, the write and delete flags and the test data names. The account
comes from QA_USER and QA_PASSWORD in .env. A new server is an edit to
those two files and nothing else.
"""
import importlib
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present. QA_USER, QA_PASSWORD and the optional keys that
# .env.template lists come from there.
load_dotenv()

# Env-resolution log. A named logger with its own handler keeps the process
# root logger untouched, so each test suite can configure its own logging.
# The path is anchored to the repo root so runs started from a subdirectory
# do not scatter logs/ directories around.
ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "env_config.log"
_log = logging.getLogger("env_config")
if not _log.handlers:
    _handler = logging.FileHandler(LOG_FILE)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(_handler)
    _log.setLevel(logging.INFO)
    _log.propagate = False

ENV_DIR = ROOT / "config" / "env"


def _env_name() -> str:
    return (os.environ.get("ENV") or "qa").strip().lower()


def _env_module():
    """Import config/env/<ENV>.py. An unknown ENV lists the files that exist."""
    env = _env_name()
    module_path = f"config.env.{env}"
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        if e.name != module_path:
            raise                    # the env file itself failed to import
        known = sorted(p.stem for p in ENV_DIR.glob("*.py") if p.stem != "__init__")
        raise RuntimeError(
            f"Unknown ENV '{env}'. config/env/ holds: {', '.join(known)}. "
            f"To add a server, copy config/env/qa.py to config/env/<name>.py "
            f"and run with ENV=<name>.") from e


def load_config():
    mod = _env_module()
    cfg = getattr(mod, "config", None)
    if not isinstance(cfg, dict):
        raise RuntimeError(f"config/env/{_env_name()}.py must define a dict named 'config'")  # noqa: TRY004 - every config failure raises RuntimeError on purpose
    _log.info(f"[ENV RESOLVED] ENV='{_env_name()}' | base_url={cfg.get('base_url')}")
    return cfg


def get_credentials():
    """The account the suite signs in as: {"email", "password"} from .env."""
    return _env_module().get_credentials()


def is_write_allowed():
    """Check if write operations (POST/PUT) are allowed in current environment."""
    return config.get("allow_write", False)


def is_delete_allowed():
    """Check if delete operations are allowed in current environment."""
    return config.get("allow_delete", False)


# Exposed to the rest of the test suite:
config = load_config()
