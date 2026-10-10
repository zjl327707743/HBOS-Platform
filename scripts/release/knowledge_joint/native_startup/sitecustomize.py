"""Install the approved audit hook before native child workers import SDKs."""
import os
if os.environ.get('HBOS_RECOVERY_PROVIDER_BUDGET'):
    try:
        from knowledge_service.provider_budget import install_from_environment
        if install_from_environment() is None:raise RuntimeError('Audit hook unavailable')
    except BaseException:
        os._exit(78)
