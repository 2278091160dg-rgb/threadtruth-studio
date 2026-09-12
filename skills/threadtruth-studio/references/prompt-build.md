# 姿势母版 + 头部视线 + 负面词 + image_gen 调用 + 单张重试(core,风格无关管线)

> **行为等价基线:** 抽取自 `korean-fashion-editorial/references/prompt-build.md`,**护栏逐字保留**;唯一抽象点 = §4.1/§4.2 公式里"韩系底座/场景"→ **pack 变量**;**风格美学负面词下沉到 `pack.negative_delta_add`**(core §3a/§3b 只保留通用安全/反拼图/保真/质量负面词,core 在预览+成片两阶段经 §4.1 商品事实守卫过滤后 append 本组 pack 负面词)。
> **铁律:** 原六姿势、闭集、串行、分阶段负面词与 source-truth 逻辑继续保留;§4.0a 只新增真人组身份锚点与失败止损,§5 只新增商业 QA 阻断,不得借此放宽 B7、安全或服饰保真。

## Contents
- §1 六个姿势母版 / §1a 输出形态覆盖层 / §2 头部视线 / §3 负面词(3a 成片 / 3b 预览 / 露肤追加) / §4 image_gen 规范(4.0 闭集串行计数 / 4.0a 首张身份锚点 / 4.0b 批次画布契约 / 4.1 成片公式 / 4.2 预览公式 / 4.3 预览→成片红线 / 4.4 落盘) / §5 QA / §6 高风险 fallback / §7 单张重试

## 1. 六个原始姿势母版(任何模式·任何风格都继承)

| # | 姿势 | 母版名 |
|---|---|---|
| 1 | 侧身回转站姿 | SIDE_TURN_STANDING |
| 2 | 侧身倚靠墙面 | SIDE_LEANING_WALL |
| 3 | 端正半身坐姿 | UPRIGHT_SEATED |
| 4 | 正面轻步迈步 | FRONT_LIGHT_STEP |
| 5 | 微前倾俯身 | SLIGHT_FORWARD_LEAN |
| 6 | 背身回眸 | BACK_TURN_GLANCE |

不得替换为普通商品站桩 / 普通街拍 / 普通 lookbook / 写真姿势。pack 可经 `pose_masters` 声明风格化增量,但**不得删减这 6 母版**。

## 1a. 输出形态覆盖层(仅 opt-in 或安全降级触发)

默认输出形态 = **真人模特服饰人像**,沿用 §1 六姿势母版与 §2 头部视线。用户未指定输出形态时,不得主动打断追问;在识别卡给一句可改提示即可。

允许的覆盖:
- **不露脸 / 局部 / 切头:** 仍是人像输出,可继承 6 姿势母版;但头部视线改为 `face out of frame, face naturally obscured, cropped below the nose or from neck down when composition allows, no identifiable face, garment remains the focus`。不得复刻源图真人身份。若使用母版 6,`BACK_TURN_GLANCE` 的回眸只保留背身/肩线姿态张力,不得要求露脸或看向镜头。
- **平铺 flat-lay:** 非人像输出;跳过 §1/§2 的真人姿势和头部视线,改为 `clean flat-lay product composition on a low-distraction surface, garment laid naturally, full outline visible, front/back/detail views as requested, no human model, no face`。
- **挂拍 hanger:** 非人像输出;跳过真人姿势和头部视线,改为 `garment hanging on a simple hanger or rail, low-distraction background, full silhouette visible, no human model, no face`。
- **人台 / 假人 / ghost mannequin:** 非真人身份输出;跳过真人头部视线,改为 `ghost mannequin or simple mannequin product presentation, no human model, no realistic face, no hair, garment shape supported clearly, low-distraction studio setting`。

非人像闭集构图编号(动作1逐张成片、动作0六宫格预览都使用同一编号语义):

