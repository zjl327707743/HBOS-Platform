#!/usr/bin/env bash
#
# 准备 PDF 中文渲染所需字体（幂等）
#
# ## 为什么需要这个脚本
#
# ERPNext 的 Print Format 由 wkhtmltopdf 渲染成 PDF，而 wkhtmltopdf 靠**系统字体**
# 画汉字。官方 erpnext 镜像里只有 DejaVu（无汉字），所以缺字体时汉字会被
# **静默丢弃**——ASCII 正常、汉字消失，不报错。
#
# 字体文件**不进代码仓库**（体积 + 授权），因此必须由部署步骤显式获取。
# 这个脚本就是那个"显式步骤"，让任何新环境都能**可验证地**重建出同样的渲染结果。
#
# ## ⚠ 只能用「可再分发」的字体
#
# 本脚本用的是 **Noto Serif SC（OFL-1.1，允许自由分发与嵌入）**。
#
# **不要**改用 macOS 自带的 `Songti.ttc`：那是 Apple 的授权字体，
# **打进 Docker 镜像 = 违反授权**。本分支开发期一度用过它，已移除；
# 改用 Noto 后四个打印格式的页数、页型、中文渲染实测完全一致。
#
# ## 用法
#
#     scripts/setup_fonts.sh                    # 下载 / 校验，写入 runtime/fonts/
#     scripts/setup_fonts.sh --install          # 再装进系统字体目录并刷新缓存
#     scripts/setup_fonts.sh --install-dir DIR  # 同上，自定安装目录
#     scripts/setup_fonts.sh --check            # 只校验现有状态，不下载（部署后冒烟）
#     scripts/setup_fonts.sh --dir DIR          # 换"仓库内"的目标目录
#
# **两种目录，别混淆**：
#
# | 选项 | 目录 | 用途 |
# | --- | --- | --- |
# | `--dir`（默认 `runtime/fonts/`） | 仓库内 | 给 docker-compose 挂载用 |
# | `--install`（默认 `~/.local/share/fonts`） | 用户字体目录 | **让 fontconfig 真的认得**（CI / 裸机用） |
#
# 只把文件放进 `runtime/fonts/` **不会**让 `fc-list` 认得——fontconfig 只扫系统目录。
# 在容器里它是靠 compose 挂到 `/usr/share/fonts/truetype/hbos` 才生效的；
# 没有挂载的环境（如 CI runner）必须显式 `--install`。
#
# 安装目录默认选**用户级**（`~/.local/share/fonts`，fontconfig 默认就扫它），
# 因此**不需要 root / sudo**。要装成全局的（如服务跑在别的账号下）就传
# `--install-dir /usr/share/fonts/truetype/hbos`，此时才可能需要 sudo。
#
# ## 容器侧验证（脚本会在最后自动尝试）
#
#     docker compose exec backend fc-list :lang=zh | wc -l    # 必须 > 0
#
# 注：脚本刻意**不使用关联数组**——macOS 自带 bash 3.2 不支持，而开发机就是 macOS。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FONT_DIR="${REPO_ROOT}/runtime/fonts"
CHECK_ONLY=0
INSTALL=0
# 默认装到**用户级**字体目录：fontconfig 默认就扫它，且不需要 root。
INSTALL_DIR="${HOME}/.local/share/fonts"

# 字体清单：`文件名|sha256|候选地址(空格分隔)`
#
# 校验和写死在这里，是为了让"下载到的东西"可验证——只校验"文件存在"
# 挡不住半截下载，或 CDN 返回一张 HTML 错误页。
#
# notofonts/noto-cjk 的 `Serif/SubsetOTF/SC` 是简体子集，单个约 12 MB。
FONTS='
NotoSerifSC-Regular.otf|e8f396decc1f0963a016a989c3d8852e863d1350996f573860a80767c83a1cd3|https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Serif/SubsetOTF/SC/NotoSerifSC-Regular.otf https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/SubsetOTF/SC/NotoSerifSC-Regular.otf
NotoSerifSC-Bold.otf|24693d48bdb9152f0a06b02af625638a1097abd6de4010ebba027f6e82710527|https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Serif/SubsetOTF/SC/NotoSerifSC-Bold.otf https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/SubsetOTF/SC/NotoSerifSC-Bold.otf
'

