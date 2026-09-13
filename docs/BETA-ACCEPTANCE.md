# Beta acceptance packet / Beta 验收资料包

This is an unfilled collection guide, not evidence of a completed test. It does not authorize installing on somebody else's machine, recording, posting, or image generation. / 本页是待填写的验收资料包，不是已完成证据，也不自动授权安装、录屏、发帖或生图。

Use alongside [installation instructions](INSTALL.md), [compatibility](COMPATIBILITY.md), [the Beta register](BETA.md) and [recruitment drafts](BETA-RECRUITMENT.md). The public beta.2 can be tested before the new preview gallery exists.

## 1. One clean external lifecycle / 一次外部干净环境全流程（T14）

The participant must actually be a non-maintainer. A temporary directory on the maintainer's computer proves installer behavior, not this external milestone. Record whether ThreadTruth had previously been installed or enabled on the recipient environment. If it was already present, retain the result but do not label that environment clean.

测试者必须是真实非维护者。记录该环境此前是否安装、注册或启用过 ThreadTruth；已存在时不能声称干净环境。不要为取得“干净”标签删除用户现有配置。

Use two separately extracted, checksum-verified published versions. The current pair is beta.1 → beta.2. The beta.2 installer can accept the separately extracted beta.1 root through `--source`; beta.1 does not need to contain its own copy of that helper. From the beta.2 extraction, select the exact beta.1 directory in the dry-run, inspect it, then explicitly apply. Follow the helper's returned `Next:` command and selector. Do not guess marketplace names or alter unrelated entries.

当前版本对为 beta.1 → beta.2。先分别下载、解压和校验两个正式制品。在 beta.2 解压目录运行安装器，使用 `--source` 指向已经核对的 beta.1 解压根目录，先 dry-run 再确认应用；启用命令使用安装器实际打印的 `Next:`。随后在 beta.2 目录按安装指南的 `--replace` 流程升级，并保留它实际返回的 `source_backup` 供回滚。路径只保留在测试者本机，公开记录不包含主目录路径。

| Step / 步骤 | Required observation / 必须记录 | Initial result / 初始结果 |
|---|---|---|
| Environment / 环境 | Non-maintainer attestation; clean-state description; host/build/OS; date | not-tested |
| Trust / 制品 | Both release links, archive SHA-256, matching sidecar check result | not-tested |
| Initial install / 初装 | beta.1 source registration and actual enablement; installed version | not-tested |
| Discovery / 发现 | A fresh Codex task actually exposes the explicit Skill | not-tested |
| Recognition / 识别 | Authorized garment; recognition card and 24-style catalogue; no generation | not-tested |
| Upgrade / 升级 | beta.1 → beta.2; preserved unrelated configuration; backup exists; new task works | not-tested |
| Remove / 移除 | Remove enabled Plugin state with its exact selector; inspect the resulting state in a fresh task | not-tested |
| Restore / 回滚 | Restore the actual beta.1 source backup through the helper, re-enable and record restored version | not-tested |
| Restored recognition / 回滚复测 | Fresh task, same recognition-only input, expected card/catalogue, no image call | not-tested |
| Retained state / 保留数据 | Source directory, marketplace entry and backups retained as documented; no unrelated data loss | not-tested |

For this milestone, **uninstall means removal of enabled Plugin state**, not complete deletion of every source, marketplace record or backup. Record that scope explicitly; do not claim a full purge. A source still listed as available is different from an enabled Plugin. If the new task still treats it as enabled after removal, record failure and investigate before claiming success. Cleanup of retained source/configuration is a separate, explicitly scoped operation.

本里程碑的“卸载”明确指移除插件启用状态，不是彻底清除源码、marketplace 条目和备份。必须如实列出保留项。若新任务仍把插件视为已启用，不能判通过；额外清理另行确认范围，不执行广泛删除命令。

First-use prompt / 首次及回滚复测指令：

```text
请用 $threadtruth-studio 识别并推荐风格，不要生图
```

Use `pass`, `fail` or `not-tested` for each step, with a brief sanitized observation and date. Failure is useful evidence, not a reason to fabricate success. All required steps need real observations before T14 is complete. Host build unavailable stays unavailable, never inferred from the CLI version.

## 2. Consent and a public-safe receipt / 同意与脱敏记录（T14–T16）

Each participant separately decides:

- Whether to test. / 是否参与测试。
- Whether the sanitized result may count in the public Beta register, under which public handle or pseudonymous ID. / 是否允许以指定公开身份或化名计入台账。
- Whether to be recorded. / 是否允许录屏。
- Whether the reviewed, redacted recording may be published, and where. / 是否允许发布脱敏后的最终录屏及发布渠道。

