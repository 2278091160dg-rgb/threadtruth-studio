# ThreadTruth Studio｜服饰保真人像工坊

[English](README.md) | [简体中文](README.zh-CN.md)

**面向 Codex 的源图保真服饰人像生产流程。**

ThreadTruth Studio 是独立维护的社区 Codex Plugin。它从真实单件服饰或完整搭配套装图提取可见事实，在 24 个风格包中路由，付费生图前等待明确授权，并以商业 QA 管理六张独立成片。处理套装时，不仅保留每件单品，还锁定可见的层次、穿搭比例及鞋包配饰关系，不重新搭配造型。本项目不是 OpenAI 官方产品或背书。

![同一套米色西装完整搭配的六姿势电商棚拍方向预览](docs/demo/style-previews/beige-blazer-denim-outfit-24-v1/ecommerce-studio-display.jpg)

这是 beta.4 已验收的完整套装方向预览：米色西装、白色上衣、深色牛仔裤、橄榄色托特包和棕色乐福鞋在六个姿势中保持一致。它是一张预览看板，不是六张独立成片。[查看套装全部24种风格](docs/demo/style-previews/beige-blazer-denim-outfit-24-v1/index.html) · [媒体权利](docs/demo/RIGHTS.md)

![一件真实白色连帽羽绒马甲的源图与六张独立韩系冷感正式成片](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/hero.jpg)

白马甲仍是权利清晰的完整“源图 → 六张成片”案例：同一件服饰的4张照片生成6张独立韩系冷感杂志风 B1 图片，登记 SHA-256 并完成人工验收。[查看完整案例](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/README.md)

## 安装并测试识别

