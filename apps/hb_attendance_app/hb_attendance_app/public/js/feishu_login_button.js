// 飞书登录按钮：在 Frappe 登录页注入「飞书登录」入口。
// 通过 hooks.py 的 web_include_js 注入到所有网站页，仅在 /login 页生效。
(function () {
	function inject() {
		if (document.querySelector(".btn-feishu-login")) return;
		var actions = document.querySelector(".page-card-actions");
		if (!actions) return;

		var btn = document.createElement("a");
		btn.href = "/api/method/hb_attendance_app.feishu_login.redirect";
		btn.className =
			"btn btn-block btn-default btn-sm btn-login-option btn-feishu-login";
		btn.textContent = "飞书登录";
		btn.style.cssText =
			"margin-top:8px;background:#3370ff;color:#fff;border:none;text-decoration:none;";

		actions.appendChild(btn);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", inject);
	} else {
		inject();
	}
})();