| # | 平铺 flat-lay | 挂拍 hanger | 人台 / ghost mannequin |
|---|---|---|---|
| 1 | 正面全轮廓平铺,完整展示长度、肩线、下摆 | 正面挂拍全轮廓,衣架/横杆低存在感 | 正面人台全轮廓,服饰结构被清楚撑起 |
| 2 | 背面全轮廓平铺,保留后片结构与后摆 | 背面挂拍全轮廓,保留后片与后摆 | 背面人台全轮廓,保留后片结构 |
| 3 | 领口、肩部、袖口或腰头细节 | 领口、肩部、袖口或腰头细节 | 领口、肩部、袖口或腰头细节 |
| 4 | 面料纹理、纽扣、拉链、logo/图案等可见细节 | 下摆、裤脚、开衩、五金或图案细节 | 面料纹理、纽扣、拉链、logo/图案等可见细节 |
| 5 | 轻微 45° 造型平铺,显示厚度/层次,不扭曲版型 | 侧向 45° 挂拍,显示厚度/垂坠 | 侧向 45° 人台,显示版型体积 |
| 6 | 折叠/搭配展示,只包含参考图里已有鞋包配饰 | 低干扰搭配挂拍,只包含参考图里已有鞋包配饰 | 细节/配饰关系展示,只包含参考图里已有鞋包配饰 |

非人像输出仍遵守一套 outfit 一组、最多 6 张、串行、计数、服饰保真、风险与 tool gates。它只改变"呈现形态",不允许并发、多套混合、API fallback 或放宽安全。非人像输出保留经 §4.1 `STYLE_VISUAL` 商品事实守卫过滤后的 `pack.visual_language` 与 `pack.lighting_palette`,但其中任何人物、真人、portrait、pose、street portrait、editorial model 等语义都必须转译为服饰呈现、商品构图、材质光线或低干扰场景,不得据此拉回真人模特。`pack.model_persona` 中的脸部、表情、姿态、身份词忽略或转译;克制、松弛、高级、低调、冷感等气质词可保留为光线/场景/构图倾向。童装敏感品类的安全降级优先使用平铺/挂拍/人台,并在前台明示。

## 2. 头部方向 / 视线(6 张各不同但服从姿势母版)

| 图 | 头部 / 视线 |
|---|---|
| 1 | 头轻微向侧前方,视线避开镜头,不正面营业 |
| 2 | 头部微垂,视线偏右下或侧下方,冷静疏离 |
| 3 | 头朝窗外或侧前方,避免甜美手托腮 |
| 4 | 头转向斜前侧,避免目录照式正面营业 |
| 5 | 头轻微前倾下压,视线垂落 |
| 6 | 必须回眸,头越过肩线看向镜头方向,但不完全正面化 |

## 3. 负面词(分阶段;**预览阶段和成片阶段不同**)

> ⚠️ 六宫格只在**预览阶段**允许,成片阶段是 6 张独立图。"禁合成页"类负面词**只在成片阶段拼**,预览阶段必须豁免(否则六宫格生不出来)。
> ⚠️ **风格美学负面词(如 no influencer style / no catalog look)= 视觉轴,由 `pack.negative_delta_add` 提供;core 在预览+成片两阶段都把经 §4.1 商品事实守卫过滤后的本组 pack 负面词 append 进去。** core §3a/§3b 只保留**通用项**。

### 3a. 成片阶段通用负面词(动作 1 逐张独立成片,每条 prompt 都拼;通用,风格无关)
```
no collage, no grid, no contact sheet, no multi-panel layout, no split-screen,
no multiple poses in one image, no lookbook composite, no poster, no text layout,
no magazine page layout, no multiple models, no logo invention, no fake text,
no garment redesign, no color change, no length change,
deformed hands, extra fingers.
```
**+ append 经 §4.1 商品事实守卫过滤后的 `pack.negative_delta_add`**(风格美学负面词,如韩系 = no influencer style / no aegyo / no sweet idol smile / no e-commerce catalog look)。

**全身姿势(母版 1/2/4/6)成片时追加**(B4:全身构图必须鞋包下摆完整):
```
cropped shoes, cropped bag, cropped hem.
```
**半身姿势(母版 3/5)不拼这三条** —— 半身构图本就自然截到上半身/膝上,鞋不在画面属正常取景,不算"裁切丢失";但仍禁止**被遮挡丢失**(如包被手臂压没、下摆被家具吃掉)。

