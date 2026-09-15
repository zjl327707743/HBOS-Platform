"""配置——全部来自环境变量，便于部署时调整而不改代码。"""

from __future__ import annotations

import os

from .contract import BACKEND_STUB

#: 默认后端。冒烟测试用 stub；实测时切到 c1_local_vlm / c2_ocr。
DEFAULT_BACKEND = os.environ.get("HBOS_OCR_BACKEND", BACKEND_STUB)

#: 监听地址与端口。
#: 默认绑 **127.0.0.1**——只允许本机访问；Frappe 容器经 host.docker.internal
#: 连进来时，容器看到的是宿主机网关地址，故如确需容器访问需改为 0.0.0.0
#: （见 README 的「网络与安全」一节）。
HOST = os.environ.get("HBOS_OCR_HOST", "127.0.0.1")
PORT = int(os.environ.get("HBOS_OCR_PORT", "8100"))

#: 单张识别超时（秒）。M3-R6 验收标准要求 P95 ≤ 10 秒，此处留出余量。
TIMEOUT_SECONDS = int(os.environ.get("HBOS_OCR_TIMEOUT", "60"))

#: 上传图片大小上限（字节）。标签照片按 5 MB 足够。
MAX_IMAGE_BYTES = int(os.environ.get("HBOS_OCR_MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))

#: 幂等缓存条数与存活秒数（**进程内，非持久**）。
#: 够覆盖"同一次入库重复点击"的场景即可；不追求跨重启幂等。
IDEMPOTENCY_TTL_SECONDS = int(os.environ.get("HBOS_OCR_IDEMPOTENCY_TTL", "600"))
IDEMPOTENCY_MAX_ITEMS = int(os.environ.get("HBOS_OCR_IDEMPOTENCY_MAX", "500"))

#: C1 模型路径覆盖。
C1_MODEL = os.environ.get("HBOS_OCR_C1_MODEL", "")

#: 日志级别。日志**绝不记录照片内容、批号或产品名**（M3-R6 方案第六节）。
LOG_LEVEL = os.environ.get("HBOS_OCR_LOG_LEVEL", "INFO")
