"""Payload-safe errors for the offline protocol."""
from dataclasses import dataclass


class ContractError(ValueError):
    def __init__(self, code: str, path: str):
        self.code = code
        self.path = path
        super().__init__(f"{code}: {path}")


@dataclass(frozen=True, slots=True)
class RegistryFailure:
    input_index: int
    code: str
    path: str
