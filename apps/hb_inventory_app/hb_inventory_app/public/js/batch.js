/* Batch 表单：重新生成货位卡 / 待检证
 *
 * 为什么需要这个按钮：
 *
 * - 自动生成挂在入库单提交的钩子上（见 `hbos_inventory/doc_gen.py`），
 *   但那条路**失败会吞掉异常**——不能因为出不了 PDF 就让人入不了库。
 *   失败后得有地方补。
 * - 卡上的放行状态、流水表等内容会随业务变化（如 QA 补了放行手续），
 *   也需要能重出。
 *
 * 生成的是「待检证 + 货位卡」两页合并的一个 PDF，挂在附件里。
 */

frappe.ui.form.on("Batch", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("重新生成货位卡 / 待检证"), () => {
			frappe.confirm(
				__("将重新生成该批次的「待检证 + 货位卡」并替换上一次生成的那份。继续？"),
				() => {
					frappe.dom.freeze(__("正在生成…"));
					frappe
						.call({
							method: "hb_inventory_app.hbos_inventory.doc_gen.regenerate_for_batch",
							args: { batch_name: frm.doc.name },
							always: () => frappe.dom.unfreeze(),
						})
						.then((r) => {
							if (r && r.message) {
								// 附件变了，刷新表单让新附件出现
								frm.reload_doc();
							}
						});
				}
			);
		});
	},
});