**非人像输出不按真人姿势母版 1/2/4/6 分类。** 平铺/挂拍/人台按 §1a 构图编号拼裁切约束:#1/#2/#5/#6 需要全轮廓或搭配关系清楚,可追加 `no cropped garment outline, no cropped hem, no cropped accessories`;#3/#4 是刻意细节图,**不追加** full-body/cropped shoes/bag/hem 或 full-outline 裁切负面词,只要求目标细节(领口、袖口、面料、纽扣、logo 等)清楚完整。

### 3b. 预览阶段负面词(动作 0 出六宫格预览)
预览图本身=「一张图里 6 个姿势」,**严禁拼**任何 `no grid / no collage / no multi-panel / no multiple poses in one image`。预览阶段只拼:
```
no multiple models, no logo invention, no fake text, no garment redesign,
no color change, no length change, deformed hands, extra fingers.
```
**+ append 经 §4.1 商品事实守卫过滤后的 `pack.negative_delta_add`**(风格美学负面词同样在预览阶段拼,与基线一致)。

**露肤 / 吊带 / bra / 短裙额外追加(去性感化,safety-core R4;预览和成片两阶段都拼;通用安全,风格无关):**
```
adult model, tasteful high-fashion editorial, non-sexualized styling, no erotic mood,
no seductive expression, no bedroom context, no lingerie advertisement feeling,
no provocative pose, no upskirt, modest seated posture.
```
> 注:`adult model` 是 R4 安全主体的去性感化锁;**性别年龄轴主体(adult/child·female/male)由 core 注入**(童装走 R1 的 `child model, age-appropriate, modest…`),pack persona 禁声明。

## 4. image_gen 调用规范(服饰保真核心)

本系统 = **保留上传服饰 + 重塑姿势/头部/场景/模特**,本质是**带参考图的生成 / 编辑**,不是纯文生图。

- **默认用宿主提供的原生图片生成能力**,无需 API key,可能消耗订阅额度。入口名称由宿主决定,也可能不在 UI 中逐字显示;**不要因没看到某个固定工具名就判定不可用**。
- **若当前会话确认没有任何可调用原生图片生成能力,立即返回 `tool-blocked`。** 不读取/使用 `OPENAI_API_KEY`,不调 OpenAI Images API,不跑 `openai` CLI / `curl` / 自写联网脚本,也不要求用户开 network 绕过 host 契约。
- **成片阶段每张图独立一次 image_gen 调用**(6 张 = 6 次)。绝不在一次调用里出多图/拼图。
- **必须把用户上传的真实服饰图作为参考图传入**,按 index+role 标注:单图 `Image 1: garment reference, keep the garment exactly as shown`;多图 `Image 1: front view` / `Image 2: back view` / `Image 3: detail/fabric`。
- **不指定具体模型、快照或 API 专属参数。** 使用宿主当前提供的参考图能力;若宿主不支持参考图输入,进入 `tool-blocked`,不得改走 API、CLI 或第三方 fallback。

**多参考图事实优先级(所有成片/重试共用):** `当前已锁定 outfit/SKU 的用户上传服饰参考图 > 识别卡中的可见事实 > 已验收的生成 look-1 身份锚点 > 风格包视觉语言`。生成图永远不是新的服饰事实源;任何生成图与上传服饰图冲突时,以上传图为准。多色/多套输入先按 `recognition.md §3.4/§3.9` 锁定本组 SKU/outfit,不得把未选色或另一套参考图混进本组。

