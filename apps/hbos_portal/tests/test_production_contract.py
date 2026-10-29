"""生产看板 Portal 适配器 —— 权限与契约测试。

**本文件里最重要的是「默认拒绝」那几条**：Owner 还没批准生产角色，
所以在授权矩阵落地前，除 Administrator 外任何人都进不去。
这几条一旦被改坏，等于把生产数据对全员开放。
"""

from __future__ import annotations

import unittest

from hbos_portal.contracts.manifest import AppManifest
from hbos_portal.production.access import build_access_context
from hbos_portal.production.manifest import get_manifest


class ProductionManifestTest(unittest.TestCase):
    def test_manifest_is_valid_and_native(self):
        manifest = AppManifest.from_mapping(get_manifest())
        self.assertEqual("production", manifest.id)
        self.assertEqual("/hbos/production", manifest.route)
        self.assertEqual("native", manifest.migration_mode)
        # 本轮不提供 summary/tasks/search 聚合
        self.assertEqual((), manifest.capabilities)


class ProductionAccessDefaultDenyTest(unittest.TestCase):
    """**默认拒绝** —— 本组是权限接入的核心断言。"""

    def test_guest_denied(self):
        for user in (None, "", "Guest"):
            with self.subTest(user=user):
                ctx = build_access_context(user, [])
                self.assertFalse(ctx["can_enter"])
                self.assertEqual([], ctx["capabilities"])

    def test_ordinary_user_denied(self):
        """普通员工（哪怕有其它业务角色）在 Owner 批准前一律拒绝。"""
        ctx = build_access_context("zhang@example.com", ["Employee", "Stock User"])
        self.assertFalse(ctx["can_enter"])
        self.assertEqual([], ctx["capabilities"])

    def test_platform_roles_do_not_grant_production(self):
        """平台管理角色 ≠ 生产业务角色（IAM 边界提案 §3）。"""
        ctx = build_access_context(
            "manager@example.com",
            ["System Manager", "HR Manager", "Accounts Manager"],
        )
        self.assertFalse(ctx["can_enter"])

    def test_administrator_allowed_as_break_glass(self):
        """内置 Administrator 是本仓库既有的审计 break-glass 身份。"""
        ctx = build_access_context("Administrator", [])
        self.assertTrue(ctx["can_enter"])
        self.assertEqual(["production.board.read"], ctx["capabilities"])

    def test_context_carries_no_raw_role_names(self):
        """access 契约只回语义化结果，不把原始角色名透给前端。"""
        ctx = build_access_context("Administrator", ["System Manager"])
        self.assertEqual(
            {"app_id", "can_enter", "capabilities", "scopes"},
            set(ctx),
        )
        serialized = str(ctx)
        self.assertNotIn("System Manager", serialized)

    def test_scope_is_empty_not_all(self):
        """范围留空表示「还没有范围能力」，**不等于 ALL**。"""
        ctx = build_access_context("Administrator", [])
        self.assertEqual({}, ctx["scopes"])


if __name__ == "__main__":
    unittest.main()
