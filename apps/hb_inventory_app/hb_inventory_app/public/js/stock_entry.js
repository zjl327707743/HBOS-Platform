/* Stock Entry 表单：拍照识别建的入库单，提交后给一个「下一步去哪」的落点
 *
 * ## 为什么需要
 *
 * 拍照识别建的是**原生 Stock Entry 草稿**（刻意如此，让操作员走 ERPNext 的标准
 * 校验）。但提交后就留在原生表单里——面包屑在 Stock 下，标题显示「物料移动」
 * （ERPNext 的 zh 翻译把 Stock Entry 译成了物料移动），等于**跳出了仓库工作台**。
 *
 * 而操作员提交完的下一步动作是**取那张待检证 / 货位卡去贴货位**，
 * 那个 PDF 挂在**批次**的附件上（见 doc_gen.py）。所以落点选「该批次」。
 *
 * ## 为什么是弹框、不是直接跳
 *
 * 仓库是连批作业，一次可能录几十张。每张提交都强制跳走会打断节奏，
 * 所以给两个按钮：去取卡，或继续识别下一张。
 *
 * ## 为什么依据 hbos_intake_batch 而不是 remarks
 *
 * `remarks` 是给人看的中文文案，改一个字判据就失效。专用字段才稳，
 * 而且以后还能用它筛「拍照识别建的入库单」。
 *
 * ## 触发时机
 *
 * 挂在 `on_submit`（表单事件，Frappe 在提交成功后触发，见 form.js 的 savesubmit）。
 * **不能挂 `refresh`**——那样每次打开已提交的单子都会弹一次。
 *
 * ## 另外：这个表单不是死胡同
 *
 * ERPNext 原生库存模块里**没有本 App 的侧边栏**，从拍照识别过来的操作员
 * 落在这里会找不到回去的路。所以给一个「返回仓库工作台」的出口。
 */

frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		// 与 hbos_inventory/workspace_setup.py 的 WORKSPACE_TITLE 必须一致；
		// 改名时两处都要改（tests/test_workspace_contract.py 会红）。
		frm.add_custom_button(__("返回仓库工作台"), () => {
			frappe.set_route("Workspaces", "仓库工作台");
		});
	},

	on_submit(frm) {
		const batch = frm.doc.hbos_intake_batch;

		// 不是拍照识别建的，不打扰（普通入库、移库、领料等都走这里返回）
		if (!batch) return;

		const safe_batch = frappe.utils.escape_html(batch);

		const dialog = new frappe.ui.Dialog({
			title: __("入库已提交"),
			fields: [
				{
					fieldtype: "HTML",
					options: `
						<p>${__("该批次的「待检证 + 货位卡」已生成，挂在批次 <b>{0}</b> 的附件里。", [
							safe_batch,
						])}</p>
						<p class="text-muted small">${__(
							"建议现在打开批次下载打印，贴到货位上。（也可以在「仓库工作台 → 批次」里找到它）"
						)}</p>`,
				},
			],
			primary_action_label: __("打开该批次（取货位卡 / 待检证）"),
			primary_action() {
				dialog.hide();
				frappe.set_route("Form", "Batch", batch);
			},
			secondary_action_label: __("继续识别下一张"),
			secondary_action() {
				dialog.hide();
				frappe.set_route("hbos-photo-intake");
			},
		});

		dialog.show();
	},
});