### 4.0 ⛔ B1 闭集 + 串行 + 计数护栏
成片阶段(动作 1)**强制**:
1. **一套 outfit = 一组 = 恰好 6 张闭集。** 一次生成请求只产**一组**。绝不为多套 outfit 同时铺多组(多套逐套串行,见 `recognition.md §3.9`)。
2. **串行执行,严禁并行。** 6 次 image_gen 调用**依次**进行(look-1→…→look-6),前一张落盘确认后再发下一张。**禁止同时开多个 image_gen 调用 / 多会话自调度并发。**
3. **生成后核对计数 = 6。** 全组完成后清点:应 6 张、实际几张、缺哪个 look 编号。少于 6 张不得以"差不多"收尾;但**补齐或 QA 重试也不得突破 B7 单次请求最多 6 次 image_gen 调用**。触顶时保留 `image-draft` + `qa-retry`,报告缺失/失败编号并等待用户明确授权对应的单张重试或“重试 look-1 后继续余下 5 张”,不得自动发第 7 次调用。
4. 测试动作(2)只产 1 张;预览动作(0)只产 1 张六宫格。两者都不触发 6 张闭集。

### 4.0a 真人组首张身份锚点(P1 商业一致性门禁)

动作1的默认真人模特与不露脸/局部真人输出,必须按以下顺序执行;平铺、挂拍、人台/ghost mannequin 跳过本节:

1. **先生成 look-1。** look-1 只接收用户上传服饰参考图,不得拿 preview-grid 当参考图,也不得把源图真人脸当身份复制目标。
2. **先验收再扩展。** look-1 落盘后,先检查上传服饰硬事实、人体结构、成人/儿童安全主体,以及其脸型/发型/表观年龄/身体比例是否足以作为稳定的 AI 模特种子。只有结果为 `qa-pass` 或仅剩不影响身份与硬事实的 `qa-user-review` 时,才能把它标为 `accepted_identity_anchor` 并继续 look-2…look-6。
3. **look-1 不合格就停止传播。** 若 look-1 出现服饰硬事实漂移、明显人体错误、身份种子不可用或安全问题,立即保持部分组为 `image-draft` + `qa-retry`,停止后续 5 张;说明失败点并等待新的明确付费授权。不得为了凑满 6 张自动消耗第 7 次调用,也不得把失败图静默提升为锚点。
4. **look-2…look-6 双参考。** 每张都同时传入当前已锁定 outfit/SKU 的全部上传服饰图 + 已验收 look-1,并在 prompt 逐图标注角色:
   - `Image 1..N = uploaded garment source(s), authoritative source truth for color, material appearance, silhouette, length, collar, shoulder, sleeve, hem, closures, pockets, pattern/logo/text, shoes, bag and accessories.`
   - `Image N+1 = accepted generated look-1, identity anchor only. Preserve the same AI model's face, hair, apparent age and body proportions. Ignore its garment, pose, crop, lighting, background and accessory details whenever they differ from the uploaded garment sources.`
5. **身份锚点不是服饰锚点。** look-1 只锁 AI 生成模特身份;上传服饰图仍是每张图的第一事实源。不得用 look-1 的袖口卷法、纽扣数量、口袋、层叠、首饰、包型、光色或裁切覆盖源图。
6. **不露脸仍不复制源图真人。** 可用 look-1 锁定 AI 模特的发型轮廓、表观年龄和身体比例,但继续执行 face-obscured/cropped 规则,不得因此补出可识别脸。

### 4.0b 批次画布契约(P1 商业比例门禁)

动作1/2在第一次付费调用前,必须按 `modes-scenes.md §4` 解析并锁定一个 `canvas_contract`:

```text
target_ratio: <用户显式比例 > 用途默认比例 > 无用途默认2:3>
target_orientation: portrait | square | landscape
target_pixels: <用户显式像素,否则 unset>
batch_canvas_baseline: <首张通过比例门禁后的实际 WIDTHxHEIGHT>
```

执行顺序:

