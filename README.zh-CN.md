# ThreadTruth Studio｜服饰保真人像工坊

**面向 Codex 的源图保真服饰人像生产流程。**

ThreadTruth Studio 是独立社区项目，不是 OpenAI 官方产品。它以用户提供的真实服饰图为唯一商品事实源，完成识别、24 风格确定性路由、显式生图授权、六张独立成片与商业 QA。

当前为 `v1.0.0-beta.1` 发布候选：运行时、风格包、回归测试、Plugin 生命周期和首个权利清晰的公开主案例已经就绪；GitHub Release 发布时才开始计算 30 天外部 Beta。最终申请尚未提交。源码仓库为 [2278091160dg-rgb/threadtruth-studio](https://github.com/2278091160dg-rgb/threadtruth-studio)。

![一件真实白色连帽羽绒马甲的源图与六张独立韩系冷感正式成片](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/hero.jpg)

## 已验收案例

首个公开主案例使用同一件白色连帽羽绒马甲的 4 张授权实拍图，按韩系冷感杂志风 B1 生成并验收 6 张独立成片。源图和结果图均登记 SHA-256，人工 QA 已关闭，并明确标识为 AI 生成媒体。

- [查看完整“源图 → 六张成片”案例](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/README.md)
- [查看 24 风格证据索引](docs/demo/STYLES.md)：目前 `1/24` 有公开视觉证据，其余均标为计划项。
- [查看媒体权利记录](docs/demo/RIGHTS.md)

## 核心能力

- 无真实、清晰、可识别的服饰图，不生图。
- 推荐风格不等于同意生图；付费动作必须得到明确授权。
- 24 个版本化风格包按规则路由，冲突时停在 `style-conflict-hold`。
- 六宫格只作方向预览；最终交付必须是六张独立图片。
- 真人组先验收 look-1，再仅以它锁定 AI 模特身份；服饰事实仍以源图为准。
- 每张检查画幅、批次尺寸、服饰硬事实和商业风险。
- 无宿主原生图片生成能力时进入 `tool-blocked`，不读取 API key，不走 CLI、网络或第三方服务降级。

## 不适用范围

本项目不用于非服饰商品、纯文字概念图、通用虚拟试衣、CAD/版型精度模拟、API 集成或无人值守商业交付。它不保证文字/logo 100% 准确、平台审核通过或投放效果。

## 本地验证

```bash
python3 -m unittest discover -s tests -v
python3 tools/pack-lint.py --strict skills/threadtruth-studio/references/styles/*.pack.yaml
python3 tools/trigger-eval.py
python3 tools/build-release.py
```

目前请从包含 `.codex-plugin/plugin.json` 的仓库根目录进行本地 Plugin 测试，不要把内层 Skill 当作独立发行单元。完整操作、状态和回滚说明见 [离线用户指南](USER-GUIDE.html)。

开发层同时管理自有/已授权主案例和 The Met Open Access CC0 辅助案例。机构候选素材先进入被 Git 忽略的本地隔离区，经过元数据、JPEG、哈希、期限和状态机检查后，仍必须由维护者完成人物、Logo、水印、实物服饰和敏感语境核验，才能公开提升。当前已有 1 个主案例和 1 个辅助案例；辅助案例不替代自有主案例，也不计入 Beta 采用数据。Apache-2.0 不覆盖媒体，详见 [媒体政策](docs/demo/MEDIA-POLICY.md)。

公开发布前不会写入姓名、ChatGPT 邮箱、GitHub 用户名或 OpenAI Organization ID。许可证为 [Apache-2.0](LICENSE)。