log() { printf '  %s\n' "$*"; }
err() { printf '::error:: %s\n' "$*" >&2; }

while [[ $# -gt 0 ]]; do
	case "$1" in
		--check | -c) CHECK_ONLY=1; shift ;;
		--install | -i) INSTALL=1; shift ;;
		--install-dir) INSTALL=1; INSTALL_DIR="${2:?--install-dir 需要一个路径}"; shift 2 ;;
		--dir) FONT_DIR="${2:?--dir 需要一个路径}"; shift 2 ;;
		--help | -h) sed -n '3,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
		*) err "未知参数：$1（用 --help 看用法）"; exit 2 ;;
	esac
done

sha256_of() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$1" | awk '{print $1}'
	else
		shasum -a 256 "$1" | awk '{print $1}'   # macOS
	fi
}

verify_file() { # 文件存在且校验和正确
	local file="$1" want="$2"
	[[ -f "${FONT_DIR}/${file}" ]] || return 1
	[[ "$(sha256_of "${FONT_DIR}/${file}")" == "${want}" ]]
}

download_file() { # 依次试候选地址；下载成功且校验和正确才算数
	local file="$1" want="$2" urls="$3" url tmp
	tmp="$(mktemp)"
	for url in ${urls}; do
		log "尝试 $(printf '%s' "${url}" | sed 's#/[^/]*$##' | cut -c1-52)…"
		# -f：HTTP 错误码变非零退出，避免把错误页当字体存下来
		# --retry：覆盖临时网络抖动
		if curl -fsSL --retry 3 --retry-delay 2 --max-time 300 -o "${tmp}" "${url}" &&
			[[ "$(sha256_of "${tmp}")" == "${want}" ]]; then
			mkdir -p "${FONT_DIR}"
			mv "${tmp}" "${FONT_DIR}/${file}"
			log "已下载并校验：${file}"
			return 0
		fi
		log "该源不可用或校验不符，换下一个"
	done
	rm -f "${tmp}"
	err "${file}：所有候选源均失败或校验不通过"
	return 1
}

echo "字体目录：${FONT_DIR}"

# ── 1. 逐个检查（缺哪个补哪个）────────────────────────────────────
#
# 用 here-string 而不是管道：管道会把 while 放进子 shell，
# 里面设的变量外面读不到。here-string 在**当前 shell** 执行。
missing=0
while IFS='|' read -r file want urls; do
	[[ -n "${file}" ]] || continue
	if verify_file "${file}" "${want}"; then
		log "✓ ${file}"
		continue
	fi
	if [[ -f "${FONT_DIR}/${file}" ]]; then
		log "✗ ${file} 校验和不符（半截下载 / 被替换过）"
	else
		log "✗ ${file} 缺失"
	fi
	if [[ "${CHECK_ONLY}" == "1" ]]; then
		missing=1
	else
		download_file "${file}" "${want}" "${urls}" || missing=1
	fi
done <<< "${FONTS}"

if [[ "${missing}" == "1" ]]; then
	err "字体未就绪。请运行：scripts/setup_fonts.sh"
	exit 1
fi
echo "字体已就绪$([[ "${CHECK_ONLY}" == "1" ]] && echo "（--check 模式，未下载）")"

# ── 2. 挡住不可再分发的字体 ──────────────────────────────────────
#
# 用 here-string 而不是管道：`set -o pipefail` 下，`grep -q` 一命中就退出，
# 上游 `ls` 收到 SIGPIPE 会以非零退出，整条管道因此判失败——**明明匹配上了却走 else**。
# （这个坑本脚本撞过一次：fc-list 那条断言就是这么"假失败"的。）
FONT_LIST="$(ls "${FONT_DIR}" 2>/dev/null || true)"
if grep -qiE 'songti|stsong|pingfang|hiragino' <<< "${FONT_LIST}"; then
	err "字体目录里出现 Apple 授权字体（Songti / STSong / PingFang / Hiragino）。"
	err "这些字体**不可再分发**，打进镜像会违反授权。请删除后改用 Noto Serif SC。"
	exit 1
