from __future__ import annotations

import frappe
from frappe.model.document import Document

from hbos_portal.auth.feishu import identity_key


class HBOSExternalIdentity(Document):
    def validate(self) -> None:
        if self.provider != "feishu":
            frappe.throw("当前仅支持飞书外部身份。")
        if self.id_type != "open_id":
            frappe.throw("飞书身份绑定必须显式使用 open_id。")
        for fieldname in ("tenant_key", "app_id", "external_id", "user"):
            if not str(self.get(fieldname) or "").strip():
                frappe.throw(f"{fieldname} 不能为空。")
        old = self.get_doc_before_save()
        identity_fields = ("provider", "tenant_key", "app_id", "id_type", "external_id", "user")
        changed = not old or any(self.get(k) != old.get(k) for k in identity_fields) or (self.enabled and not old.enabled)
        authority = getattr(frappe.flags, "hbos_identity_authority", None)
        if changed and authority != tuple(self.get(k) for k in identity_fields):
            frappe.throw("飞书绑定须在账号与安全中验证双方身份，不能手工建立或转移。")
        from hbos_portal.auth.migration import active_user_key

        self.active_user_key = active_user_key(self.provider, self.tenant_key, self.app_id, self.user) if self.enabled else None
        self.identity_key = identity_key(
            provider=self.provider,
            tenant_key=self.tenant_key,
            app_id=self.app_id,
            id_type=self.id_type,
            external_id=self.external_id,
        )

    def on_trash(self):
        if not (frappe.conf.get('hbos_account_test_site') and frappe.flags.get('hbos_owned_test_cleanup')):
            frappe.throw('飞书绑定历史不得删除；请使用受控变更流程。', frappe.PermissionError)
