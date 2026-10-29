# 固定 P1 传输回归

`gateway.py` 是 `provenance.json` 中固定基线文件的逐字副本，只供保留的 P1 旧接口断言使用。它位于 tests，不属于 flit 安装包；候选运行时禁止导入它。旧网关调用形式不能作为候选配置或授权后备。

原 `test_policy_gateway.py` 仅调整导入位置，所有断言保留。候选 ticket 边界由 `test_gateway_boundary.py` 和联合候选的 K1C2 207 项重放及原生 HTTP 验证覆盖。这个套件通过不表示旧 P1 已部署候选代码，也不表示旧接口可以接入新服务。