从 [`v1.0.0-beta.4` Release](https://github.com/2278091160dg-rgb/threadtruth-studio/releases/tag/v1.0.0-beta.4)分别下载 Plugin ZIP 与校验文件。beta.1–beta.3 保持不可变。真实新宿主 CLI 激活仍是另行披露的兼容性缺口。请按完整的[安装指南](docs/INSTALL.md)操作。

安装后新建一个 **Codex 任务**，先上传服饰图，再原样输入：

```text
请用 $threadtruth-studio 识别并推荐风格，不要生图
```

预期返回服饰识别卡、主推与备选方向、完整 24 风格目录；这句话**不授权生图**。

安装完成后可通过[安装反馈表](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/new?template=installation-feedback.yml)提交脱敏结果；Bug 发到 [GitHub Issues](https://github.com/2278091160dg-rgb/threadtruth-studio/issues)，一般问题使用 [Discussions](https://github.com/2278091160dg-rgb/threadtruth-studio/discussions)。不要公开私有服饰图、客户数据、凭据或完整日志。维护者：[DENGGUI](https://github.com/2278091160dg-rgb) · 微信：`Lvmusic0930`。

## 当前公开证据

- 六张独立正式成片覆盖：`1/24`，即上方真实案例。
- 单风格预览覆盖：**两个集合均为机器版式24/24、维护者验收24/24、beta.4公开24/24**，分别是冻结的白马甲和米色西装完整套装。每个风格均有原生整板优化副本、`1200×1200`展示图和整板缩略图；纠正与失败重试保留哈希证据，但不公开本地工作路径。所有图片均为AI生成方向预览、非独立成片。完整进度见[任务台账](docs/WORK-STATUS.md)。
- 性别或文化命名风格只翻译氛围、造型语言、光线与场景，不从服饰或人物推断身份、族裔、国籍、身体或性别。

[查看 24 风格证据索引](docs/demo/STYLES.md)。六格看板只是方向预览，不等于六张独立成片，也不计为完整案例。

两个边界清晰的演示分别维护：

- **单件服饰 · 24种风格** — 已公开的白马甲 beta.3 集合仍是下方图库与风格索引的唯一代表来源；
- **完整套装 · 24种风格** — 米色西装、白色上衣、深色牛仔裤、橄榄色托特包与棕色乐福鞋的 [beta.4 集合](docs/demo/style-previews/beige-blazer-denim-outfit-24-v1/index.html) 已按 `ThreadTruth-Demo-Only-1.0` 公开并完成24/24验收。

这两个示例只展示受治理的流程，不证明所有服饰或套装均已覆盖，也不计为非维护者采用或新增完整主案例。

在 ChatGPT 中可用 Plugin 选择器或 `@threadtruth-studio`；受支持的 Codex 界面可用 skill 选择器或 `$threadtruth-studio`，Codex CLI 可查看 `/skills`。本项目不声称已获官方 marketplace 上架。

<!-- STYLE_PREVIEWS:START -->

| | | | |
|---|---|---|---|
| <a href="docs/demo/style-previews/white-vest-24-v1/american-street-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/american-street-thumb.jpg" alt="American Street — six-pose layout preview, not finals" width="180"></a><br>American Street | <a href="docs/demo/style-previews/white-vest-24-v1/athleisure-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/athleisure-thumb.jpg" alt="Athleisure — six-pose layout preview, not finals" width="180"></a><br>Athleisure | <a href="docs/demo/style-previews/white-vest-24-v1/balletcore-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/balletcore-thumb.jpg" alt="Balletcore — six-pose layout preview, not finals" width="180"></a><br>Balletcore | <a href="docs/demo/style-previews/white-vest-24-v1/british-heritage-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/british-heritage-thumb.jpg" alt="British Heritage — six-pose layout preview, not finals" width="180"></a><br>British Heritage |
| <a href="docs/demo/style-previews/white-vest-24-v1/cityboy-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/cityboy-thumb.jpg" alt="Cityboy — six-pose layout preview, not finals" width="180"></a><br>Cityboy | <a href="docs/demo/style-previews/white-vest-24-v1/clean-fit-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/clean-fit-thumb.jpg" alt="Clean Fit — six-pose layout preview, not finals" width="180"></a><br>Clean Fit | <a href="docs/demo/style-previews/white-vest-24-v1/coquette-ladylike-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/coquette-ladylike-thumb.jpg" alt="Coquette Ladylike — six-pose layout preview, not finals" width="180"></a><br>Coquette Ladylike | <a href="docs/demo/style-previews/white-vest-24-v1/ecommerce-studio-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/ecommerce-studio-thumb.jpg" alt="E-commerce Studio — six-pose layout preview, not finals" width="180"></a><br>E-commerce Studio |
| <a href="docs/demo/style-previews/white-vest-24-v1/french-effortless-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/french-effortless-thumb.jpg" alt="French Effortless — six-pose layout preview, not finals" width="180"></a><br>French Effortless | <a href="docs/demo/style-previews/white-vest-24-v1/gorpcore-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/gorpcore-thumb.jpg" alt="Gorpcore — six-pose layout preview, not finals" width="180"></a><br>Gorpcore | <a href="docs/demo/style-previews/white-vest-24-v1/guochao-street-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/guochao-street-thumb.jpg" alt="Guochao Street — six-pose layout preview, not finals" width="180"></a><br>Guochao Street | <a href="docs/demo/style-previews/white-vest-24-v1/italian-luxe-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/italian-luxe-thumb.jpg" alt="Italian Luxe — six-pose layout preview, not finals" width="180"></a><br>Italian Luxe |
| <a href="docs/demo/style-previews/white-vest-24-v1/japanese-lifestyle-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/japanese-lifestyle-thumb.jpg" alt="Japanese Lifestyle — six-pose layout preview, not finals" width="180"></a><br>Japanese Lifestyle | <a href="docs/demo/style-previews/white-vest-24-v1/korean-cold-editorial-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/korean-cold-editorial-thumb.jpg" alt="Korean Cold Editorial — six-pose layout preview, not finals" width="180"></a><br>Korean Cold Editorial | <a href="docs/demo/style-previews/white-vest-24-v1/korean-menswear-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/korean-menswear-thumb.jpg" alt="Korean Menswear — six-pose layout preview, not finals" width="180"></a><br>Korean Menswear | <a href="docs/demo/style-previews/white-vest-24-v1/neo-chinese-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/neo-chinese-thumb.jpg" alt="Neo Chinese — six-pose layout preview, not finals" width="180"></a><br>Neo Chinese |
| <a href="docs/demo/style-previews/white-vest-24-v1/nordic-minimal-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/nordic-minimal-thumb.jpg" alt="Nordic Minimal — six-pose layout preview, not finals" width="180"></a><br>Nordic Minimal | <a href="docs/demo/style-previews/white-vest-24-v1/office-commute-women-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/office-commute-women-thumb.jpg" alt="Office Commute Women — six-pose layout preview, not finals" width="180"></a><br>Office Commute Women | <a href="docs/demo/style-previews/white-vest-24-v1/old-money-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/old-money-thumb.jpg" alt="Old Money — six-pose layout preview, not finals" width="180"></a><br>Old Money | <a href="docs/demo/style-previews/white-vest-24-v1/preppy-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/preppy-thumb.jpg" alt="Preppy — six-pose layout preview, not finals" width="180"></a><br>Preppy |
| <a href="docs/demo/style-previews/white-vest-24-v1/quiet-luxury-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/quiet-luxury-thumb.jpg" alt="Quiet Luxury — six-pose layout preview, not finals" width="180"></a><br>Quiet Luxury | <a href="docs/demo/style-previews/white-vest-24-v1/resort-vacation-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/resort-vacation-thumb.jpg" alt="Resort Vacation — six-pose layout preview, not finals" width="180"></a><br>Resort Vacation | <a href="docs/demo/style-previews/white-vest-24-v1/workwear-vintage-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/workwear-vintage-thumb.jpg" alt="Workwear Vintage — six-pose layout preview, not finals" width="180"></a><br>Workwear Vintage | <a href="docs/demo/style-previews/white-vest-24-v1/y2k-millennium-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/y2k-millennium-thumb.jpg" alt="Y2K Millennium — six-pose layout preview, not finals" width="180"></a><br>Y2K Millennium |

<!-- STYLE_PREVIEWS:END -->

## 工作边界

上传的单件服饰或已锁定完整套装始终是颜色、材质观感、廓形、长度、结构、图案、Logo 位置和配饰的事实源。完整套装还必须保留每件单品、穿搭层次、比例以及可见鞋包配饰关系。风格只改变视觉处理，不改变商品事实或重新搭配造型。流程包含真实服饰输入门禁、确定性路由、独立付费授权、串行六图、身份锚、画布检查和证据化 QA。

适用于服饰模特、电商人像和时尚编辑；不适用于非服饰商品、纯文字概念图、通用虚拟试衣、CAD 级合体模拟、API 集成或无人值守商业交付。不保证小字/Logo 完全准确、平台审核通过或销售效果。

运行时无遥测、MCP 服务、外部连接器、API key 流程或联网降级。仅在明确授权后调用宿主原生生图；宿主无该能力时，仍可识别或输出提示词，但生图停在 `tool-blocked`。

## 发布与兼容状态

公开 Beta 从 [`v1.0.0-beta.1`](https://github.com/2278091160dg-rgb/threadtruth-studio/releases/tag/v1.0.0-beta.1) 开始。[`v1.0.0-beta.4`](https://github.com/2278091160dg-rgb/threadtruth-studio/releases/tag/v1.0.0-beta.4) 是最新公开下载，增加已验收的完整套装24风格图库，不改变运行时行为。已审计宿主：macOS `26.6.2`、`codex-cli 0.144.1`；Codex 桌面版 build 不可用，不能从 CLI 版本推断。详见[兼容性](docs/COMPATIBILITY.md)与[30 天 Beta 登记](docs/BETA.md)。

至少 30 天、5 个非维护者安装、3 个授权完整案例，是项目自己的退出目标，不是 OpenAI 固定准入条件。Codex for Open Source 申请细节只放在 [docs/CODEX-FOR-OSS.md](docs/CODEX-FOR-OSS.md)。

## 开发

```bash
python3 -m unittest discover -s tests -v
python3 tools/pack-lint.py --strict skills/threadtruth-studio/references/styles/*.pack.yaml
python3 tools/trigger-eval.py
python3 tools/build-release.py
```

运行时位于 `skills/threadtruth-studio/`；测试、eval、发布工具和证据位于其外。另见[贡献指南](CONTRIBUTING.md)、[安全策略](SECURITY.md)、[离线用户指南](USER-GUIDE.html)、[迁移说明](MIGRATION.md)与[来源记录](PROVENANCE.md)。Apache-2.0 覆盖代码与文档，不覆盖 demo 媒体。
