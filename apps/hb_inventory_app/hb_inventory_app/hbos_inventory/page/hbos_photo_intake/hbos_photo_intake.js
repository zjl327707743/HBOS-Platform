/* 入库拍照识别
 *
 * 流程：拍/选照片 → 识别 → 人工校对（低置信度与提示字段高亮）→ 生成草稿入库单
 *
 * 三条不可动摇的规则（M3-R6 方案）：
 *   1. 识别服务不可用时**如实提示**，引导走人工录入，**不伪造结果**；
 *   2. 识别结果**不直接入账**，只生成**草稿**，由操作员复核后自行提交；
 *   3. 任何字段都可**人工改正**，改正后再生成草稿。
 */

frappe.pages["hbos-photo-intake"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "入库拍照识别",
		single_column: true,
	});

	const state = {
		context: null,
		fileUrl: null,
		fileDocName: null,
		result: null,
		corrections: {},
	};

	const esc =
		(frappe.utils && frappe.utils.escape_html) ||
		function (v) {
			return String(v == null ? "" : v)
				.replace(/&/g, "&amp;")
				.replace(/</g, "&lt;")
				.replace(/>/g, "&gt;")
				.replace(/"/g, "&quot;")
				.replace(/'/g, "&#039;");
		};

	const FIELD_LABELS = {
		product_name: "产品名称",
		item_code: "物料代码",
		batch_no: "批号",
		manufacturing_date: "生产日期",
		expiry_date: "有效期至",
	};

	$(page.body).html(`
		<div class="hbos-pi">
			<div class="hbos-pi-head">
				<div>
					<div class="text-muted small">仓储库存工作台 / 入库拍照识别</div>
					<p class="text-muted">
						拍摄产品标签，系统自动识别关键字段；<b>识别结果须人工核对后</b>才生成草稿入库单。
						照片仅在内网处理，不出内网。
					</p>
				</div>
				<button class="btn btn-default" data-route="Workspaces/仓储库存工作台">返回仓储库存工作台</button>
			</div>

			<div class="hbos-pi-status" data-region="status"></div>

			<div class="hbos-pi-grid">
				<div class="hbos-pi-col">
					<div class="hbos-pi-card">
						<h5>① 标签照片</h5>
						<div class="hbos-pi-drop" data-region="drop">
							<input type="file" accept="image/*" data-role="file" hidden />
							<button class="btn btn-primary btn-sm" data-action="choose">选择 / 拍摄照片</button>
							<div class="text-muted small mt-2">支持手机拍照；照片会作为入库原始凭证留存</div>
						</div>
						<div data-region="preview"></div>
					</div>

					<div class="hbos-pi-card">
						<h5>② 识别</h5>
						<label class="hbos-pi-field">
							<span>来源类型</span>
							<select data-role="source_type"></select>
						</label>
						<button class="btn btn-primary btn-sm" data-action="recognize" disabled>开始识别</button>
						<div data-region="recognize-msg" class="mt-2"></div>
					</div>
				</div>

				<div class="hbos-pi-col">
					<div class="hbos-pi-card">
						<h5>③ 人工校对</h5>
						<div data-region="fields">
							<div class="text-muted small">识别后在此核对并修正。</div>
						</div>
					</div>

					<div class="hbos-pi-card">
						<h5>④ 生成草稿入库单</h5>
						<label class="hbos-pi-field">
							<span>货位</span>
							<select data-role="warehouse"></select>
						</label>
						<label class="hbos-pi-field">
							<span>数量（kg）</span>
							<input type="number" step="0.001" min="0" data-role="qty" />
						</label>
						<button class="btn btn-success btn-sm" data-action="create" disabled>
							生成草稿（不直接入账）
						</button>
						<div data-region="create-msg" class="mt-2"></div>
					</div>
				</div>
			</div>
		</div>
	`);

	const $status = $(page.body).find('[data-region="status"]');
	const $preview = $(page.body).find('[data-region="preview"]');
	const $fields = $(page.body).find('[data-region="fields"]');
	const $recognizeMsg = $(page.body).find('[data-region="recognize-msg"]');
	const $createMsg = $(page.body).find('[data-region="create-msg"]');
	const $file = $(page.body).find('[data-role="file"]');
	const $sourceType = $(page.body).find('[data-role="source_type"]');
	const $warehouse = $(page.body).find('[data-role="warehouse"]');
	const $qty = $(page.body).find('[data-role="qty"]');

	// --- 初始化 ---
	frappe.call({
		method: "hb_inventory_app.hbos_inventory.api.get_intake_context",
		callback(r) {
			if (!r.message) return;
			state.context = r.message;
			renderStatus();
			renderOptions();
		},
	});

	function renderStatus() {
		const svc = (state.context && state.context.service) || {};
		if (svc.available) {
			const rows = Object.entries(svc.backends || {})
				.map(
					([k, v]) =>
						`<span class="hbos-pi-tag ${v.available ? "ok" : "off"}">${esc(k)}${
							v.available ? " 可用" : " 未装依赖"
						}</span>`
				)
				.join(" ");
			$status.html(
				`<div class="hbos-pi-alert ok">识别服务已连接（默认后端：${esc(
					svc.default_backend || "-"
				)}）<div class="mt-1">${rows}</div></div>`
			);
		} else {
			// 服务不可用**不是**页面的致命错误——如实提示并给出降级路径
			$status.html(
				`<div class="hbos-pi-alert warn">
					<b>识别服务当前不可用。</b><br />
					${esc(svc.reason || "未启动或不可达")}<br />
					你仍可使用 ERPNext 原生的入库单人工录入（库存 &gt; 库存入库）。
				</div>`
			);
		}
		$(page.body)
			.find('[data-action="recognize"]')
			.prop("disabled", !svc.available || !state.fileUrl);
	}

	function renderOptions() {
		const ctx = state.context || {};
		$sourceType.html(
			(ctx.source_types || []).map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")
		);
		// 货位过多时用 select 会很长，加搜索提示
		$warehouse.html(
			['<option value="">请选择货位</option>']
				.concat(
					(ctx.warehouses || []).map(
						(w) =>
							`<option value="${esc(w.value)}">${esc(w.label)}${
								w.parent ? "（" + esc(w.parent.split(" - ")[0]) + "）" : ""
							}</option>`
					)
				)
				.join("")
		);
	}

	// --- ① 选照片 ---
	$(page.body).on("click", '[data-action="choose"]', () => $file.trigger("click"));

	$file.on("change", function () {
		const f = this.files && this.files[0];
		if (!f) return;
		$preview.html('<div class="text-muted small">上传中…</div>');
		const fd = new FormData();
		fd.append("file", f);
		fd.append("is_private", "1");
		fd.append("folder", "Home");

		fetch("/api/method/upload_file", {
			method: "POST",
			body: fd,
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
		})
			.then((r) => r.json())
			.then((data) => {
				const msg = data.message || {};
				if (!msg.file_url) {
					$preview.html('<div class="hbos-pi-alert warn">照片上传失败。</div>');
					return;
				}
				state.fileUrl = msg.file_url;
				state.fileDocName = msg.name;
				state.result = null;
				state.corrections = {};
				$preview.html(
					`<img src="${esc(msg.file_url)}" class="hbos-pi-thumb" alt="标签照片" />`
				);
				$fields.html('<div class="text-muted small">识别后在此核对并修正。</div>');
				$createMsg.empty();
				renderStatus();
			})
			.catch(() => $preview.html('<div class="hbos-pi-alert warn">照片上传失败。</div>'));
	});

	// --- ② 识别 ---
	$(page.body).on("click", '[data-action="recognize"]', () => {
		if (!state.fileUrl) return;
		$recognizeMsg.html('<div class="text-muted small">识别中，请稍候…</div>');
		$(page.body).find('[data-action="recognize"]').prop("disabled", true);

		frappe.call({
			method: "hb_inventory_app.hbos_inventory.api.recognize_label",
			args: {
				file_url: state.fileUrl,
				source_type: $sourceType.val(),
			},
			callback(r) {
				$(page.body).find('[data-action="recognize"]').prop("disabled", false);
				$recognizeMsg.empty();
				if (!r.message) return;
				state.result = r.message;
				state.corrections = {};
				renderFields();
			},
			error() {
				$(page.body).find('[data-action="recognize"]').prop("disabled", false);
				// frappe.call 已弹出服务端 throw 的消息（含降级建议）
				$recognizeMsg.html(
					'<div class="hbos-pi-alert warn">识别未完成。可重试，或改用人工录入。</div>'
				);
			},
		});
	});

	// --- ③ 校对 ---
	function renderFields() {
		const res = state.result || {};
		const fields = res.fields || {};
		const hints = res.hints || {};
		const conf = res.confidence || {};
		const raw = res.raw_fields || {};

		const rows = Object.keys(FIELD_LABELS)
			.map((key) => {
				const value = fields[key] == null ? "" : fields[key];
				const hintList = hints[key] || [];
				const needs = hintList.length > 0;
				const rawVal = raw[key];
				// 原始值被纠正过才提示"AI 原读作…"，避免噪音
				const showRaw =
					rawVal != null && String(rawVal) !== String(value)
						? `<div class="hbos-pi-raw">AI 原读作：<code>${esc(rawVal)}</code></div>`
						: "";
				const confVal = conf[key];
				const confText =
					confVal != null ? `<span class="hbos-pi-conf">置信度 ${esc(confVal)}</span>` : "";
				const hintHtml = needs
					? `<ul class="hbos-pi-hints">${hintList
							.map((h) => `<li>${esc(h)}</li>`)
							.join("")}</ul>`
					: "";

				return `
					<div class="hbos-pi-fieldrow ${needs ? "needs-review" : ""}">
						<label>
							<span class="hbos-pi-label">${esc(FIELD_LABELS[key])} ${confText}</span>
							<input type="text" data-field="${esc(key)}" value="${esc(value)}" />
						</label>
						${showRaw}
						${hintHtml}
					</div>`;
			})
			.join("");

		const review = res.needs_review
			? `<div class="hbos-pi-alert warn">有字段需要核对（已高亮）。请确认无误后再生成草稿。</div>`
			: `<div class="hbos-pi-alert ok">未发现可疑字段。仍建议对照标签确认一次。</div>`;

		$fields.html(review + rows);

		$fields.find("input[data-field]").on("input", function () {
			state.corrections[$(this).data("field")] = $(this).val();
		});

		// 识别出代码后带出物料名，帮助操作员判断有没有认错
		if (fields.item_code) {
			frappe.db.get_value("Item", fields.item_code, "item_name").then((r) => {
				const name = r && r.message && r.message.item_name;
				$fields.find('[data-field="item_code"]').after(
					`<div class="hbos-pi-raw">主数据中的物料名称：<b>${esc(
						name || "（未建档）"
					)}</b></div>`
				);
			});
		}

		$(page.body).find('[data-action="create"]').prop("disabled", false);
	}

	// --- ④ 生成草稿 ---
	$(page.body).on("click", '[data-action="create"]', () => {
		if (!state.result) return;
		const merged = Object.assign({}, state.result.fields || {}, state.corrections);
		const wh = $warehouse.val();
		const qty = $qty.val();

		if (!wh) {
			frappe.msgprint("请选择货位。");
			return;
		}
		if (!qty || Number(qty) <= 0) {
			frappe.msgprint("请填写数量。");
			return;
		}

		$(page.body).find('[data-action="create"]').prop("disabled", true);
		$createMsg.html('<div class="text-muted small">生成中…</div>');

		frappe.call({
			method: "hb_inventory_app.hbos_inventory.api.create_intake_draft",
			args: {
				item_code: merged.item_code,
				batch_no: merged.batch_no,
				qty: qty,
				warehouse: wh,
				file_url: state.fileUrl,
				source_type: $sourceType.val(),
				manufacturing_date: merged.manufacturing_date || null,
				expiry_date: merged.expiry_date || null,
			},
			callback(r) {
				$(page.body).find('[data-action="create"]').prop("disabled", false);
				if (!r.message) return;
				$createMsg.html(
					`<div class="hbos-pi-alert ok">
						已生成<b>草稿</b>入库单 <b>${esc(r.message.name)}</b>（未入账）。<br />
						请打开复核，确认无误后<b>自行提交</b>。
						<div class="mt-2">
							<a class="btn btn-xs btn-default" href="${esc(r.message.route)}">打开草稿</a>
						</div>
					</div>`
				);
			},
			error() {
				$(page.body).find('[data-action="create"]').prop("disabled", false);
				$createMsg.html('<div class="hbos-pi-alert warn">生成失败，见上方提示。</div>');
			},
		});
	});
};
