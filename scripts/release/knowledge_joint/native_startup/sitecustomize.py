"""Fail closed before any candidate process imports provider SDKs."""
import os
if os.environ.get('HBOS_RECOVERY_PROVIDER_BUDGET'):
    try:
        from knowledge_service.provider_budget import install_from_environment
        if install_from_environment() is None:raise RuntimeError('Audit hook unavailable')
    except BaseException:
        os._exit(78)
if os.environ.get('HBOS_MODEL_EGRESS_REQUIRED')=='1':
    try:
        from knowledge_service.model_egress import install_from_environment
        if install_from_environment() is None:raise RuntimeError('Model boundary unavailable')
    except BaseException:
        os._exit(78)
