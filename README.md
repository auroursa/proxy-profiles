# proxy-profiles

Customized Quantumult X rules and optional rewrites by Frudrax. Inspired by Steven.

配置面向中国大陆网络：国内服务和 APNs 默认直连，海外服务默认走手动代理，
Apple Intelligence、Siri、OpenAI、Anthropic、GitHub 与媒体可以分别选择出口。
2026-10-02 按官方 **v1.5.5 build 914** 示例核对；建议使用该版本或更新版本。
这是一份配置模板，不包含可用节点、订阅凭据或 MITM 证书。

## 导入与升级

1. 先备份当前配置、策略选择和本机证书。更新整个配置可能重置策略选择。
2. 将 [quantumultx.conf](QuantumultX/quantumultx.conf) 导入 Quantumult X。
   发布后的订阅地址为：
   `https://raw.githubusercontent.com/froseiun/proxy-profiles/master/QuantumultX/quantumultx.conf`。
3. 在客户端添加自己的节点订阅。原生 QX 格式关闭资源解析器，Clash／URI 等格式按需开启。
   `[server_remote]` 的示例默认禁用；不要把真实订阅 URL、token 或节点密码提交到仓库。
4. 在 **Manual** 中选择一个可用节点。未选择时使用内置 `proxy`，仍需要在客户端配置代理节点。
5. 更新全部规则资源，确认无下载错误；使用“规则分流”模式，并按下方清单检查实际请求记录。

**本地改造尚未发布时**，主配置中的本仓库 raw URL 仍指向已发布版本，新增文件也可能不存在。
要预览本地改动，先将 `QuantumultX/filter/` 下文件和 `rewrite-rules.conf` 通过文件／iCloud
导入客户端为资源，并将对应远程条目替换成本地资源引用。正式发布后再切回 raw URL 并刷新资源。

## 策略与默认行为

| 策略 | 默认出口 | 用途 |
| --- | --- | --- |
| Manual | 内置 proxy；导入后选择固定节点 | 常用手动出口；自动列出节点 |
| Auto | 延迟优选节点 | 可选；900 秒检查间隔，50ms 容差，空闲不主动测速 |
| Apple、APNs | direct | 常规 Apple 服务、下载与推送 |
| AppleIntelligence | Manual | AI／Private Cloud Compute relay 域名 |
| Siri | Manual | Siri、搜索及相关端点；与 AI relay 分开控制 |
| OpenAI、Anthropic、GitHub | Manual | API、网页、资源、语音／开发服务 |
| Google、Microsoft、Telegram、Twitter | Manual | 各服务整体出口 |
| ForeignMedia | Manual | 固定出口，按需要选择地区合适的节点 |
| DomesticMedia、China | direct | 国内媒体和国内域名／GeoIP CN |
| Global | Manual | 通用海外分流 |
| Final | Global | 未命中请求的兜底；可以独立改为直连或代理 |

`Auto` 是可选项，默认业务出口不自动切换。其节点候选由名称正则 `^.+$` 收集；
导入订阅后确认候选列表，必要时修改正则，排除到期提示／流量说明等条目。
地区组需要根据你的真实节点名称创建，模板不预设可能为空的地区组。
AppleIntelligence、Siri、OpenAI、Anthropic、GitHub 和 ForeignMedia 也会列出节点，可直接选择各自的固定节点，
不必共用 Manual 的选择。例如 OpenAI 选一个节点，ForeignMedia 选另一个地区的节点。
测速成功不等于 AI 或媒体解锁成功，也不等于节点支持 UDP。

本项目明确使用 `force-policy` 将每份远程规则绑定至一个整体出口。
源文件原有动作会被覆盖，包括 `direct`、`reject`；不能用这种方式导入混合广告拒绝与正常访问的列表。
此版国内媒体改用单一服务分类列表，不继续依赖旧混合列表中的拒绝规则。

## 规则优先级

所有分流资源都显式设置 `inserted-resource=true`，位于 `[filter_local]` 的 GeoIP／Final 之前：

```text
LAN
→ APNs → AppleIntelligence → Siri → OpenAI → Anthropic → GitHub → TechNews
→ Telegram → Twitter → ForeignMedia → DomesticMedia
→ Google → Microsoft → Apple
→ Global → China
→ 本地私网 IPv4/IPv6 直连 → GeoIP CN（China）→ Final
```

专用服务先于大范围 Apple、Google 和 Global 列表，避免通用规则抢先命中。
需要个人例外时，在设备上添加独立分流资源，启用“插入资源”，放在 LAN 后、其他服务前。
由于现有资源均插入本地规则之前，仅向 `[filter_local]` 添加域名规则不能保证覆盖它们。
本地检查固定了这份已审核顺序；维护公共规则顺序时同步修改检查器的期望顺序。

## DNS、局域网与 IPv6

