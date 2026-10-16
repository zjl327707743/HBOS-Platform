app_name = "hb_knowledge_app"
app_title = "HBOS Knowledge"
app_publisher = "HBOS"
app_description = "Controlled knowledge access and evidence delivery"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["frappe", "hbos_portal"]
before_request = ["hb_knowledge_app.hb_knowledge.frappe_factory.setup_request"]
after_migrate = ["hb_knowledge_app.hb_knowledge.k1c2_migration.add_indexes"]

hbos_portal_provider = [
    "hb_knowledge_app.hb_knowledge.portal.provider.get_provider",
]