1. **先锁比例再调用。** 每条独立图 prompt 都逐字注入同一个精确比例和方向,并要求主体/服饰/鞋包下摆位于安全边距内。不能只写“竖版倾向”或依赖姿势词让 host 猜画幅。
2. **提示词不等于通过。** 原生生图 host 可能忽略比例并返回内容自适应尺寸。每张落盘后立即读取实际宽高;优先运行 `python3 scripts/image-spec-check.py --ratio <W:H> [--size <WxH>] <file>`。工具不可用时也必须用当前 host 的只读元数据能力做等价检查,不得目测比例。
3. **首张同时锁批次像素。** 用户显式给像素时,首张必须精确匹配;只给比例时,首张先通过精确比例,其实际 `WIDTHxHEIGHT` 才能成为 `batch_canvas_baseline`。真人/不露脸的 look-1 还必须同时通过 §4.0a,才能作为身份锚点;非人像组的首张只建立画布基线,不建立身份锚点。
4. **后续五张双重检查。** 每张必须同时满足目标比例和 `batch_canvas_baseline` 的精确像素尺寸。可运行 `python3 scripts/image-spec-check.py --ratio <W:H> --same-size <accepted-look-1-or-first.png> <new-look.png>` 做增量校验;整组交付前再对六张一起校验。
5. **失配立即止损。** 比例或批次像素失配属于交付结构失败=`qa-retry`;该图不得成为 identity anchor 或 accepted deliverable。停止后续未调用编号,报告已消耗调用数/失败文件实际尺寸/目标契约,等待用户明确授权单张重试或续生;不得自动突破 B7。
6. **禁止静默修形。** 不得用非等比拉伸、强裁切、加边、preview-grid 放大或无授权 outpaint 掩盖失配。用户明确要求本地后处理时保留原图、版本化保存并重跑服饰/构图/元数据 QA;若需要新原生生图,仍走付费授权门禁。

动作0预览使用独立 grid 画布,只检查其自身为单张 preview-grid;它不继承也不建立动作1的 `batch_canvas_baseline`。

### 4.1 单张成片 prompt 拼装公式(抽象点:底座/场景→pack 变量)

**`STYLE_VISUAL` 商品事实守卫(中心规则,预览/成片/prompts-only 与所有输出形态共用):** 先用识别卡中的真实服饰事实过滤 `pack.visual_language`、`pack.lighting_palette` 与会影响服饰外观的 `pack.model_persona` 语义,再注入 prompt。pack 提到的面料/材质、口袋/绑带/五金、层叠、腰线/衣长、图案/logo、配饰、廓形/剪裁/结构或搭配方式,只有在参考图已明确存在时才可作为服饰描述保留,且只能强调、不得改写。参考图未出现或无法确认时,不得给服装新增这些事实;只把相应风格意图转译为灯光、色调、低干扰背景/道具或构图氛围,且道具不得覆盖服饰。`pack.negative_delta_add` 同样不得删除参考图已有的 logo、图案、材质、结构、配饰或层次;冲突项改写为 `no added/invented ...` 或跳过。该守卫对真人模特、不露脸、平铺、挂拍、人台一视同仁。

**`lighting_palette` 场景自适应光影签名(不新增 schema):** 将这个单一字段按“光源 → 方向 → 阴影特征 → 对比/曝光”顺序解释并转译到当前场景;pack 已写明的分量必须保留,未写明或无法从字段判断的分量保持克制,不得自行补成戏剧光。方向可以随 `pack.scenes` 与输出形态做等价转译,但不得改变光影气质。光线只用于照明、塑形和呈现服饰事实,不得导致服饰改色、换材质、改廓形,不得遮挡 logo/图案/结构或凭空新增层叠与配饰。柔光、低阴影、低对比 pack 必须继续保持柔和,不得为了“光影感”统一升级成硬光或高反差。

`pack.qa_extra` 只能在出图后作为 QA 加项读取,永不注入 prompt;每条 QA 先经同一商品事实守卫。若 QA 项暗示删除、新增或改写参考图中的 logo/图案/材质/结构/配饰/层次,该项必须改写为“无新增/无改写”检查或直接忽略;core source truth 永远优先。

