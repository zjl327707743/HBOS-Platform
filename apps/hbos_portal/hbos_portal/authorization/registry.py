"""Explicit injection only. No installed-App loader or runtime authorization."""
from types import MappingProxyType
from collections.abc import Mapping

from .contracts import RegistrationInput, RegistrySnapshot
from .errors import ContractError, RegistryFailure
from .validation import _app_id, _text, validate_definition


def build_definition_registry(inputs):
    candidates = {}
    failures = []
    for index, entry in enumerate(inputs):
        try:
            if not isinstance(entry, RegistrationInput):
                raise ContractError("INVALID_TYPE", "input")
            _text(entry.source_id, "source_id")
            expected = _app_id(entry.expected_app_id, "expected_app_id")
            data = entry.definition
            if not isinstance(data, Mapping):
                raise ContractError("INVALID_TYPE", "definition")
            if "app_id" not in data:
                raise ContractError("MISSING_FIELD", "definition.app_id")
            claimed = _app_id(data["app_id"], "definition.app_id")
            if claimed != expected:
                raise ContractError("SOURCE_MISMATCH", "definition.app_id")
            candidates.setdefault(expected, []).append((index, entry))
        except ContractError as error:
            failures.append(RegistryFailure(index, error.code, error.path))
    apps = {}
    for app_id, entries in sorted(candidates.items()):
        if len(entries) > 1:
            failures.extend(RegistryFailure(i, "DUPLICATE_APP", "definition.app_id") for i, _ in entries)
            continue
        index, entry = entries[0]
        try:
            apps[app_id] = validate_definition(entry.definition, entry.source_id, entry.expected_app_id)
        except ContractError as error:
            failures.append(RegistryFailure(index, error.code, error.path))
    return RegistrySnapshot(MappingProxyType(apps), tuple(sorted(failures, key=lambda f: f.input_index)))
