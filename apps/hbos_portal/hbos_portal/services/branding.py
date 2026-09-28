from __future__ import annotations


def get_branding() -> dict[str, object]:
    """P2 keeps branding configuration-free.

    Future Portal Settings may override these fields without changing the
    bootstrap contract.
    """

    return {
        "product_name": "HBOS",
        "company_name": "海滨",
        "logo_url": None,
        "workspace_name": "海滨智能运营工作台",
    }


def get_user_identity(user: str) -> dict[str, object]:
    import frappe

    values = frappe.db.get_value(
        "User",
        user,
        ["full_name", "user_image"],
        as_dict=True,
    ) or {}

    display_name = values.get("full_name") or user
    avatar_url = values.get("user_image")

    return {
        "id": user,
        "display_name": display_name,
        "avatar_url": avatar_url,
        # P2 does not infer provider from client input.
        # Feishu identity mapping will populate this in a later phase.
        "identity_provider": "frappe",
    }
