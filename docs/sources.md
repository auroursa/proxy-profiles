# 资源来源与审核记录

审核日期：2026-10-02。以下日期是此次读取到的文件头／提交信息，不是持续更新状态。
主配置中的规则每日刷新（86400 秒）；主配置自身需要重新导入更新。

## 配置和语法基准

- [crossutility 官方示例](https://github.com/crossutility/Quantumult-X/blob/master/sample.conf)：
  文件标注 v1.5.5 build 914；核对 DoH3、策略、更新间隔、force-policy、内置 FILTER_LAN 和 MITM。
- [墨鱼配置](https://ddgksf2013.top/Profile/QuantumultX.conf)：文件标注 2026-09-10；
  参考服务与节点分层、可选模块、独立兜底；未照搬其全局 UDP／QUIC 丢弃、订阅或重写集合。

## 分流资源

常规服务统一使用 [blackmatrix7 QuantumultX](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/QuantumultX)
原生格式，关闭资源解析器转换。使用 `master` 以跟随规则维护。

| 主配置 tag | 上游文件 | 文件头 UPDATED | 此次规则数 | 决策 |
| --- | --- | --- | --- | --- |
| Apple | [Apple.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Apple/Apple.list) | 2026-10-02 | 1881 | AI／Siri／媒体专用资源在前；其他 Apple 默认直连 |
| Google | [Google.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Google/Google.list) | 2026-05-12 | 711 | 整体绑定 Google；不继承旧资源国内子分类 |
| Microsoft | [Microsoft.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Microsoft/Microsoft.list) | 2025-12-08 | 712 | 整体绑定 Microsoft |
| Telegram | [Telegram.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Telegram/Telegram.list) | 2025-09-10 | 40 | 包含域名与 IP／ASN，通话需 UDP 支持 |
| Twitter | [Twitter.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Twitter/Twitter.list) | 2025-09-28 | 33 | 包含 x.com，替换旧 8 条规则资源 |
| ForeignMedia | [GlobalMedia.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/GlobalMedia/GlobalMedia.list) | 2026-09-28 | 2341 | 固定手动出口；在 Apple／Google 大范围服务前 |
| DomesticMedia | [ChinaMedia.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/ChinaMedia/ChinaMedia.list) | 2025-06-06 | 440 | 国内媒体分类，不继承旧 sve1r 混合拒绝动作 |
| Global | [Proxy.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Proxy/Proxy.list) | 2026-10-02 | 7442 | 约 232KB；不采用约 1.21MB 的 Global.list，未覆盖域名由 Final 接住 |
| China | [China.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/China/China.list) | 2026-06-22 | 3753 | 整体绑定 China；GeoIP CN 同样绑定 China |

局域网使用官方内置 `FILTER_LAN`，在所有服务前强制 direct；本地保留私网 IPv4／IPv6 兜底。
大范围列表中的 IP 规则可能涉及共享 CDN；异常时用前置个人例外修正，并查看实际命中记录。

本仓库维护下列小范围覆盖：

- `apns.txt`：保留原有推送规则，优先于 Apple。
- `apple-intelligence.txt`、`siri.txt`：参考
  [墨鱼 AppleIntelligence.list](https://raw.githubusercontent.com/ddgksf2013/Filter/refs/heads/master/AppleIntelligence.list)
  （文件标注 2026-09-17）及现有配置。上游为 DOMAIN-SUFFIX 格式，不直接作为原生 QX 资源导入。
  拆分 relay 与 Siri／搜索端点；增加 akamaized relay 与 api-siri-prod；
  将 `apps.mzstatic.com` 交回常规 Apple。分类是维护决策，不表示各域名仅服务于 AI。
- `github.txt`：参考
  [GitHub.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/GitHub/GitHub.list)
  （2025-06-12），补齐 assets／usercontent／下载／ghcr／Copilot。
  不引入整个 npm 服务、通用云存储后缀或 host-keyword 匹配。
- `openai.txt`：参考
  [OpenAI.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/OpenAI/OpenAI.list)
  （2025-06-06）与旧规则，保留专用域名与具体 CDN／语音端点。
  不将整个 ASN 或 `stripe.com`、`sentry.io`、`auth0.com` 等共享后缀交给 OpenAI。
  `challenges.cloudflare.com`、`client-api.arkoselabs.com`、`host.livekit.cloud` 和
  `turn.livekit.cloud` 仍可能服务其他产品：这些精确主机也会走 OpenAI，已知影响限定在相应主机。
- `technews.txt`：个人覆盖，绑定 Global 并置于通用规则前。

## 脚本和重写

| 资源 | 固定版本／来源 | 更新策略 |
| --- | --- | --- |
| KOP-XIAO 解析器 | [38a6fe02eb7cc67efd26a8f3c618bd031f1885b4](https://github.com/KOP-XIAO/QuantumultX/commit/38a6fe02eb7cc67efd26a8f3c618bd031f1885b4)，脚本最新提交 2026-09-18 | 固定提交；升级需检查格式兼容和源码差异 |
| GoogleRedirect | 本仓库 `QuantumultX/rewrite-rules.conf` | 默认关闭，精确 hostname、保留路径与查询，随本仓库发布更新 |
| TestFlight 配置 | [8d2249d1e114d09fca4c37a824ba06f5c92c410b](https://github.com/NobyDa/Script/commit/8d2249d1e114d09fca4c37a824ba06f5c92c410b)，该文件最新提交 2021-02-06 | 默认关闭，固定配置；内部 gist 仍动态，启用前重新审核 |
| Qure 图标 | [Koolson/Qure](https://github.com/Koolson/Qure) | 跟随 master，仅展示图标 |

解析器仅在订阅需要转换时启用；本项目不因解析器能识别 URI 就假设客户端支持对应协议。
在线检查确认内容可取和基础格式，不执行外部脚本，也不证明旧 TestFlight 补丁有效。

## 更新方式

1. 常规规则保持每日刷新；出现命中变化时检查上游文件及客户端请求记录。
2. 改动脚本 pin、规则来源、专用域名或顺序时，记录原因并运行本地／在线检查。
3. 重新导入候选配置，在 Wi-Fi 与蜂窝网络完成 README 的验收步骤。
4. 发布后检查本仓库 raw 文件可取且与发布提交一致，再在设备刷新资源。
5. 需要回滚时恢复备份主配置与策略选择；本仓库资源随 master 变化，必要时临时改为旧提交的 raw URL。
