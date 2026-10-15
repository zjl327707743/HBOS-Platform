"""Independent IAM decision point; original delivery remains disabled in UAT5."""
from dataclasses import dataclass

ACTION='document.download'

@dataclass(frozen=True)
class DownloadDecision:
    allowed:bool
    action:str
    reason:str
    requires_current_version:bool=True
    requires_short_lived_delivery:bool=True
    requires_audit:bool=True

def document_download_decision(*,subject_enabled,version_current,iam_allowed=False,
                               department_allowed=False,public_download_allowed=False):
    # Search permission is deliberately absent. Future delivery must supply an
    # independent IAM allow, department/public scope and a fresh version proof.
    if not subject_enabled:return DownloadDecision(False,ACTION,'SUBJECT_DISABLED')
    if not version_current:return DownloadDecision(False,ACTION,'SOURCE_VERSION_STALE')
    if not iam_allowed:return DownloadDecision(False,ACTION,'IAM_PERMISSION_REQUIRED')
    if not (department_allowed or public_download_allowed):return DownloadDecision(False,ACTION,'DOWNLOAD_SCOPE_REQUIRED')
    return DownloadDecision(False,ACTION,'ORIGINAL_DELIVERY_DISABLED')
