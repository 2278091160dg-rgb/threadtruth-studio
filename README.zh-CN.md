# ThreadTruth Studio｜服饰保真人像工坊

[English](README.md) | [简体中文](README.zh-CN.md)

**面向 Codex 的源图保真服饰人像生产流程。**

ThreadTruth Studio 是独立维护的社区 Codex Plugin。它从真实服饰图提取可见事实，在 24 个风格包中路由，付费生图前等待明确授权，并以商业 QA 管理六张独立成片。本项目不是 OpenAI 官方产品或背书。

![一件真实白色连帽羽绒马甲的源图与六张独立韩系冷感正式成片](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/hero.jpg)

这是权利清晰的真实“源图 → 六张成片”案例：同一件白色连帽羽绒马甲的 4 张照片，生成 6 张独立韩系冷感杂志风 B1 图片，登记 SHA-256 并完成人工验收。[查看案例](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/README.md) · [媒体权利](docs/demo/RIGHTS.md)

## 安装并测试识别

从 [Releases 页面](https://github.com/2278091160dg-rgb/threadtruth-studio/releases)分别下载 Plugin ZIP 与校验文件。`v1.0.0-beta.1` 保持不可变；beta.2 包已通过静态、打包、checksum、版本与源注册检查。真实新宿主 CLI 激活是另行披露的兼容性缺口，不是补丁发布阻塞项。请按完整的[安装指南](docs/INSTALL.md)操作。

安装后新建一个 **Codex 任务**，先上传服饰图，再原样输入：

```text
请用 $threadtruth-studio 识别并推荐风格，不要生图
```

预期返回服饰识别卡、主推与备选方向、完整 24 风格目录；这句话**不授权生图**。

安装完成后可通过[安装反馈表](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/new?template=installation-feedback.yml)提交脱敏结果；Bug 发到 [GitHub Issues](https://github.com/2278091160dg-rgb/threadtruth-studio/issues)，一般问题使用 [Discussions](https://github.com/2278091160dg-rgb/threadtruth-studio/discussions)。不要公开私有服饰图、客户数据、凭据或完整日志。维护者：[DENGGUI](https://github.com/2278091160dg-rgb) · 微信：`Lvmusic0930`。

## 当前公开证据

- 六张独立正式成片覆盖：`1/24`，即上方真实案例。
- 单风格预览覆盖：已验收 `0/24`。目标是**同一件白色马甲，24 个风格各一张预览；每张只有一种风格、六个姿势**。v2 开发收集器现已按注册风格分别准备绑定源图、运行时规则、风格包和动作 0 提示词的记录；工具本身不生图、不代填验收。图库缩略图展示整张六宫格并链接完整预览，保留“方向预览／非成片”标记。beta.2 混合风格 v1 格式仅供历史只读查看，不能晋级。未真实生成、未人工验收的预览不公开、不计数。
- 性别或文化命名风格只翻译氛围、造型语言、光线与场景，不从服饰或人物推断身份、族裔、国籍、身体或性别。

[查看 24 风格证据索引](docs/demo/STYLES.md)。六格看板只是方向预览，不等于六张独立成片，也不计为完整案例。

## 工作边界

上传服饰始终是颜色、材质观感、廓形、长度、结构、图案、Logo 位置和配饰的事实源。风格只改变视觉处理，不改变商品事实。流程包含真实服饰输入门禁、确定性路由、独立付费授权、串行六图、身份锚、画布检查和证据化 QA。

适用于服饰模特、电商人像和时尚编辑；不适用于非服饰商品、纯文字概念图、通用虚拟试衣、CAD 级合体模拟、API 集成或无人值守商业交付。不保证小字/Logo 完全准确、平台审核通过或销售效果。

运行时无遥测、MCP 服务、外部连接器、API key 流程或联网降级。仅在明确授权后调用宿主原生生图；宿主无该能力时，仍可识别或输出提示词，但生图停在 `tool-blocked`。

## 发布与兼容状态

公开 Beta 从 [`v1.0.0-beta.1`](https://github.com/2278091160dg-rgb/threadtruth-studio/releases/tag/v1.0.0-beta.1) 开始。beta.2 预发行版新增发行包自带的 personal source 安装器；其 mock home 聚焦测试已通过，但尚未验证新宿主 CLI 激活。已审计宿主：macOS `26.6.2`、`codex-cli 0.144.1`；Codex 桌面版 build 不可用，不能从 CLI 版本推断。详见[兼容性](docs/COMPATIBILITY.md)与[30 天 Beta 登记](docs/BETA.md)。

至少 30 天、5 个非维护者安装、3 个授权完整案例，是项目自己的退出目标，不是 OpenAI 固定准入条件。Codex for Open Source 申请细节只放在 [docs/CODEX-FOR-OSS.md](docs/CODEX-FOR-OSS.md)。

## 开发

```bash
python3 -m unittest discover -s tests -v
python3 tools/pack-lint.py --strict skills/threadtruth-studio/references/styles/*.pack.yaml
python3 tools/trigger-eval.py
python3 tools/build-release.py
```

运行时位于 `skills/threadtruth-studio/`；测试、eval、发布工具和证据位于其外。另见[贡献指南](CONTRIBUTING.md)、[安全策略](SECURITY.md)、[离线用户指南](USER-GUIDE.html)、[迁移说明](MIGRATION.md)与[来源记录](PROVENANCE.md)。Apache-2.0 覆盖代码与文档，不覆盖 demo 媒体。