```
[Reference roles: look-1 = uploaded garment source(s) only;
 look-2..6 = uploaded garment source(s) as authoritative garment truth
 + accepted look-1 as identity-only anchor, per §4.0a]
+ [Canvas contract per §4.0b: exact <W:H> <orientation> canvas for every
   independent image; keep the complete required subject/garment/shoes/bag/hem
   inside safe margins; no extra-tall or alternate-ratio canvas]
+ [core 注入的安全主体:按 recognition 性别年龄轴 + safety-core R1/R4
   → adult model(默认)/ child model, age-appropriate, modest(童装)/ + 去性感化锁(露肤时)]
+ [output form: 默认真人模特→用 §1 姿势母版+§2 头部视线;
   不露脸→继承姿势但改 face-obscured/cropped framing;
   平铺/挂拍/人台→改用 §1a 非人像构图,跳过真人头部视线]
+ [STYLE_VISUAL = 经商品事实守卫过滤后的 pack.visual_language + 场景自适应四段光影签名 pack.lighting_palette
   (非人像输出时再把人物/portrait 语义转译为服饰呈现与光线)]
+ [经商品事实守卫过滤后的 pack.model_persona
   (真人模特/不露脸时气质叠加;非人像输出只保留氛围/气质词,忽略或转译表情/脸部/姿态要求)]
+ Pose/composition: [真人模特→姿势母版 #N + 头部视线 #N;
   非人像输出→平铺/挂拍/人台构图 #N,无真人头部视线]
+ Mode/scene: [真人模特/不露脸→棚拍背景 或 pack.scenes #N(对齐 modes-scenes 场景强度);
   平铺/挂拍/人台→棚拍表面/衣架/人台/低干扰商品背景;C/D 模式只把 pack.scenes #N 转译为材质、光线、色调、背景氛围或陈列环境,不得直拼真人地点场景或拉回人像]
+ Garment fidelity: keep the garment from the reference image unchanged —
  keep [颜色/材质/版型/长度/领型/袖型/肩线/下摆/纽扣/图案/logo/鞋/包/配饰 中的实际项],
  do not redesign, do not change color/material/length.
+ single image only, one model/mannequin/garment presentation only, one pose or composition only.
+ Negative: [§3a 通用成片负面词 + 经商品事实守卫过滤后的 pack.negative_delta_add (+ 全身追加 cropped 三条 / + 露肤追加)]
```

### 4.2 六宫格预览 prompt 拼装公式(动作 0,只调一次 image_gen 出 1 张图)
```
[core 安全主体] + [STYLE_VISUAL(先过 §4.1 商品事实守卫;非人像时再转译人物/portrait 语义)] + [经商品事实守卫过滤后的 pack.model_persona(非人像时只保留气质/氛围)]
+ A single 2x3 grid contact-sheet preview showing the SAME one outfit in 6
  different directions.
  - 真人模特/不露脸: show the SAME one model in six pose templates
    (top row poses 1-2-3, bottom row poses 4-5-6), with head/gaze per template
    or face-obscured framing when requested.
  - 平铺/挂拍/人台: show the SAME garment presentation type in six non-portrait
    composition views #1-#6 from §1a, no human model, no head/gaze instruction.
+ This is a LOW-RES DIRECTION PREVIEW, not a final deliverable.
+ Garment fidelity: keep the garment from the reference image unchanged —
  keep [实际服饰项], do not redesign, do not change color/material/length.
+ Add a small, unobtrusive single-line preview label near the bottom-right corner
  or bottom margin, no larger than about 3-4% of image height, low opacity but
  readable, never covering the model, face, garment, shoes, bag, or pose:
  "方向预览·非成片 / PREVIEW ONLY — NOT FINAL".
+ Do not place a large centered watermark across the image.
+ Negative: [§3b 预览负面词 + 经商品事实守卫过滤后的 pack.negative_delta_add (+ 露肤追加)]   ← 注意:不拼 no grid/no collage
```
> 多套不同 outfit 的预览(`recognition.md §3.9`):6 格改为「每格一套 outfit 的代表姿势」,其余规则一致。

