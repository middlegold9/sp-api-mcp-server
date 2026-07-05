# Spec: Amazon SP-API MCP Server

> Spec-Kit 规格说明（做什么 / 为什么）。技术细节见 `plan.md` / `tasks.md`。

## 目标
把亚马逊 **SP-API** 与 **Advertising API** 封装为一组标准 MCP 工具，作为上层跨境电商 Agent（广告复盘、经营日报、Listing 推送、客服助手）的统一数据 / 执行层。一个能力喂饱五个场景，是 FDE「碎石路→高速公路」的地基。

## 用户故事
- **US1 (P0)** — 作为 Agent 开发者，我希望调用 `spapi_orders_list` 拿到订单列表，而不碰 LWA / SigV4 细节。
- **US2 (P0)** — 作为客服后端，我希望调用 `spapi_orders_buyer_info` 时服务端**自动换取并使用 RDT**，安全拿到买家信息。
- **US3 (P1)** — 作为日报 Agent，我希望用 `spapi_fba_inventory` + `spapi_reports_*` 聚合经营数据。
- **US4 (P1)** — 作为 Listing 工具，我希望用 `spapi_feeds_create` 把草稿推到卖家后台并查处理结果。
- **US5 (P1)** — 作为广告 Agent，我希望用 `ads_*` 工具拉报表 / 写调价，且写操作受审批网关控制。
- **US6 (P2)** — 作为运维，我希望用 MCP Inspector 列出全部工具并看到合法 JSON Schema。

## 功能需求
- **FR1** MUST 提供 stdio 传输的 MCP server，暴露带 JSON Schema 的工具。
- **FR2** MUST 管理 LWA `refresh_token` / `access_token` 持久化与自动刷新。
- **FR3** MUST 对返回 PII 的接口（买家信息、地址）自动换取并使用 RDT。
- **FR4** MUST 对广告 API 做独立 OAuth，按 `profileId` 路由市场 / 账号。
- **FR5** MUST 对 429 / quota 做指数退避重试，尊重 `Retry-After`。
- **FR6** MUST 所有写工具（feed / ads 更新）经审批网关：未开启时返回 `{blocked:true, reason}`。
- **FR7** SHOULD 对读结果做缓存（TTL 可配）。
- **FR8** MUST 出参统一包装 `{ok, data, request_id, rate_remaining, cached}`。
- **FR9** MUST 出参 PII 默认脱敏，掩码开关可控。
- **FR10** SHOULD 支持 SSE 传输（可选）。

## 验收清单
- [ ] MCP Inspector 能列出全部工具且 schema 合法、必填入参校验生效。
- [ ] sandbox 下 `spapi_orders_list` 返回数据。
- [ ] `spapi_orders_buyer_info` 自动用 RDT 调用（mock 断言）。
- [ ] 人为触发 429，断言退避后重试成功。
- [ ] 写工具在未开启审批时返回 `blocked`。

## 范围外（Non-goals）
- 调价 / 选品等具体业务策略（上层 Agent 负责）。
- UI / 多租户 SaaS 账号体系（v1 单机单凭证）。
