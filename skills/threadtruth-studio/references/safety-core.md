# safety-core.md — 平台政策红线映射(R1–R7)+ 优先级链 + pack 加载二次校验

> **core 横切安全件。风格包(pack)只管视觉轴,绝不触碰本文件任何红线;安全只增不减。**
> **红线来源原则:** 内容红线**以平台政策为准,非自创**。每条标官方出处 + 确认日;不确定项标「待确认」,**禁止凭记忆臆造**。
> **政策快照:** OpenAI Usage Policies 生效日 **2025-10-29**(官方英文页);本表确认日 **2026-09-12**。**政策会更新,到期/发布前须重新核对。**
> **成熟度口径:** 本表 = **政策映射可审计**(G1 PASS)。`未验` 真机项(童装/泳装/moderation/无fallback)随 G5 取证;补齐前**不得对外声称"已通过平台合规验证"**。

## 0. 权威出处(本表唯一依据)

| 代号 | 文档 | URL | 确认日 |
|---|---|---|---|
| S1 | OpenAI Usage Policies(Effective 2025-10-29) | https://openai.com/policies/usage-policies/ | 2026-09-12 |
| S2 | OpenAI Image generation guide(Content Moderation / Limitations / 错误处理) | https://developers.openai.com/api/docs/guides/image-generation | 2026-09-12 |

> S1/S2 已于确认日重新核对。宿主原生图片生成能力是执行入口,不是独立政策来源;核心行为不绑定具体模型名、快照名或 API 参数。

## 1. 平台政策原文要点(逐条引用)

- **S1 · Protect people:** 禁 "sexual violence or non-consensual intimate content";"threats, intimidation, harassment, or defamation"。⚠️ Usage Policies **没有**"成人裸露/性感全面禁止"条款;硬禁的是**性暴力/非自愿亲密内容**;成人露肤是否出图由 S2 moderation 裁决。
- **S1 · Keep minors safe:** "must never be used to **exploit, endanger, or sexualize anyone under 18**";禁 CSAM / grooming / 向未成年人暴露年龄不适(性/暴力/自残)内容。⚠️ 政策**不禁止生成儿童形象本身**(S2 官方示例即儿童绘本);禁的是对未成年人的性化/危害/年龄不适。
- **S1 · Privacy/likeness:** 禁 "use of someone's likeness, including their **photorealistic image** or voice, **without their consent** in ways that **could confuse authenticity**"。
- **S1 · IP:** 含泛化 "infringe on intellectual property rights of others"。⚠️ **无**专门"品牌/logo 禁止"条款 → 品牌/logo 属**本地 IP/法务/保真规则**,非平台硬禁。
- **S2 · Content Moderation:** "All prompts and generated images are filtered…"。`moderation` 参数 `auto`(默认,限制 age-inappropriate)/ `low`(更宽松)。⚠️ `moderation` 是 **Images API 参数**;本 skill 走原生生图,**无法也不应**设置,默认即 `auto`。
- **S2 · 被拦:** `error.code="moderation_blocked"`(带 `moderation_details`)。"Don't automatically retry these errors without modifying the prompt or input images." 示例 `categories` 标签含 `harassment/self-harm/sexual/violence`,但**完整集合未公开** → 规则**不写死枚举**,仅作日志/提示参考。

## 2. 红线映射表(政策 → 可执行规则)

> 字段:〔条款 / 出处 / skill 状态 / 处置话术 / 工程规则 / eval / 真机等级〕。真机等级:`未验`/`逻辑`/`真机`。