- 保留腾讯和两个阿里 DoH 地址；它们并发查询，不是按顺序备用。未做设备实测前不缩减解析器。
- `prefer-doh3` 优先尝试 HTTP/3，失败后回退 HTTP/2。改变 DNS 设置后重连隧道。
- IPv6 默认保留；仅在确认网络或节点 IPv6 异常后启用注释中的 `no-ipv6`。
- `dns_exclusion_list` 是 Fake IP 兼容例外，不是直连名单。目前保留原有认证、游戏、NTP、
  局域网／AD 条目，避免无设备依据的删减；如确认无需游戏或 AD，可逐项删除并重连验证。
- `excluded_routes` 的私网／CGNAT 地址绕过整个隧道，策略无法覆盖。若需要通过代理访问私网，
  应先按实际路由需求修改这些排除项；官方建议修改后重启设备。
- 未设置全局 QUIC／UDP 443 丢弃，避免干扰 DoH3、语音和其他应用。
  语音、Telegram 通话等功能需要节点实际支持 UDP；未配置可用 UDP 回退节点时保持客户端默认行为。

## 可选重写与 MITM

默认关闭两个重写订阅，日常分流无需安装证书：

| 模块 | 功能 | 启用条件 |
| --- | --- | --- |
| GoogleRedirect | `google.cn`／`g.cn` 跳转到 Google，保留路径和查询参数 | 需要该跳转；HTTPS 请求需 MITM |
| TestFlight | 上游旧版安装地区问题补丁 | 仅遇到对应问题时尝试，确认当前 TestFlight 仍兼容 |

Google 跳转限定 `google.cn`、`www.google.cn`、`g.cn`、`www.g.cn`；
不匹配其他子域或 `google.cn.example.com`。例如 `/search?q=qx` 保留为 Google 的搜索请求。

启用 HTTPS 重写前，在设备生成、安装并信任自己的 CA，开启 Rewrite 和 MITM，启用对应资源，
确认资源声明的 hostname 已生效。Google 模块仅声明上面四个域名；TestFlight 模块声明
`testflight.apple.com`。不要向通用 Apple／AI 域名扩大 MITM。
`passphrase` 与 `p12` 留空，`skip_validating_cert=false`；证书私钥始终保留在设备。

解析器和 TestFlight 配置固定至审核过的提交。TestFlight 内部仍引用上游动态 gist 脚本，
并非整个依赖链都被冻结；启用前需重新审查。检查器会访问这条脚本链接，但不执行它。

## 检查与验收

需要 Python 3.12 或更新版本，无第三方依赖：

```sh
python3 scripts/check_profiles.py
python3 -m unittest discover -s tests -v
python3 scripts/check_profiles.py --online
```

静态检查覆盖策略引用／环路／未使用策略、规则类型和重复、本仓库资源、
明确的资源顺序、GeoIP 与唯一末尾 Final、证书与订阅凭据。
在线检查额外下载上游规则、固定解析器、禁用的 TestFlight 配置及其脚本，
拒绝空文件、HTML 错误页和基本格式错误，网络请求最多重试三次。
上游重复规则被容忍，本地重复规则报错。

本仓库 raw URL **从工作区读取**，用于验证尚未发布的候选配置；在线检查不证明这些改动已经发布。
检查器是项目约定检查，不是 QX 的完整语法解析器或网络引擎，不验证内置 `FILTER_LAN` 的展开内容、
策略运行结果、DNS 解析质量或证书信任。GitHub Actions 在 push、PR 和手动触发时运行相同检查。

发布、导入并刷新后，在 **Wi-Fi 和蜂窝网络** 分别验收：

- 私网访问正常，APNs 推送命中 APNs／direct。
- GitHub 网页、图片、raw 文件、Release 下载和 ghcr.io 命中 GitHub。
- `x.com` 命中 Twitter；OpenAI 登录、API、附件和语音分别可用。
- Claude 网页、`api.anthropic.com`、内容资源与 MCP 域名命中 Anthropic，可独立选择固定节点。
- AI relay 命中 AppleIntelligence；Siri 命中 Siri；普通 Apple 下载命中 Apple。
- 国内媒体、国内域名走预期出口；未命中请求使用 Final。
- 改变 Global／China／Final 选择后，对新连接查看请求记录，确认策略实际生效。
- 节点支持 UDP，DNS 无持续超时，局域网与 IPv6 无回退异常。
- 若启用 GoogleRedirect，搜索路径和参数保留；若启用 TestFlight，实际安装成功。

分流只控制网络出口，不保证 Apple Intelligence 的设备／地区资格或媒体解锁。

## 来源

规则来源、审核日期、迁移范围及选用理由见 [docs/sources.md](docs/sources.md)。
本项目 MIT 许可见 [LICENSE](LICENSE)；外部规则、脚本和图标遵循各自上游许可。
