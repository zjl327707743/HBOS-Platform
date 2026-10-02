from __future__ import annotations

import unittest

from hbos_portal.services.internal_users import classify_internal_user


class InternalUserAccessTest(unittest.TestCase):
    def test_enabled_website_and_system_users_are_internal(self):
        for user_type in ("Website User", "System User"):
            with self.subTest(user_type=user_type):
                decision = classify_internal_user(
                    "employee@example.test",
                    account={"enabled": 1, "user_type": user_type},
                    roles={"All"},
                )
                self.assertTrue(decision.allowed)

    def test_guest_disabled_external_service_and_privileged_users_are_denied(self):
        cases = (
            ("Guest", {"enabled": 1, "user_type": "Website User"}, {"All"}),
            ("disabled@example.test", {"enabled": 0, "user_type": "Website User"}, {"All"}),
            ("customer@example.test", {"enabled": 1, "user_type": "Website User"}, {"Customer"}),
            ("service@example.test", {"enabled": 1, "user_type": "System User"}, {"Integration User"}),
            ("manager@example.test", {"enabled": 1, "user_type": "System User"}, {"System Manager"}),
        )
        for user, account, roles in cases:
            with self.subTest(user=user):
                self.assertFalse(
                    classify_internal_user(user, account=account, roles=roles).allowed
                )

    def test_configured_account_denial_wins(self):
        decision = classify_internal_user(
            "external@example.test",
            account={"enabled": 1, "user_type": "Website User"},
            roles={"All"},
            config={"hbos_portal_external_accounts": ["external@example.test"]},
        )
        self.assertFalse(decision.allowed)


if __name__ == "__main__":
    unittest.main()