fi

# ── 3. 装进系统字体目录（--install）────────────────────────────────
#
# 只把文件放进 runtime/fonts/ 是不够的：fontconfig **只扫系统目录**。
# 容器里靠 compose 挂载生效；没有挂载的环境（CI runner / 裸机）要显式装。
if [[ "${INSTALL}" == "1" ]]; then
	echo "装进系统字体目录：${INSTALL_DIR}"
	# 先试直接写；写不了（比如装到 /usr/share 而当前不是 root）再上 sudo。
	SUDO=""
	if ! mkdir -p "${INSTALL_DIR}" 2>/dev/null; then
		if command -v sudo >/dev/null 2>&1; then
			SUDO="sudo"
			${SUDO} mkdir -p "${INSTALL_DIR}"
		else
			err "无法创建 ${INSTALL_DIR}，且本机没有 sudo。"
			err "换个可写目录：scripts/setup_fonts.sh --install-dir <可写路径>"
			exit 1
		fi
	fi
	while IFS='|' read -r file _want _urls; do
		[[ -n "${file}" ]] || continue
		${SUDO} cp -f "${FONT_DIR}/${file}" "${INSTALL_DIR}/${file}" || {
			err "复制 ${file} 到 ${INSTALL_DIR} 失败"
			exit 1
		}
	done <<< "${FONTS}"
	${SUDO} fc-cache -f "${INSTALL_DIR}" >/dev/null 2>&1 || fc-cache -f >/dev/null 2>&1 || true
	# ⚠ 断言必须**指名到我们的字体**，不能只数 `:lang=zh` 的条数。
	# 只数条数的话，在已经装了别的中文字体的机器上（比如 macOS 自带 100 个 CJK 字体）
	# 即使这次安装完全没生效，也会"通过"——那就成了假绿。
	#
	# 同样用 here-string 而非管道，理由见上面第 2 节（pipefail + grep -q 会假失败）。
	ZH_FONTS="$(fc-list :lang=zh 2>/dev/null || true)"
	if grep -qi 'NotoSerifSC' <<< "${ZH_FONTS}"; then
		log "✓ fontconfig 已识别 NotoSerifSC"
	else
		err "装到 ${INSTALL_DIR} 后，fontconfig 仍找不到 NotoSerifSC"
		err "该目录没被 fontconfig 扫描？用户级用 ~/.local/share/fonts，"
		err "全局级用 /usr/share/fonts/truetype/<任意名>。"
		exit 1
	fi
fi

# ── 3. 容器侧冒烟（发现容器就验；失败即报错，因为那说明挂载没生效）──
if command -v docker >/dev/null 2>&1; then
	container="$(docker ps --format '{{.Names}}' | grep -E 'backend' | head -1 || true)"
	if [[ -n "${container}" ]]; then
		echo "容器侧验证（${container}）…"
		n="$(docker exec "${container}" bash -lc 'fc-list :lang=zh 2>/dev/null | wc -l' 2>/dev/null || echo 0)"
		n="$(printf '%s' "${n}" | tr -d '[:space:]')"
		if [[ "${n:-0}" -gt 0 ]]; then
			log "✓ 容器内中文字体数：${n}"
		else
			err "容器内中文字体数为 0 —— 挂载未生效。"
			err "确认 docker-compose.yml 挂了 ./runtime/fonts:/usr/share/fonts/truetype/hbos:ro，"
			err "且 backend 容器已重建：docker compose up -d backend"
			exit 1
		fi
	else
		log "（未发现运行中的 backend 容器，跳过容器侧验证）"
	fi
fi
