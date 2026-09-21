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
		// 手工补录的值。渲染会整体重建 DOM，故须在 state 里留一份，
		// 否则重新识别一次就会把操作员填过的东西冲掉。
		extra: {},
		packagingRows: [],
		// 标签原文按行拆开（OCR 返回的 raw_text），每行可编辑
		rawLines: [],
		itemCode: "",
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
						<div class="text-muted small">
							标签照片上要印的信息<b>全部列在下面</b>：识别到的已预填，没读到的留空，
							就地补填即可。带橙框的是需要重点核对的。
						</div>
						<div class="text-muted small mb-1" data-region="item-hint">
							先识别出物料代码，物料级字段会自动带出主数据里已有的值。
						</div>
						<div data-region="fields">
							<div class="text-muted small">
								识别后在此核对；<b>标「须人工填写」的项请照标签直接填</b>。
							</div>
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
	const $itemHint = $(page.body).find('[data-region="item-hint"]');

	// 容器类型选项（与 HBOS Packaging Detail 的 Select 取值一致）
	const CONTAINER_TYPES = ["件", "听", "瓶", "桶", "袋", "箱"];

	// 物料级字段：识别出物料后在主数据里的现状，用于区分「已有」与「为空可补」
	const itemMasterState = {};

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
				state.fileDocName = msg.name; // File docname，用于精确定位附件
				state.result = null;
				state.corrections = {};
				// 换照片 = 换一张标签，上一张的手工补录不能留
				state.extra = {};
				state.packagingRows = [];
				state.rawLines = [];
				$preview.html(
					`<img src="${esc(msg.file_url)}" class="hbos-pi-thumb" alt="标签照片" />`
				);
				$fields.html(
					'<div class="text-muted small">识别后在此核对；<b>标「须人工填写」的项请照标签直接填</b>。</div>'
				);
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
				// 渲染会整体重建校对区，先把操作员已填的值接住
				snapshotManualInputs();
				// 标签原文按行拆。**同一张照片重识别时保留操作员已改过的行**
				// （OCR 对同一张图的结果是确定的，重识别拿回原值只会把改动冲掉）；
				// 换了照片则整批换成新结果——换照片时 state.rawLines 已清空。
				const samePhoto = state.rawLines.length && state.fileUrl === state.rawSourceUrl;
				if (!samePhoto) {
					state.rawLines = String(r.message.raw_text || "").split("\n");
				}
				state.rawSourceUrl = state.fileUrl;
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

	// --- ③ 校对：把标签照片上要印的信息全部列在一处 ---
	//
	// 三组共 11 项 + 包装构成：
	//   A. OCR 识别到的 5 项
	//   B. 物料级 3 项（储存条件 / 生产车间 / 效期类型，从主数据带出，仅补空）
	//   C. 本批 3 项（供货单位 / 生产单位 / 原厂批号，逐批不同）
	// 识别到位的预填、没读到的留空就地填——不再需要「先识别、再翻到另一张卡片补」。
	// 末尾附 OCR **原文**，供逐字对照照片。
	//
	// ⚠ **B / C 两组是「须人工填写」，不是「可补」**（2026-09-21 对着真实标签核实后改的措辞）：
	//   标签上这些字段全是**小字汉字**（`六车间B线车间` / `储存温度不超过30℃`）
	//   或**勾选框**（复检期 □ 有效期 □），实测 OCR 读不准甚至读成别字
	//   （车间读成「过果线」、`操作人/日期` 只读到「作」）。
	//   所以本页**从来没打算**靠识别填它们——界面文案必须让人一眼看出
	//   「这几项得自己看标签填」，而不是让人以为等一会识别就会出来。
	const EXTRA_GROUPS = [
		{
			group: "物料级",
			manual: true,
			note: "标签上是小字，OCR 读不准，须照标签人工填写。填了会写回物料主数据，该物料以后每批都带上；主数据已有值的会锁住，不会被覆盖。",
			items: [
				{
					key: "storage_condition",
					label: "储存条件",
					state: "sd-state",
					ph: "如：储存温度不超过30℃",
				},
				{ key: "workshop", label: "生产车间", state: "ws-state", ph: "如：六车间B线" },
				{
					key: "shelf_life_type",
					label: "效期类型",
					state: "sl-state",
					options: ["复检期", "有效期"],
				},
			],
		},
		{
			group: "本批信息",
			manual: true,
			note: "不在识别字段里，须照标签人工填写。逐批不同，写在对应批次上；主要是外购料的待检证要用。",
			items: [
				{ key: "supplier_name", label: "供货单位", ph: "照标签填写" },
				{ key: "manufacturer", label: "生产单位", ph: "照标签填写" },
				{ key: "supplier_batch_no", label: "原厂批号", ph: "外购标签上的原厂批号" },
			],
		},
	];

	/** 重新渲染前把当前已填的手工值存起来，免得被下一次渲染冲掉。 */
	function snapshotManualInputs() {
		$(page.body)
			.find("[data-extra]")
			.each(function () {
				state.extra[$(this).data("extra")] = $(this).val();
			});
		state.packagingRows = collectPackaging();
		// 标签原文行同理：快照后再重新识别，操作员改过的字不会被 OCR 原值冲掉
		$(page.body)
			.find("input[data-raw]")
			.each(function () {
				const i = Number($(this).data("raw"));
				if (state.rawLines[i] != null) state.rawLines[i] = $(this).val();
			});
	}

	function extraFieldHtml(item) {
		const value = state.extra[item.key] == null ? "" : state.extra[item.key];
		const stateTag = item.state
			? `<span data-role="${item.state}" class="hbos-pi-src"></span>`
			: "";
		const control = item.options
			? `<select data-extra="${esc(item.key)}">
					<option value="">（未设置）</option>
					${item.options
						.map(
							(o) =>
								`<option value="${esc(o)}"${
									String(value) === o ? " selected" : ""
								}>${esc(o)}</option>`
						)
						.join("")}
				</select>`
			: `<input type="text" data-extra="${esc(item.key)}" value="${esc(value)}"
					placeholder="${esc(item.ph || "")}" />`;
		return `
			<div class="hbos-pi-fieldrow">
				<label>
					<span class="hbos-pi-label">${esc(item.label)} ${stateTag}</span>
					${control}
				</label>
			</div>`;
	}

	function renderFields() {
		const res = state.result || {};
		const fields = res.fields || {};
		const hints = res.hints || {};
		const conf = res.confidence || {};
		const raw = res.raw_fields || {};

		// --- A. OCR 识别到的字段 ---
		const ocrRows = Object.keys(FIELD_LABELS)
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

				// 品名**不由本页决定**——待检证与货位卡印的是主数据里的 item_name。
				// 后端已把 `fields.product_name` 换成主数据的值（见 api._enrich_from_master），
				// 所以这里展示的是「将要打印的那个名字」；AI 当初读到的放在 raw_fields 里，
				// 两者并列，读错了正好暴露出来。
				if (key === "product_name") {
					const ocrVal = rawVal == null ? value : rawVal;
					const differs = ocrVal && String(ocrVal) !== String(value);
					return `
						<div class="hbos-pi-fieldrow ${differs ? "needs-review" : ""}">
							<div class="hbos-pi-label">产品名称（主数据为准，不可在此修改）</div>
							<div class="hbos-pi-pair">
								<span>将打印：<b>${esc(value || "（主数据无名称）")}</b></span>
								${
									differs
										? `<span>AI 读作：<code>${esc(ocrVal)}</code> ← 与主数据不符，请核对物料代码</span>`
										: ""
								}
							</div>
							<div class="hbos-pi-note">品名取自物料主数据；若与此处不符，多半是物料代码认错了。</div>
						</div>`;
				}

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

		// --- B / C. 须人工填写的两组（OCR 不读这些，见 EXTRA_GROUPS 上的注释） ---
		const extraRows = EXTRA_GROUPS.map(
			(g) => `
				<div class="hbos-pi-sub">
					${esc(g.group)}${
						g.manual ? ` <span class="hbos-pi-must">须人工填写</span>` : ""
					}
					<span class="hbos-pi-subnote">${esc(g.note)}</span>
				</div>
				${g.items.map(extraFieldHtml).join("")}`
		).join("");

		// --- D. 包装构成 ---
		const pkgHtml = `
			<div class="hbos-pi-sub">
				包装构成 / 件数
				<span class="hbos-pi-pkgsum" data-region="pkg-sum"></span>
			</div>
			<div class="text-muted small mb-1">
				照标签逐条填「容器类型 + 单件重量 + 件数」，件数自动汇总，便于与标签核对。
			</div>
			<div data-region="pkg-rows"></div>
			<button class="btn btn-xs btn-default" data-action="pkg-add">+ 添加一行</button>`;

		// --- E. 标签原文逐行（可编辑） ---
		// OCR 逐字读到的内容，**按行拆成可编辑的行**，操作员对着照片逐行核。
		//
		// 为什么要可编辑而不是只给个只读的原文块：OCR 会读错字（实测把「贮藏：避免硫碰」
		// 读成过品名）。只读展示的话，操作员看得到错但改不了；可编辑才能把错的纠正过来，
		// 校对后的文本会存到批次上（`Batch.hbos_label_text`）——照片是原始凭证，
		// 这段是可检索的转录件：**照片没法搜，文字可以**。
		//
		// 这也避免了本批第 6 条批评过的「假控件」：改了会生效，才配做成输入框。
		const rawLines = state.rawLines;
		const rawHtml = rawLines.length
			? `<div class="hbos-pi-sub">
					标签原文逐行（共 ${rawLines.length} 行，可改）
					<span class="hbos-pi-subnote">校对后的文本随批次留存</span>
				</div>
				<div class="text-muted small mb-1">
					对着照片逐行核；读错的字直接改。这些行不打印，但会存进批次便于日后检索。
				</div>
				<div class="hbos-pi-rawlines">
					${rawLines
						.map(
							(line, i) => `
						<div class="hbos-pi-rawline">
							<span class="hbos-pi-rawidx">${i + 1}</span>
							<input type="text" data-raw="${i}" value="${esc(line)}" />
						</div>`
						)
						.join("")}
				</div>
				<button class="btn btn-xs btn-default" data-action="raw-reset">恢复识别原文</button>`
			: `<div class="hbos-pi-sub">标签原文逐行</div>
				<div class="text-muted small">本次识别没有返回原文（后端可能未提供）。「须人工填写」那几项照照片直接填即可。</div>`;

		const review = res.needs_review
			? `<div class="hbos-pi-alert warn">有字段需要核对（橙框）。请确认无误后再生成草稿。</div>`
			: `<div class="hbos-pi-alert ok">未发现可疑字段。仍建议对照照片与下方原文逐行确认一次。</div>`;

		$fields.html(
			review +
				`<div class="hbos-pi-sub">识别到的字段</div>` +
				ocrRows +
				extraRows +
				pkgHtml +
				rawHtml
		);

		// 恢复上次已填的手工值（重新识别时不该把操作员填过的冲掉）
		$(page.body)
			.find("[data-extra]")
			.each(function () {
				const v = state.extra[$(this).data("extra")];
				if (v != null && v !== "") $(this).val(v);
			});
		renderPackagingRows(state.packagingRows);

		$fields.find("input[data-field]").on("input", function () {
			state.corrections[$(this).data("field")] = $(this).val();
			// 物料代码一变，物料级的补充信息要跟着换物料
			if ($(this).data("field") === "item_code") scheduleItemLookup($(this).val());
		});

		// 标签原文逐行：改动同步回 state（重新识别时也已先快照，不会丢）
		$fields.find("input[data-raw]").on("input", function () {
			state.rawLines[$(this).data("raw")] = $(this).val();
		});

		// 识别后立刻带一次物料级现状（识别出的代码就是初值）
		scheduleItemLookup(fields.item_code);

		$(page.body).find('[data-action="create"]').prop("disabled", false);
	}

	// --- ③-补：物料级补充信息的主数据回显 ---
	//
	// 两个坑（都已处理）：
	//   1. **要绑在 item_code 输入上**，不能像原来那样只在渲染时触发一次——
	//      操作员改正代码后，这里必须跟着换物料；
	//   2. **要防抖 + 丢弃迟到响应**：连着改几次代码会发出多个请求，先发的可能
	//      后到，把上一个物料的值标在当前物料头上。
	let itemLookupTimer = null;
	let itemLookupSeq = 0;

	function scheduleItemLookup(code) {
		clearTimeout(itemLookupTimer);
		itemLookupTimer = setTimeout(() => lookupItemMaster(code), 350);
	}

	function lookupItemMaster(code) {
		code = (code || "").trim();
		const seq = ++itemLookupSeq;
		state.itemCode = code;

		// 状态标记分三种，语气要能区分「不用填」和「必须自己填」：
		//   has   = 主数据已有值，输入框锁住（不用填）
		//   empty = 主数据为空，但**这一项本来就该人来填**（见 EXTRA_GROUPS 注释）
		// 所以 empty 的文案是「须人工填」而非「可补」——它不是备选方案，是必需动作。
		const setState = (role, text, ok) => {
			$(page.body)
				.find(`[data-role="${role}"]`)
				.text(text)
				.attr("class", `hbos-pi-src ${ok ? "has" : "empty"}`);
		};

		if (!code) {
			itemMasterState.current = null;
			["sd-state", "ws-state", "sl-state"].forEach((r) => setState(r, "", false));
			$itemHint.text("先识别出物料代码，这里会自动带出主数据里已有的值。");
			return;
		}

		frappe.db
			.get_value("Item", code, [
				"hbos_storage_condition",
				"hbos_workshop",
				"hbos_shelf_life_type",
			])
			.then((r) => {
				// 迟到的响应：期间代码又变了，丢弃
				if (seq !== itemLookupSeq || state.itemCode !== code) return;
				const m = (r && r.message) || null;
				itemMasterState.current = m;

				if (!m) {
					$itemHint.html(
						`<span class="hbos-pi-src empty">该物料尚未建档</span>，无法带出主数据；请先建档再入库。`
					);
					return;
				}

				const pairs = [
					["sd-state", "storage_condition", "hbos_storage_condition", "储存条件"],
					["ws-state", "workshop", "hbos_workshop", "生产车间"],
					["sl-state", "shelf_life_type", "hbos_shelf_life_type", "效期类型"],
				];
				let emptyCount = 0;
				pairs.forEach(([role, extra, field, label]) => {
					const cur = (m[field] || "").toString().trim();
					const $input = $(page.body).find(`[data-extra="${extra}"]`);
					if (cur) {
						// 主数据已有：填进去并锁住，让操作员知道这项不用管了
						$input.val(cur).prop("disabled", true);
						setState(role, "主数据已有", true);
					} else {
						$input.val("").prop("disabled", false);
						setState(role, "须人工填", false);
						emptyCount++;
					}
				});
				$itemHint.html(
					emptyCount
						? `主数据里有 <b>${emptyCount}</b> 项为空，<b>请照标签填</b>（OCR 读不准这几项小字）。填了会写回主数据，该物料以后每批自动带上；已有值不会被覆盖。`
						: "该物料这三项主数据都已有值，无需重复填写。"
				);
			});
	}

	// --- ④ 包装构成：可增删的重复行 ---
	//
	// 为什么不复用 Frappe 的 grid 控件：那是一整个 DocType 感知的组件，在
	// 自定义 Page 里挂它比直接画几个 input 复杂得多，收益也小。这里是纯前端行编辑。
	const CONTAINER_OPTIONS = CONTAINER_TYPES.map(
		(t) => `<option value="${esc(t)}">${esc(t)}</option>`
	).join("");

	function packagingRowHtml() {
		return `
			<div class="hbos-pi-pkgrow">
				<select data-pkg="container_type">
					<option value="">容器</option>
					${CONTAINER_OPTIONS}
				</select>
				<input type="number" step="0.001" min="0" data-pkg="unit_weight" placeholder="单件重量 kg" />
				<input type="number" step="1" min="0" data-pkg="count" placeholder="件数" />
				<button class="btn btn-xs btn-default" data-action="pkg-del" title="删除本行">×</button>
			</div>`;
	}

	function addPackagingRow() {
		state.packagingRows.push({ container_type: "", unit_weight: "", count: "" });
		renderPackagingRows(state.packagingRows);
	}

	/** 按 state 重画包装构成行。整个 DOM 会被校对区重建，故只能整体重画。 */
	function renderPackagingRows(rows) {
		if (!rows || !rows.length) rows = [];
		const $wrap = $(page.body).find('[data-region="pkg-rows"]');
		$wrap.html(rows.map((r) => packagingRowHtml(r)).join(""));
		// 回填值（packagingRowHtml 只出结构）
		$wrap.find(".hbos-pi-pkgrow").each(function (i) {
			const r = rows[i] || {};
			$(this).find('[data-pkg="container_type"]').val(r.container_type || "");
			$(this).find('[data-pkg="unit_weight"]').val(r.unit_weight === 0 ? "" : r.unit_weight);
			$(this).find('[data-pkg="count"]').val(r.count === 0 ? "" : r.count);
		});
		renderPackagingSummary();
	}

	function collectPackaging() {
		const rows = [];
		$(page.body)
			.find(".hbos-pi-pkgrow")
			.each(function () {
				const container = $(this).find('[data-pkg="container_type"]').val();
				const weight = $(this).find('[data-pkg="unit_weight"]').val();
				const count = $(this).find('[data-pkg="count"]').val();
				if (!container && !weight && !count) return; // 空白行跳过
				rows.push({
					container_type: container,
					unit_weight: weight === "" ? 0 : Number(weight),
					count: count === "" ? 0 : parseInt(count, 10),
				});
			});
		return rows;
	}

	// 与 print_utils.hbos_packaging_count 同一口径：按容器类型汇总，保留首次出现顺序。
	// 放在界面上是为了让操作员能拿它跟标签上的「33件2听1瓶」直接对照。
	function renderPackagingSummary() {
		const totals = {};
		const order = [];
		collectPackaging().forEach((r) => {
			const k = r.container_type || "";
			if (!(k in totals)) {
				totals[k] = 0;
				order.push(k);
			}
			totals[k] += r.count || 0;
		});
		const text = order.map((k) => `${totals[k]}${k}`).join("");
		$(page.body).find('[data-region="pkg-sum"]').text(text ? `合计 ${text}` : "");
	}

	// 包装构成行在校对区里，会被整体重画，故事件一律用**事件委托**绑在 page.body 上
	$(page.body).on("click", '[data-action="pkg-add"]', addPackagingRow);
	$(page.body).on("click", '[data-action="pkg-del"]', function () {
		const idx = $(this).closest(".hbos-pi-pkgrow").index();
		state.packagingRows.splice(idx, 1);
		renderPackagingRows(state.packagingRows);
	});
	$(page.body).on("input change", ".hbos-pi-pkgrow input, .hbos-pi-pkgrow select", function () {
		const idx = $(this).closest(".hbos-pi-pkgrow").index();
		const key = $(this).data("pkg");
		if (state.packagingRows[idx]) state.packagingRows[idx][key] = $(this).val();
		renderPackagingSummary();
	});

	// 手工录入的补充信息也要存进 state，同样的原因
	$(page.body).on("input change", "[data-extra]", function () {
		state.extra[$(this).data("extra")] = $(this).val();
	});

	// 标签原文行在校对区里，会被整体重画，故事件委托绑在 page.body 上
	$(page.body).on("click", '[data-action="raw-reset"]', function () {
		frappe.confirm("把下方所有行恢复成识别结果的原样？你的修改会丢失。", () => {
			state.rawLines = String((state.result || {}).raw_text || "").split("\n");
			renderFields();
		});
	});

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

		// 物料级：主数据里已有的（输入框被禁用、值已回填）不重复提交，
		// 只提交操作员在「为空」字段里填的。后端另有「仅补空」兜底。
		const ext = {};
		$(page.body)
			.find("[data-extra]")
			.each(function () {
				const key = $(this).data("extra");
				const v = ($(this).val() || "").toString().trim();
				ext[key] = v || null;
			});

		frappe.call({
			method: "hb_inventory_app.hbos_inventory.api.create_intake_draft",
			args: {
				item_code: merged.item_code,
				batch_no: merged.batch_no,
				qty: qty,
				warehouse: wh,
				file_url: state.fileUrl,
				file_name: state.fileDocName,
				source_type: $sourceType.val(),
				manufacturing_date: merged.manufacturing_date || null,
				expiry_date: merged.expiry_date || null,
				storage_condition: ext.storage_condition,
				workshop: ext.workshop,
				shelf_life_type: ext.shelf_life_type,
				supplier_name: ext.supplier_name,
				manufacturer: ext.manufacturer,
				supplier_batch_no: ext.supplier_batch_no,
				// 以 state 为准（DOM 是它的渲染产物），避免取值时机不一致
				packaging: JSON.stringify(
					state.packagingRows && state.packagingRows.length
						? state.packagingRows
						: collectPackaging()
				),
				// 逐行校对后的标签原文。空行会被后端丢掉，只留非空行
				label_text: state.rawLines.join("\n"),
			},
			callback(r) {
				$(page.body).find('[data-action="create"]').prop("disabled", false);
				if (!r.message) return;
				const filled = r.message.filled || [];
				const filledHtml = filled.length
					? `<div class="mt-1 text-muted small">本次补进物料主数据：${filled
							.map((f) => `${esc(f.label)} = ${esc(f.value)}`)
							.join("、")}</div>`
					: "";
				$createMsg.html(
					`<div class="hbos-pi-alert ok">
						已生成<b>草稿</b>入库单 <b>${esc(r.message.name)}</b>（未入账）。<br />
						请打开复核，确认无误后<b>自行提交</b>。
						<div class="mt-1 text-muted small">
							提交后系统会<b>自动生成货位卡与待检证</b>（一个 PDF），挂在对应批次的附件里。
						</div>
						${filledHtml}
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