The [installation Issue form](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/new?template=installation-feedback.yml) is public and uses the GitHub handle. Declining evidence consent does not make an Issue private. Someone who prefers a pseudonym can contact DENGGUI via WeChat `Lvmusic0930`, provide only a sanitized result and chosen public ID, then approve the exact redacted record before it is published. Do not send passwords, account tokens, customer images or full logs through either channel. No installation is counted until actual non-maintainer and publication-counting consent are recorded; repeated versions or reports count as one person.

公开 Issue 不能作为私密入口。偏好化名者可通过微信联系 DENGGUI，仅提供脱敏结果与希望公开的化名；维护者展示拟公开记录，取得明确同意后才登记。不要提交凭据、客户图片或完整日志。是否录屏、是否公开录屏和是否计入安装统计是不同的授权，不能相互替代。

Receipt fields to collect, without prefilling anyone's decision:

| Field / 字段 | Content / 内容 |
|---|---|
| Identity / 身份 | Agreed public handle or pseudonym; non-maintainer declaration; deduplication review |
| Environment / 环境 | Host, actual version/build, OS; clean-environment declaration |
| Versions / 版本 | Old/new archive versions and SHA-256; actual installed/cachebuster versions |
| Results / 结果 | Every lifecycle step above, its observation and date |
| Feedback / 反馈 | Public Issue/Discussion link if consented, otherwise a non-secret local evidence reference |
| Consent / 同意 | Exact scope, decision, date and approved public identity; recording permissions separately |

Keep the full lifecycle receipt separate from the [installation metrics input](BETA.md#opt-in-feedback-and-local-metrics): the counter's install/discovery/recognition fields alone cannot prove upgrade, removal or rollback. Publish only the consented summary, never raw account/configuration output.

## 3. Real recording / 真实录屏（T15）

Record actual UI and commands only after consent. Hide notifications, private tabs, usernames, local paths and account fields. The concise installation demo may show download/checksum, install/enable, a fresh task and recognition-only output. If the recording is also cited as full lifecycle evidence, include upgrade, removal, rollback and restored recognition, or attach the separate observed receipt above; a short cut cannot prove omitted steps.

录制真实操作前先取得同意。若片尾展示已验收的白马甲六张案例，必须标为 **“已有案例展示／非本次录屏生成”**；不可剪成仿佛本次识别操作自动产生六张图片。录屏不授权生图。失败或未获录屏许可不阻塞普通安装测试。

Record capture date, operator's consented identity, actual host/build, what was captured, redaction review, final artifact hash and final publication approval. No recording exists merely because this checklist exists.

## 4. Two new source garments / 另外两件服饰素材（T17）

Target cases: **E-commerce Studio / 电商棚拍** and **American Street / 美式街头**. These are two new full workflows; neither the white-vest previews nor the Met auxiliary case substitutes for them.

For each product, prepare four distinct clear JPEG views for the current developer primary-case validator: front, back, construction/closure detail, and hood/collar/material detail as appropriate. All four must show the same selected product/color, with no mixed SKU. Four views is this evidence tool's current requirement, not the runtime Skill's general minimum input rule. Do not invent a collar/hood if the product lacks one.

每件另需确认：素材拥有者或授权方；公开发布权限；项目媒体政策接受；若有真人展示，其公开展示权；拟用成年模特与模式；可见商品事实及无法确认的细节。无需重新索要已经确认的白马甲源图权利。

Generation remains two separate gates per new case: one test image, then six independent finals after the test is accepted. Plan seven initial native calls per case only if all succeed; targeted retries need new authorization. Final acceptance requires six unique images, consistent canvas, source comparison, human identity/product QA, AI-label acknowledgment and separate public promotion approval.

Developer handoff: use [the primary-case evidence requirements](demo/README.md) and the existing `primary-demo.py validate`, `promote` and `build-media` entrypoints. Maintainers prepare the machine records; contributors must not have to fabricate hashes, generation receipts or human approvals. There is no claim here that a new case or its staging record is already complete.

## 5. Feedback-driven patch / 外部反馈修复版（T18）

Retain the real external report, reporter's non-maintainer status, affected version/environment, reproducible sanitized steps, expected/actual behavior and severity. Link the report to a failing regression, fix commit/PR, verification, changelog and newly published patch. A maintainer-authored issue or already-published beta.2 is not a substitute for an external-feedback-driven release.

## Current status / 当前状态

This packet supplies intake and acceptance instructions only. External lifecycle **0/1**, consented installers **0/5**, new complete cases **0/2**, feedback-driven patch **0/1**, and real recording **not recorded** remain unchanged until real evidence is obtained. Use the [task register](WORK-STATUS.md) for the current schedule and status.
