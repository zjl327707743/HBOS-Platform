"""Read a verified native private artifact without remote File retrieval."""
from pathlib import Path
import frappe


def private_content(file, *, max_size=50*1024*1024):
    url=file.file_url
    if not file.is_private or not isinstance(url,str) or not url.startswith('/private/files/') or any(char in url for char in ('?','#','\\')):
        frappe.throw('附件不是可核验的本站私有文件。',frappe.PermissionError)
    root=Path(frappe.get_site_path('private','files')).resolve()
    try:
        path=Path(file.get_full_path()).resolve(strict=True)
        if root not in path.parents or not path.is_file() or not 0<path.stat().st_size<=max_size:
            raise ValueError()
        content=path.read_bytes()
        if len(content)>max_size:raise ValueError()
        return content
    except (OSError,ValueError):
        frappe.throw('附件路径、内容或大小已变化。',frappe.PermissionError)
