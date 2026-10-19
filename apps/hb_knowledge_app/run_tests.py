"""Run the knowledge-domain test suite with the correct package layout.

The Frappe app is imported as ``hb_knowledge_app`` from its package parent
``apps/hb_knowledge_app`` (inside it, ``hb_knowledge_app/`` is the real
package). pytest's rootdir insertion can instead resolve the container
directory of the same name, which has no ``hb_knowledge`` submodule. Import
the real package first, then hand the suite to pytest.

Usage (from this directory or the repository root):
    python apps/hb_knowledge_app/run_tests.py [pytest args...]
"""
from __future__ import annotations
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import hb_knowledge_app.hb_knowledge  # noqa: F401  (binds the real package)

import pytest  # noqa: E402

if __name__ == '__main__':
    arguments = sys.argv[1:] or ['tests/', '-q']
    # importlib mode avoids re-importing ``tests`` as a subpackage of the app
    # package, which the container/app directory name collision would break.
    if '--import-mode' not in arguments:
        arguments = [*arguments, '--import-mode=importlib']
    raise SystemExit(pytest.main(arguments))