### 4.3 ⛔ 预览→成片的红线(逐字保留,风格无关)
1. **`preview-grid` 与 `image-ready` 严格互斥。** 六宫格预览**永远**不能当最终成片,哪怕用户主动说"预览就行/不用再出了"也必须拒绝,固定回复:"预览图为低分辨率方向示意,无法逐张做服饰保真审计,不能当成片。要拿到可用成片,需逐张重新生成 6 张高清独立图(消耗订阅额度)。要我现在开始生成这 6 张吗?"**到此停住等用户明确回答,不自动进成片。** 仅当用户明确说"生成/全部生成/动作1/好/开始"等才进成片;用户改口不生成则停在 `preview-grid` 不调 image_gen。
2. **禁止任何形式的子图提取/裁切/放大/超分。** 对预览图做切割/抠图/放大/超分的请求一律拒绝。成片必须是**重新独立调用 image_gen** 生成的单图。用户说"把预览第3格给我高清版"= 按预览阶段输出形态对应的姿势母版 3 或非人像构图 #3 **重新独立生成**,不是放大预览格。
3. **不接受去标记请求。** 预览标记是生成时画进图里的,**不得**应用户要求 P 掉/遮盖/透明化/局部重绘;遇此请求拒绝并引导进成片。
4. **预览修正至多 3 轮**,但预览永远不具备成片资格;进成片必须经用户**明确**"方向确认/全部生成/动作1"等指令。**"可以了/出图吧/就这个"等模糊词不自行推断为成片授权**——先回确认一句"那我进成片逐张生 6 张高清独立图?"得到肯定再开始。
5. 预览阶段产出状态 = `preview-grid`,绝不标 `image-draft`/`image-ready`。**升 `image-ready` 前二次核验:本组有 look-1…look-6 六个有效独立文件、无 preview-grid 残留、调用数已报告且商业 QA/用户确认已关闭**,否则不得标 ready。

### 4.4 落盘(官方 save-path 策略 + B3 沙箱 fallback,逐字保留)
- 内置模式产物默认在 `$CODEX_HOME/generated_images/...`;要保存时生成后 move/copy 到工作目录,**不只留默认路径**。
- **B3 fallback:** 若沙箱无写入权限,**不要静默失败、也不要重试制造并发**。明确告知:图已生成但落不进工作目录,实际在 `$CODEX_HOME/generated_images/`,并**列出每张缓存绝对路径**让用户自取。绝不因为"看起来没生成"就重跑。
- 不覆盖已有图,版本化命名(`look-1.png` / `look-3-v2.png` / `preview-grid.png`)。

## 5. QA 审计(生成或出提示词前内部自检)

逐张检查:通过输入门禁 / 有真实服饰事实源 / 有明确生成意图 / 单图输出 / 服饰是主角 / 输出形态符合用户或安全默认(真人模特/不露脸/平铺/挂拍/人台) / 真人模特时符合姿势母版 / 非人像时符合 §1a 构图编号且无真人头部视线 / 身体结构清楚(非人像不适用) / 头部方向合理(非人像不适用) / 场景低干扰 / **已读取元数据且符合本组 `canvas_contract` 与 `batch_canvas_baseline`** / 用途构图与留白目标到位 / 颜色材质版型保真 / pack 未新增或删除参考图不存在/已有的材质、结构、图案、层叠、配饰 / 鞋包配饰保留 / 模特身份一致(非人像不适用) / **风格底座到位(对齐所选 pack;非人像时人物/portrait 语义已转译)** / **光源、方向、阴影、对比/曝光与所选 pack 一致,柔光/低阴影 pack 未被戏剧化,光线未改变服饰颜色、材质或结构可见性** / 露肤已非性感化。

**裁切检查按姿势分类(B4):**
- **全身姿势(母版 1/2/4/6):** 鞋、包、下摆必须完整在画面,被裁掉=不合格,重试。
- **半身姿势(母版 3/5):** 构图本就到膝上/腰上,鞋不在画面属正常取景,**不算裁切丢失**;只检查"画面内应有的服饰项是否被遮挡丢失"。
- **非人像构图编号:** #1/#2/#5/#6 检查服饰全轮廓、下摆、结构线、已有鞋包/配饰关系是否完整;#3/#4 是刻意细节裁切,不得按真人全身裁切规则误判,只检查目标细节是否清楚且未被不合理遮挡。

**B8 指标性质:** 下列百分比是 **LLM 自评启发式目标,不是可测量客观指标**,**不得对用户声称"已达成 X% 保真"**:(启发式目标)单图输出正确率 100%;服饰保真 ≥95%;姿势母版保真 ≥92%;头部方向合理 ≥90%;场景适配 ≥90%;风格底座感 ≥90%。