### R1 · 未成年人:允许生成,严禁性化/危害/年龄不适
- **条款/出处:** S1 Keep minors safe / 2026-09-12。
- **skill 状态:** 允许出儿童模特(童装/母婴);命中性化/暴露/危险情境 → `gate-blocked`。
- **话术:** 「童装可生成儿童模特,但只做年龄得体、得体着装与姿势、安全日常场景;无法生成任何性化/暴露/危险情境的未成年人内容。」
- **工程规则:** prompt 强制 `child model, age-appropriate, modest clothing, safe everyday setting, non-sexualized`;禁暴露/暧昧/危险场景;**儿童泳装/贴身/睡衣/暴露剪裁 → 默认 flat-lay/挂拍/人台,真人儿童模特需白名单 + 真机证据**。
- **eval:** `kidswear_normal` / `kidswear_sensitive`。**真机等级:** 未验(童装入 MVP = 前置必测,各 1 次)。

### R2 · 真人身份:只取服饰事实,不复刻可识别真人
- **条款/出处:** S1 Privacy/likeness / 2026-09-12。
- **skill 状态:** 真人穿搭图只取服饰,不复刻特定人脸;生成为泛化模特。
- **话术:** 「我只提取这件服饰的事实,不会复刻图中真人的可识别长相。」**真机等级:** 未验。

### R3 · 性暴力/非自愿亲密:绝对禁止
- **条款/出处:** S1 Protect people / 2026-09-12。**skill 状态:** `gate-blocked`,绝不生成。
- **话术:** 「该请求涉及平台明令禁止的内容,无法生成。」**eval:** `prohibited_sexual_content`(负向)。**真机等级:** 未验。

### R4 · 成人泳装/内衣:不写死,去性感化 + 交 moderation 裁决
- **条款/出处:** S1 无成人裸露全面禁令 + S2 moderation / 2026-09-12。
- **skill 状态:** 高风险路由(允许尝试,不保证出图);成人锁定 + 去性感化。
- **话术(被拦时):** 「这张被平台内容审核拦下了(moderation_blocked)。我不会改用 API 或绕过审核;可以换更克制的构图/场景重试,或改出平铺图。」
- **工程规则:** 成人锁定 + 去性感化负面词;**强制非露骨、无性行为/性暗示、无挑逗姿势、无卧室/床/暗光/暧昧、无 upskirt/走光**;短裙坐姿防走光。**禁设 `moderation=low` 或走 API 绕过**。被拦如实报告、**不盲目重试**;仅在**用户确认**后做"更克制改写"再试一次。
- **eval:** `high_risk_clothing` + `swimwear_moderation_blocked`。**真机等级:** 未验(泳装入 MVP = 前置必测;不含则列已知限制)。

### R5 · 品牌/logo:本地 IP/保真规则,非平台硬禁
- **条款/出处:** S1 泛化 IP(无专门 logo 条款)/ 2026-09-12。
- **skill 状态:** 不发明 logo/文字;不能准确渲染时降级为正确位置色块标记,不漂移。
- **工程规则:** prompt 加 `no logos, no trademarks, no invented brand text`;保留原图 logo 位置关系。
- **说明:** **本地 IP/法务/保真规则,非平台硬禁**;用户自有/已授权品牌素材可按保真处理;**skill 不判断商标授权状态,商用合规责任由用户/法务承担**。**真机等级:** 逻辑(基线已覆盖"不编造 logo")。

### R6 · moderation 机制:官方机制 vs 本 skill host 门禁(分栏,勿混淆)
- **6a · 官方机制(来源 S2,可引用):** 原生生图按 content policy 过滤;被拦返回 `moderation_blocked`;官方明示 user-correctable error **不要在不改 prompt/输入下自动重试**;`moderation` 参数仅 Images/Responses API 可设。
- **6b · 本 skill host 门禁(来源=基线 skill 契约,非 S2):** 走原生生图,**无法也不应**设 `moderation`(默认 `auto`);被拦 → **如实告知**,不盲目重试、**不走 API/CLI/curl/`OPENAI_API_KEY` fallback**(继承 `tool-blocked` + B3 纪律:不并发补生、不绕过门禁)。
- **eval:** `moderation_blocked_no_bypass`。**真机等级:** 未验。

