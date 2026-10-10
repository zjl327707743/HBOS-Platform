"""Same native API or metadata-only controller. Never full/unscoped worker startup."""
import os,sys
from knowledge_service.provider_budget import install_from_environment
os.environ['HBOS_PROVIDER_ACCOUNTING_MODE']='AUDIT_ONLY'
if install_from_environment() is None:raise SystemExit('Approved provider identity/audit route configuration is required')
if len(sys.argv)!=2 or sys.argv[1] not in ('api','controller'):raise SystemExit('Supported native role: api/controller')
if sys.argv[1]=='api':
    from knowledge_service.hbos_gateway.native_rerank import install_ragflow_extension
    install_ragflow_extension(os.environ['HBOS_RECOVERY_PROVIDER_BUDGET'],
        expected_source_sha256='69335398b94a9ac09762cae9f867d889bda657bc7143a2947e9901c4ad739101')
    from api.apps import app
    app.run(host='0.0.0.0',port=9380,use_reloader=False,access_log_format='')
else:
    sys.argv=['maintenance_controller',os.environ['HBOS_MAINTENANCE_CONTROLLER_CONFIG']]
    from knowledge_service.maintenance_controller import main
    main()
