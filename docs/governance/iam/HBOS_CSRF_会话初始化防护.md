# 已认证会话的 CSRF 初始化保护

Frappe 16 的请求初始化会在 Session 尚无已保存 CSRF token 时跳过原生 token 校验。HBOS Portal 在 `before_request` 中阻止这种已认证会话执行 POST、PUT、PATCH 和 DELETE。客户端可通过现有的 `hbos_portal.auth.accounts.get_request_security` 获取并初始化 token，然后重试合法写入。已初始化的会话继续由 Frappe 原有 CSRF 校验处理。

Frappe 原生登录会在请求初始化期间先创建新 Session。Portal 的 `before_login` 因而在创建新 Session 前核对已有 Cookie 会话的 token；首次登录无已认证 Cookie 时允许原生认证流程继续。此前 Session 的数据库记录必须仍为 Active 且符合有效期，token 使用常量时间比较。HBOS 的账号密码登录在访客请求中经过既有的同源和 JSON 校验。

保护随 `hbos_portal` 应用代码及其 hooks 一起交付。部署后须确认目标 Site 已安装该应用，按既有发布流程清理该 Site 的 hooks 缓存并重启承载 Frappe 的进程。未安装或未加载 Portal hooks 的 Site 需要独立的框架级防护。鉴权网关和反向代理应维护可信的 Host、Origin 与 Cookie 边界。安全审查应覆盖其它已安装应用中先于 Portal 执行的请求钩子及非 Cookie 认证客户端。

运行 Portal 后端合同测试：

```sh
PYTHONPATH=apps/hbos_portal python -m unittest discover -s apps/hbos_portal/tests -t apps/hbos_portal -q
```

真实 Site 验收应包括新 Session 在 token 初始化前的跨来源写入拒绝和数据库前后值核对、初始化 token 后的合法写入、原生和 HBOS 登录、有效 token 的原生再次登录、跨来源原生登录拒绝、退出及撤权。独立浏览器跨站表单需同时记录 Cookie 是否由浏览器发送和服务端的响应。