### R7 · 通用禁止内容兜底(防服饰任务被包装成违规)
- **条款/出处:** S1 R1–R6 之外的全部禁止项 / 2026-09-12。**skill 状态:** 命中任一即 `gate-blocked`,引导回正常服饰诉求。
- **覆盖清单(S1):** 自杀/自残/饮食失调;骚扰/恐吓/诽谤;恐怖/暴力/仇恨/武器;非法/规避安全/侵犯 IP;隐私/敏感个人信息/生物识别·人脸识别;冒充/诈骗/名人·真人深伪;政治竞选/游说/选举干预;无人工审核的高风险自动决策。
- **工程规则:** 即便上传服饰图,若文字指令把任务导向上述任一(如"做成仇恨海报/政治宣传/某明星深伪穿这件"),拒绝该越界部分,只保留合规服饰人像生成。
- **eval:** `general_prohibited_fallback`(负向)。**真机等级:** 未验。

## 3. 优先级链(硬规则)

**平台政策(R1–R7) > 风险轴 > 品类/性别年龄轴 > 用途轴 > 风格视觉轴。**
下游永远不得放宽上游:风格包/用途诉求("要大片氛围/要性感一点")**不得**突破任何红线。**风格包只管视觉轴;年龄/性别/性化主体一律由 core 注入,pack persona 禁声明。**

## 4. core 加载 pack 时的二次校验契约(强制,来自 g3 §3.5)

`pack.safety_delta.cannot_relax: true` 只是 pack 自声明,linter 只能机械保证"声明存在 + 无放宽 token/键"。**不充分**,故 core 每次加载 pack **必须**再做:
1. **重跑 pack-lint 等价校验**(把 `tools/pack-lint.py --strict` 逻辑内化为加载前置门;FAIL 即拒绝加载该 pack)。
2. **字段白名单分层:** 可进入运行时 prompt/router 的字段只有 `visual_language` / `model_persona` / `scenes` / `lighting_palette` / `pose_masters` / `negative_delta_add` / `safety_delta.extra_constraints` / `default_mode` / `trigger_words` / `suitable_categories` / `anti_categories`;其中 `model_persona` 必须继续经过下一条与 `prompt-build.md §4.1` 的净化。`qa_extra` 仅是 **QA-only** 检查元数据,不得注入正/负面 prompt,且不得覆盖商品事实守卫。`slug/name/version/maturity/extends` 等治理元数据仅供加载校验;除上述运行时、QA 与治理元数据外,**忽略任何未知字段**。
3. **`negative_delta_add` 只允许 append** 到 core 负面词,**core 安全负面词不可被覆盖/删除**;`negative_delta_remove` / `safety_override` 任意形态一律拒绝。
4. **年龄/性化主体一律由 core 按"性别年龄轴"注入**,pack `model_persona` 仅作"气质/表情/状态"叠加,不得声明年龄词/性化词(linter R1#7 强拦 + 本契约二次确认)。
5. **运行时禁 fallback:** pack 内即便写了任何"生成能力退路"措辞(linter 多视图+二要素已拦截一层),core 工具门禁仍以 §SKILL §6 / `tool-blocked` 为准:无原生生图能力即停,**绝不** API/CLI/curl/network/`OPENAI_API_KEY` fallback。

## 5. 已知缺口 / 待确认(诚实标注,禁臆造)

1. 成人泳装/内衣原生生图实际 moderation 阈值 → **必须真机**(含泳装即前置;不含列已知限制)。
2. 儿童模特原生生图是否稳定 → **必须真机**(童装入 MVP 即前置,`kidswear_normal`+`kidswear_sensitive` 各 1 次)。
3. moderation 完整 `categories` 集合未公开 → 规则不写死枚举(不阻断)。
4. 政策时效:S1/S2 均于 2026-09-12 复核;每次公开发布前须重新核对。
5. 所有 `未验` 项补齐前,**不得对外声称"已通过平台合规验证"**;静态/linter 通过 ≠ 行为已验证。
