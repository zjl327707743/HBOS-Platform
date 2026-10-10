app_name = "hb_twin_app"
app_title = "HBOS Twin"
app_publisher = "HBOS"
app_description = "Protected equipment and digital-twin asset delivery"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["frappe", "hbos_portal"]

hbos_portal_provider = [
    "hb_twin_app.hb_twin.portal.provider.get_provider",
]
