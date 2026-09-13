# Compatibility / 兼容性

[English](#english) | [简体中文](#简体中文)

## English

| Surface | Evidence | Status |
|---|---|---|
| macOS | `26.6.2` maintainer host | Audited |
| Codex CLI | `codex-cli 0.144.1` | `plugin add`, `list`, `remove`, and marketplace help audited |
| beta.2 installer | Focused tests in an isolated mock home: 6 passing | Source registration behavior verified; real new-host CLI activation pending |
| Codex desktop app | Build unavailable on audited host | Not verified; never inferred from CLI version |
| Clean non-maintainer environment | No retained successful record yet | Pending |
| Official Plugin marketplace | No listing or acceptance evidence | Not available |

For the beta.2 patch release, static tests, package shape/checksum/version checks, and source-registration tests form the release-verification boundary. Actual new-host CLI activation remains explicitly pending and must not be represented as verified compatibility. A successful non-maintainer clean-environment lifecycle is a separate public Beta exit target, not a prerequisite that blocks this patch release. The beta.1 maintainer lifecycle remains historical summary evidence only. See [INSTALL.md](INSTALL.md).

## 简体中文

| 环境 | 证据 | 状态 |
|---|---|---|
| macOS | 维护者宿主 `26.6.2` | 已审计 |
| Codex CLI | `codex-cli 0.144.1` | 已审计 `plugin add`、`list`、`remove` 及 marketplace 帮助 |
| beta.2 安装器 | 隔离 mock home 聚焦测试 6 项通过 | 已验证源注册行为；真实新宿主 CLI 激活待验证 |
| Codex 桌面应用 | 审计宿主无法取得 build | 未验证，不能从 CLI 版本推断 |
| 非维护者干净环境 | 尚无留存的成功记录 | 待验证 |
| 官方 Plugin marketplace | 无上架或获批证据 | 不可用 |

beta.2 补丁发布的验证边界是静态测试、制品结构/checksum/版本检查和源注册测试。真实新宿主 CLI 激活仍明确为待验证，不得宣传为已验证兼容性。非维护者干净环境完整生命周期是另一项公开 Beta 退出目标，不是阻塞本补丁发布的前置条件。beta.1 维护者生命周期仅保留为历史摘要证据。详见 [INSTALL.md](INSTALL.md)。
