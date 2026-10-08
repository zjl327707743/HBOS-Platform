"""让 Desk 页面脚本的浏览器缓存失效。

## 为什么需要它

Frappe 把标准 Page 的脚本缓存在**浏览器 localStorage** 里（`_page:<页面名>`），
下次打开直接读缓存、不再问服务端（`frappe/public/js/frappe/views/pageview.js`
的 `with_page`）。失效判据是同文件 `desk.js` 的 `sync_pages`：

    if (!page_info[name] || page_info[name].modified != p.modified)
        delete localStorage["_page:" + name]

即**比对 `Page` 文档的 `modified` 时间戳**。而修改磁盘上的 `<page>.js` 只改文件，
**不会**动 `Page` 文档——所以改完 JS，所有看过该页的浏览器会一直跑旧版本，
且永远不会自愈。本脚本把 `modified` 顶到现在，使下一次 Desk 加载时
`sync_pages` 判定不一致、清掉那批缓存。

## 正确做法

改完考勤页面的 `.js`（或它引用的共享 CSS）后执行一次：

    bench --site frontend execute hb_attendance_app.hbos_attendance.bump_page_cache.run

指定页面：

    bench --site frontend execute hb_attendance_app.hbos_attendance.bump_page_cache.run \
        --kwargs '{"pages": ["hbos-employee-management"]}'

之后用户**普通刷新** Desk 即可——不需要 Ctrl+Shift+R（那个快捷键反而会清掉
全部 localStorage，代价更大）。

## 边界

只写 `modified`，不碰 `script` / `style` / 角色 / 名称。可反复执行。
"""
import frappe

# 本 App 的标准 Page 名（`Page.name` 前缀）。改了这个前缀要同步这里。
DEFAULT_PREFIX = "hbos-%"


def run(pages=None):
    """把指定页面（默认本 App 全部标准页）的 modified 顶到当前时间。

    pages: 页面名列表；None 表示按 DEFAULT_PREFIX 匹配。
    返回 {updated, pages:[{name, before, after}], cache_cleared}
    """
    if pages:
        placeholders = ", ".join(["%s"] * len(pages))
        rows = frappe.db.sql(
            f"SELECT name, modified FROM tabPage WHERE name IN ({placeholders}) ORDER BY name",
            tuple(pages),
            as_dict=True,
        )
    else:
        rows = frappe.db.sql(
            "SELECT name, modified FROM tabPage WHERE name LIKE %s ORDER BY name",
            (DEFAULT_PREFIX,),
            as_dict=True,
        )

    if not rows:
        frappe.msgprint("没有匹配的 Page，未做任何修改")
        return {"updated": 0, "pages": [], "cache_cleared": False}

    before = {r["name"]: str(r["modified"]) for r in rows}
    names = list(before)

    # 一次性 UPDATE：只改 modified，不触碰其它字段
    placeholders = ", ".join(["%s"] * len(names))
    frappe.db.sql(
        f"UPDATE tabPage SET modified = NOW() WHERE name IN ({placeholders})",
        tuple(names),
    )
    frappe.db.commit()

    after_rows = frappe.db.sql(
        f"SELECT name, modified FROM tabPage WHERE name IN ({placeholders}) ORDER BY name",
        tuple(names),
        as_dict=True,
    )
    after = {r["name"]: str(r["modified"]) for r in after_rows}

    # boot 的 page_info 可能被缓存，清一次确保下一次加载就带上新时间戳
    frappe.clear_cache()

    result = {
        "updated": len(names),
        "pages": [{"name": n, "before": before[n], "after": after[n]} for n in names],
        "cache_cleared": True,
    }
    frappe.msgprint(
        "已更新 {} 个页面的 modified：{}".format(len(names), "、".join(names))
    )
    return result
