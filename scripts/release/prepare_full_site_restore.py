"""Offline proposal and pinned backup validation CLI. No execution option exists."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__:
    from .full_site_restore.common import BACKUP_EXPECTED, BEFORE_SHA256, RestoreError
    from .full_site_restore.plan import build_proposal
else:
    from full_site_restore.common import BACKUP_EXPECTED, BEFORE_SHA256, RestoreError
    from full_site_restore.plan import build_proposal


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # Operator mistakes never echo file paths, arbitrary argv or secrets.
        raise RestoreError("RESTORE_ARGUMENTS_INVALID")


def main(argv=None) -> int:
    parser = SafeParser(description="Only show offline proposal or validate the pinned backup. Never execute.")
    parser.add_argument("--manifest", help="Explicit private host manifest; read-only validation only.")
    try:
        args = parser.parse_args(argv)
        if args.manifest is None:
            result = build_proposal()
        else:
            # Import lazily: default proposal does not even open backup files.
            if __package__:
                from .full_site_restore.inputs import validate_backup_inputs
            else:
                from full_site_restore.inputs import validate_backup_inputs
            pins = {key: dict(value) for key, value in BACKUP_EXPECTED.items()}
            result = {"status": "OFFLINE_INPUT_VALIDATION_ONLY", "runtime_ready": False,
                      "execution": "NOT_IMPLEMENTED",
                      "inputs": validate_backup_inputs(Path(args.manifest), pins, BEFORE_SHA256)}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except RestoreError as error:
        print(json.dumps({"status": "REJECTED", "code": error.code, "runtime_ready": False}))
        return 2
    except (OSError, ValueError, TypeError, OverflowError):
        print(json.dumps({"status": "REJECTED", "code": "RESTORE_VALIDATION_FAILED", "runtime_ready": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
