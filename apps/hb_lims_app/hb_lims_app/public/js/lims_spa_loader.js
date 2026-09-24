const ASSET_ROOT = "/assets/hb_lims_app/hbos-lims/";

function showBootError(error) {
	console.error("[HBOS LIMS] production bundle bootstrap failed", error);
	const root = document.getElementById("app");
	if (!root) return;
	root.innerHTML = [
		'<div class="hbos-lims-boot">',
		'<div><strong>HBOS LIMS 前端资源未就绪</strong><br>',
		'请联系系统管理员检查 LIMS production bundle。</div>',
		'</div>',
	].join("");
}

async function loadProductionBundle() {
	const manifestResponse = await fetch(`${ASSET_ROOT}.vite/manifest.json`, {
		credentials: "same-origin",
		cache: "no-store",
	});
	if (!manifestResponse.ok) {
		throw new Error(`manifest request failed: HTTP ${manifestResponse.status}`);
	}

	const manifest = await manifestResponse.json();
	const entry = manifest["index.html"]
		|| Object.values(manifest).find((item) => item && item.isEntry);

	if (!entry?.file) {
		throw new Error("Vite manifest does not contain an application entry");
	}

	for (const cssFile of entry.css || []) {
		const href = `${ASSET_ROOT}${cssFile}`;
		if (document.querySelector(`link[data-hbos-lims-css="${href}"]`)) continue;
		const link = document.createElement("link");
		link.rel = "stylesheet";
		link.href = href;
		link.dataset.hbosLimsCss = href;
		document.head.appendChild(link);
	}

	await import(`${ASSET_ROOT}${entry.file}`);
}

loadProductionBundle().catch(showBootError);
