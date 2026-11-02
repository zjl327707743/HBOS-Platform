"""One server-side download decision, two configurable scopes.

The current business scope is ``shared_all_authenticated``: every signed-in,
normally enabled HBOS business user may read and download the original of a
current, published, shared document without a per-file grant. The same entry
point already carries ``department_scoped`` so a future department restriction
is a configuration change, not a new authorization stack.

What this decision never relaxes: the subject must be enabled (anonymous and
disabled accounts are refused before this function is reached), the version must
be the current published one, the original must not be explicitly withheld as a
sensitive exception, and original delivery must be enabled. An unknown scope
denies rather than falling back to the shared one.
"""
from dataclasses import dataclass

SHARED_ALL_AUTHENTICATED = 'shared_all_authenticated'
DEPARTMENT_SCOPED = 'department_scoped'
ACTION = 'document.download'
SCOPES = (SHARED_ALL_AUTHENTICATED, DEPARTMENT_SCOPED)


@dataclass(frozen=True)
class DownloadDecision:
    allowed: bool
    action: str
    reason: str
    scope: str
    requires_current_version: bool = True
    requires_short_lived_delivery: bool = True
    requires_audit: bool = True


def document_download_decision(*, subject_enabled, version_current,
                               scope=SHARED_ALL_AUTHENTICATED, iam_allowed=False,
                               department_allowed=False, public_download_allowed=False,
                               delivery_enabled=False, withheld=False,
                               synthetic=False):
    """Return the one download decision for this binding and subject.

    ``iam_allowed``/``department_allowed``/``public_download_allowed`` are only
    consulted under ``department_scoped``; a legacy per-file grant is passed as
    ``iam_allowed`` there so an existing grant keeps working after the scope
    changes. Under the shared scope they are irrelevant by design, and search
    or read permission alone is still not what grants the action - the scope
    does, together with every check below.
    """
    if scope not in SCOPES:
        return DownloadDecision(False, ACTION, 'DOWNLOAD_SCOPE_UNKNOWN', str(scope))
    if not subject_enabled:
        return DownloadDecision(False, ACTION, 'SUBJECT_DISABLED', scope)
    if not version_current:
        return DownloadDecision(False, ACTION, 'SOURCE_VERSION_STALE', scope)
    if synthetic:
        # A synthetic test binding is never a company document an employee reads.
        return DownloadDecision(False, ACTION, 'SYNTHETIC_BINDING_REFUSED', scope)
    if withheld:
        return DownloadDecision(False, ACTION, 'ORIGINAL_WITHHELD', scope)
    if not delivery_enabled:
        return DownloadDecision(False, ACTION, 'ORIGINAL_DELIVERY_DISABLED', scope)
    if scope == DEPARTMENT_SCOPED and not (iam_allowed and (
            department_allowed or public_download_allowed)):
        return DownloadDecision(False, ACTION,
                                'IAM_PERMISSION_REQUIRED' if not iam_allowed
                                else 'DOWNLOAD_SCOPE_REQUIRED', scope)
    return DownloadDecision(True, ACTION, 'DOWNLOAD_AUTHORIZED', scope)
