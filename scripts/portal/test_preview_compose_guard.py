#!/usr/bin/env python3
"""Regression cases for the isolated Preview volume contract."""
import copy
import unittest

from preview_compose_guard import (
    ASSET_USERS,
    BAD_ASSETS,
    BENCH_ASSETS,
    FRAPPE_SERVICES,
    SITES,
    validate_compose,
)

PROJECT = "hbos-portal-preview"


def valid_config():
    services = {}
    for service in FRAPPE_SERVICES:
        volumes = [{"type": "volume", "source": f"{PROJECT}_sites", "target": SITES}]
        if service in ASSET_USERS:
            volumes.append(
                {
                    "type": "volume",
                    "source": f"{PROJECT}_assets-data",
                    "target": BENCH_ASSETS,
                }
            )
        services[service] = {"volumes": volumes}
    return {
        "name": PROJECT,
        "volumes": {
            "sites": {"name": f"{PROJECT}_sites"},
            "assets-data": {"name": f"{PROJECT}_assets-data"},
        },
        "services": services,
    }


class PreviewComposeGuardTests(unittest.TestCase):
    def test_valid_isolated_volume_layout(self):
        validate_compose(valid_config(), PROJECT)

    def test_compose_logical_sources_are_valid_if_declared_names_are_isolated(self):
        data = valid_config()
        for service in FRAPPE_SERVICES:
            for volume in data["services"][service]["volumes"]:
                if volume["target"] == SITES:
                    volume["source"] = "sites"
                elif volume["target"] == BENCH_ASSETS:
                    volume["source"] = "assets-data"
        validate_compose(data, PROJECT)

    def test_nested_sites_assets_mount_must_fail_even_if_named(self):
        data = valid_config()
        data["services"]["backend"]["volumes"].append(
            {"type": "volume", "source": f"{PROJECT}_assets-data", "target": BAD_ASSETS}
        )
        with self.assertRaisesRegex(ValueError, "EBUSY"):
            validate_compose(data, PROJECT)

    def test_no_service_can_mount_nested_assets(self):
        data = valid_config()
        data["services"]["hbos-web-prepare"] = {
            "volumes": [{"type": "volume", "source": f"{PROJECT}_assets-data", "target": BAD_ASSETS}]
        }
        with self.assertRaisesRegex(ValueError, "EBUSY"):
            validate_compose(data, PROJECT)

    def test_foreign_sites_volume_is_not_accepted(self):
        data = valid_config()
        data["services"]["queue-short"]["volumes"][0]["source"] = "production_sites"
        with self.assertRaisesRegex(ValueError, "not Preview-namespaced"):
            validate_compose(data, PROJECT)

    def test_reused_global_volume_name_is_not_accepted(self):
        data = valid_config()
        data["volumes"]["sites"]["name"] = "sites"
        with self.assertRaisesRegex(ValueError, "must resolve"):
            validate_compose(data, PROJECT)

    def test_missing_assets_volume_is_not_accepted(self):
        data = valid_config()
        data["services"]["backend"]["volumes"].pop()
        with self.assertRaisesRegex(ValueError, "bench/assets"):
            validate_compose(data, PROJECT)

    def test_missing_required_service_is_not_accepted(self):
        data = valid_config()
        del data["services"]["configurator"]
        with self.assertRaisesRegex(ValueError, "missing"):
            validate_compose(data, PROJECT)

    def test_cross_project_config_is_not_accepted(self):
        data = valid_config()
        with self.assertRaisesRegex(ValueError, "differs"):
            validate_compose(data, "another-preview")

    def test_production_project_is_not_accepted(self):
        data = valid_config()
        data["name"] = "hbos-m0-r3a"
        with self.assertRaisesRegex(ValueError, "distinct"):
            validate_compose(data, "hbos-m0-r3a")


"""Focused supplementary tests. No Docker daemon, network, or real data."""


def with_db():
    config = valid_config()
    config['volumes']['db-data'] = {'name': f'{PROJECT}_db-data'}
    config['services']['db'] = {'volumes': [
        {'type': 'volume', 'source': 'db-data', 'target': '/var/lib/mysql'}
    ]}
    return config


class PreviewVolumeRegressionTests(unittest.TestCase):
    def test_namespaced_database_volume_allowed(self):
        validate_compose(with_db(), PROJECT)

    def test_foreign_database_volume_denied(self):
        config = with_db()
        config['volumes']['db-data'] = {'name': 'existing-business-db', 'external': True}
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)

    def test_external_site_volume_denied_even_if_name_matches(self):
        config = valid_config()
        config['volumes']['sites']['external'] = True
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)

    def test_local_volume_bind_to_host_database_denied(self):
        config = with_db()
        config['volumes']['db-data']['driver_opts'] = {
            'type': 'none', 'o': 'bind', 'device': '/protected-business-db'
        }
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)

    def test_undeclared_foreign_worker_volume_denied(self):
        config = valid_config()
        config['services']['queue-long']['volumes'].append(
            {'type': 'volume', 'source': 'business-backups', 'target': '/backups'}
        )
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)

    def test_anonymous_volume_denied(self):
        config = valid_config()
        config['services']['queue-long']['volumes'].append(
            {'type': 'volume', 'target': '/scratch-data'}
        )
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)

    def test_database_direct_host_bind_denied(self):
        config = with_db()
        config['services']['db']['volumes'] = [
            {'type': 'bind', 'source': '/private/business-db', 'target': '/var/lib/mysql'}
        ]
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)

    def test_invalid_volume_declaration_denied(self):
        config = valid_config()
        config['volumes']['sites'] = []
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)

    def test_invalid_service_mount_denied(self):
        config = valid_config()
        config['services']['backend']['volumes'].append('sites:/unknown')
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)

    def test_resolved_looking_alias_cannot_hide_foreign_volume(self):
        config = valid_config()
        config['volumes'][f'{PROJECT}_sites'] = {'name': 'existing-business-sites'}
        with self.assertRaises(ValueError):
            validate_compose(config, PROJECT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