动作1每张落盘后还必须执行 `commercial-qa.md` 的结构化逐张 QA;用户出现“商用/上线/客户交付/电商主图/商品详情/投放/品牌大片”等意图时,必须输出该报告的用户可见版本。任何硬服饰事实或真人身份一致性失败都保持 `image-draft` + `qa-retry`,不得直接升 `image-ready`。

## 6. 高风险 fallback

高风险品类(透明/超短裙/复杂礼服/复杂图案/强民族结构/极端前卫/大logo大文字/多层叠穿):
1. 推荐棚拍版 → 2. 建议先生成 1 张测试 → 3. 测试通过再扩展 6 张 → 4. 用户坚持直接 6 张则用更保守姿势+低干扰背景+更严格遮挡 → 5. 失败只重试单张。泳装/内衣叠 safety-core R4(去性感化 + 被拦不绕过)。

## 7. 单张重试(不重做整组)

用户说"重试第3张""第5张不好""只改图2"时,只重试指定单张。**仅用于成片阶段(`image-draft`)的单张**;预览阶段(`preview-grid`)改方向走 flow-gates 分支4b"第N格调整"。QA 发现失败只报告 `qa-retry`,**未经用户明确单张重试授权不自动调用 image_gen**。

**必须继承:** 当前已锁定 outfit/SKU 的全部用户上传服饰参考图(始终第一事实源) / 原服饰事实档案 / 原模式 / 原场景逻辑 / 原输出形态(真人模特/不露脸/平铺/挂拍/人台) / 已验收 look-1 身份锚点(真人/不露脸适用) / 原姿势编号或非人像构图编号 / 原鞋包配饰关系 / 原用途规格线索 / **原 `canvas_contract` + `batch_canvas_baseline`** / **原风格底座(所选 pack)** / 原负面规则(真人全身 1/2/4/6 拼 cropped 三条,真人半身 3/5 不拼;非人像 #1/#2/#5/#6 查全轮廓/搭配关系,#3/#4 细节图不拼真人 cropped 规则)。

- 重试 look-2…look-6:同时传上传服饰源 + 已验收 look-1;look-1 仍只作身份锚点。
- 重试 look-1:旧 look-1 若脸/发型身份种子可用,可在用户授权后作为 identity-only seed 与上传服饰源共同传入;若身份/人体本身不可用,必须前台说明需要重建锚点,不得静默换人。新 look-1 通过 §4.0a 验收后才替换锚点并继续余图。

只修复指定问题(姿势跑偏 / 头部方向错 / 场景抢戏 / 颜色变了 / logo文字漂移 / 下摆被遮 / 鞋包丢失 / 过甜美 / 过网红 / 变电商目录照)。

重试 prompt patch 模板:
```
Retry only image N. Use every uploaded garment reference as the authoritative fact source.
When a real/faceless model is used, also use the accepted look-1 as identity-only anchor;
never copy garment, pose, crop, lighting, background or accessories from the anchor over the source.
Keep the same outfit colors,
materials, silhouette, shoes, bag, accessories, same generation mode, same pose template
number or same non-portrait composition type, same output form, same [pack 风格底座] mood,
and same model identity when a real model is used.
Keep the exact original canvas contract: <W:H>, <orientation>, and batch pixel
baseline <WIDTHxHEIGHT>; keep all required content inside safe margins.
Fix only this issue: <retryReason>.
Do not redesign the outfit. Do not change the mode. Do not regenerate the whole set.
single image only, one model/mannequin/garment presentation only, one pose or composition only,
no collage, no grid, no text.
[真人模特/不露脸且 N 为全身姿势 1/2/4/6,追加: no cropped shoes, no cropped bag, no cropped hem.]
[平铺/挂拍/人台且 N 为 #1/#2/#5/#6,追加: no cropped garment outline, no cropped hem, no cropped accessories.]
[平铺/挂拍/人台且 N 为 #3/#4,不要追加真人 cropped 或 full-outline 裁切负面词;只写清目标细节必须完整清楚。]
```
