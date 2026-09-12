# style-router.md — 风格路由(推荐 + 确认 + 冲突检测 + 可审计 trace)

> **职责(L2 内部 router):** core 已加载后,据"识别事实 + 用户措辞"选风格包,输出**可审计 trace**;**只推荐不生图、不自动选定**。选定风格代号后仍须 §SKILL §6 动作授权才进生图。
> **铁律:** 路由结果**不得绕过** `safety-core.md`(R1–R7)与输入门禁;`score` 只能查权重表累加,模型不得自由填分。

## 1. 路由输入
- **识别卡事实:** 品类 / 主色 / 材质 / 版型 / 露肤 / **性别年龄信号** / 用途·平台线索 / 是否高风险品类。
- **用户措辞:** 显式风格名(如"法式")、平台("发小红书")、用途("品牌大片/电商主图")。
- **默认:** 用户**未指定风格** → 走 §6 推荐算法(主+2备)+§6.1 完整注册包选择面板,**不自动选定、不生图**,停 `recognition-ready`。

## 2. 路由优先级(硬序,防"无脑默认韩系" + 防"冲突风格被直路由抢先")

**第 0 步在直路由之前执行**(否则"显式风格名→直路由"会挡不住"两个风格名都可识别但互斥")。

0. **显式风格确定性匹配与冲突检测(最先执行):** 从用户措辞抽取 pack `trigger_words` 命中,按以下固定顺序收口。不得依赖 pack 加载顺序或模型自由判断。
   1. **规范化 + 词边界:** 对 query 与 trigger 做 Unicode NFKC、大小写折叠;trigger **自身内部**已声明的空白、连字符与下划线可视为等价或缺省,但 ASCII trigger 首尾必须保留 ASCII 词边界。因此 `resort` 不得从 `presort`/`re-sort` 中取子串,`W Korea` 不得从 `show Korea`/`new Korea` 跨词拼出;trace 仍保留原始 query/trigger,不得伪造用户措辞。
   2. **同包别名折叠:** 同一 slug 下规范化后相等的拼写别名(如 `old money`/`old-money`)只记 1 次 `STYLE_EXPLICIT` hit。
   3. **同一命中位置的最长完整触发词优先:** 只有短 trigger 在 query 中的命中区间被另一条更长 trigger 的命中区间**完整覆盖**时,才淘汰该短命中。例:`美式学院` 只归 `preppy`,不再同时命中 `american-street` 的裸`美式`;`性冷淡极简`只归 `nordic-minimal`,不再同时命中 korean 的`性冷淡`。如果用户在另一个位置又独立写出短词(如`美式和美式学院融合`),该独立命中必须保留,最终按多 slug 规则 hold。
   4. **按最终 slug 数决策:** 0 个 slug→进入第 3/4 步;1 个 slug→进入第 1 步;≥2 个不同 slug→无论 §3 判为互斥还是视觉上可兼容,均**不静默混合、不臆选主风格**,停 `style-conflict-hold`(`fallback_used=conflict`),列出候选并请用户确认主风格或是否明确融合。
   5. 用户确认融合后仍需选定一个**主 pack**;其它风格只作为经 core 边界过滤的辅助视觉语言,不得把两个 pack 假装“归并为同一 pack”。
1. **用户单一显式风格代号/风格名**(已过第 0 步无冲突)→ 先检查该 pack 与识别卡性别/品类事实是否存在边界张力,再决定是否直路由(仍需动作授权才生图)。
   - 若显式风格是明显性别/品类倾向 pack,且识别事实与其方向冲突或高度不适配(如`女装连衣裙` + `cityboy/宽松男装/男装通勤`,或命中 pack `anti_categories`),**不得**静默改服饰事实、改模特性别或强行直路由;停 `style-conflict-hold`,说明张力,请用户二选一:`保留原服饰/性别事实,只借该风格氛围` 或 `改走对应男装/女装/更适配风格路线`。
   - 若用户明确选择"保留原服饰事实 + 借氛围",可继续使用该 pack 的可转译视觉语言,但 core 性别年龄轴与品类保真仍优先;若用户选择改路线,回到 style-router 推荐/确认。
   - 该规则不把普通可共存风格变成新菜单;只在显式风格与已识别性别/品类事实冲突时触发。
2. **平台/用途线索** → 用途权重抬升,推荐对应 pack(品牌大片→editorial 族;电商主图→ecommerce-studio)。
3. **仅有识别事实,无风格线索** → §6 评分排序,**输出主推+2备选 + §6.1 完整风格选择面板,停 recognition-ready**。
4. **风格名完全无法识别**(无任何已知风格 token)→ **不报错、不默认**,回落第 3 步并列出可选风格。
5. 任一路由结果**不得绕过** safety-core(R1–R7)与输入门禁。

## 3. 风格互斥矩阵(供第 0 步冲突检测;同一造型不可兼得的视觉 register 视为互斥)

| 风格 A | 与之互斥的族(示例) |
|---|---|
| cyber-tech(赛博/未来机能) | old-money / quiet-luxury / balletcore / preppy / neo-chinese |
| balletcore(芭蕾柔美) | gorpcore / cyber-tech / workwear-vintage / american-street |
| old-money / quiet-luxury(克制低调) | y2k-millennium / guochao-street / maximalist / cyber-tech |
| gorpcore / athleisure(机能运动) | balletcore / old-money / coquette / italian-luxe |
| ecommerce-studio(纯净棚拍高转化) | 任意"重场景/重氛围 editorial"族(用途冲突) |

> 视觉上可兼容(不是自动路由许可):法式↔松弛、韩系↔quiet luxury↔性冷淡、preppy↔british-heritage、北欧↔clean-fit。最长匹配后若仍命中不同 slug,仍按 §2 第 0 步停 `style-conflict-hold`;只有用户确认主风格/融合后才继续。

## 4. 路由 trace(防"模型假装路由" + 防"假算分")

每次路由**必须**输出结构化 trace(可折叠展示 + 写审计日志)。**算分硬约束:**
- 每个 `hit` **必须**绑定一个 `rule_id`(来自 §5 权重表),其 `term` 必须是用户措辞/识别事实里**真实出现**的词(来自 §5 hit vocabulary)。
- `score` **只能**由命中规则权重**累加**:`score(pack) = Σ weight(rule_id_i)`;**禁止**模型自由填分。
- **同一输入 token 只消费一次:** 先执行 `STYLE_EXPLICIT`;一旦某个规范化输入片段已作为显式风格命中消费,不得再用同一片段重复命中 `USE_*`、`MAT_*`、`SILH_*` 或其它评分规则。不同真实片段可分别计分,trace 应能看出每个 term 的唯一 `rule_id`。
- **同一 pack 的 `STYLE_EXPLICIT` 权重最多计 1 次:** 同一 slug 同时命中多个不同别名/近义 trigger 时,trace 可把它们列在 `matched_terms`,但加权 hit 只保留 1 条 `STYLE_EXPLICIT(w=100)`;不得因用户重复说同一风格而把显式分叠成 200/300。
- **无命中即不打分:** 某 pack 若 `hits=[]`,不得出现在 candidates。
- trace 必须**可复算**:审计者据 §5 表 + 列出的 `rule_id` 应能重算同一 `score`;对不上 = 假 trace = FAIL。
- **不暴露:** 用户密钥/凭证、本地路径、环境变量;仅含识别事实与路由决策。

```
[route-trace]
detected: {category: 连衣裙, main_color: 米白, material: 醋酸缎, skin_exposure: 低,
           gender_age: 女装成人, ecommerce: 否, platform: 小红书, high_risk: 否}
conflict_check: 命中风格 token = [];无显式风格,跳过冲突 hold
candidates(top3):
  - {pack: french-effortless, score: 78, hits: [
        {rule_id: MAT_ACETATE_FR, term: 醋酸缎, w: 18},
        {rule_id: PLATFORM_XHS_RELAX, term: 小红书, w: 12},
        {rule_id: SILH_RELAXED, term: 松弛廓形, w: 8}, ... ]}   # Σw = 78,可复算
  - {pack: korean-cold-editorial, score: 71, hits: [{rule_id: COLOR_COOLWHITE_KR, term: 米白, w: 16}, ...]}
  - {pack: clean-fit, score: 64, hits: [{rule_id: SILH_MINIMAL_CLEAN, term: 极简版型, w: 14}, ...]}
chosen: 推荐主推=french-effortless(待用户确认);备选=korean-cold / clean-fit
fallback_used: 否
gate: recognition-ready(未生图,等待『风格代号+动作代号』)
```

> `rule_id + term + w` 让"路由是否真按事实算分"可**逐条复算**;`score` 是启发式排序累加值,**不对外声称是测量值**。

## 5. 权重常量表 + hit vocabulary(trace 唯一算分依据)

> 权重与命中词典是**常量**;模型只能"查表命中→累加",不能自创规则或分数。骨架节选,加 pack 时补全。

**(a) 权重表(rule_id → weight,节选):**
| rule_id | 维度 | 命中条件(term ∈ vocabulary) | weight |
|---|---|---|---|
| `STYLE_EXPLICIT` | 显式风格 | 用户直接说出该 pack 风格名/代号 | 100(直路由级) |
| `MAT_ACETATE_FR` | 材质 | 醋酸缎/雪纺/真丝 → french | 18 |
| `COLOR_COOLWHITE_KR` | 主色 | 冷白/冷灰 → korean-cold/nordic | 16 |
| `SILH_MINIMAL_CLEAN` | 版型 | 极简/基础版型 → clean-fit/nordic | 14 |
| `PLATFORM_XHS_RELAX` | 平台 | 小红书 → 生活/法式/clean | 12 |
| `USE_ECOM_STUDIO` | 用途 | 商品上架/店铺首图/白底商品照/详情页展示 → ecommerce-studio;仅在未命中该 pack 显式 trigger 时计分 | 20 |
| `USE_EDITORIAL` | 用途 | 品牌大片/杂志感 → editorial 族 | 16 |
| `SILH_RELAXED` | 版型 | 松弛/oversize 廓形 → french/street | 8 |
| `RISK_PENALTY_EXPOSE` | 风险(负) | 高露肤/高风险品类 → 压低重场景/露肤风格 | −P(见 safety-core) |

**(b) hit vocabulary(term 词典,节选;term 必须真实出现才可命中):**
- 材质:`醋酸缎/雪纺/真丝/针织/棉麻/皮革/金属/丝绒/牛仔` …
- 主色:`冷白/冷灰/暖土/高饱和/低饱和/暖金` …
- 版型:`oversize/廓形/修身/正装/极简/基础` …
- 平台/用途:`小红书/商品上架/店铺首图/白底商品照/详情页展示/品牌大片/杂志感/editorial` …
- 风格名/代号:见 §6 注册表(显式风格命中 → `STYLE_EXPLICIT`,先过 §2 第 0 步冲突检测)。

## 6. 触发词 → 风格包 注册表(pack `trigger_words` 是数据真相源;本表为完整人读镜像,SKILL description 只放高频词)

| 用户措辞(示例) | 路由到 pack | 说明 |
|---|---|---|
| 韩系/韩杂/韩系杂志风/韩国杂志/韩国杂志人像/W Korea/Vogue Korea/性冷淡/安静奢华/冷感大片 | korean-cold-editorial | 已落地 |
| 法式/松弛感/巴黎/effortless/French girl/慵懒法式 | french-effortless | 已落地 |
| 电商主图/高转化/淘宝白底/棚拍主图/商品主图人像/详情页人像 | ecommerce-studio | 已落地,默认棚拍 B;这些词已由 `STYLE_EXPLICIT` 消费时不得再重复记 `USE_ECOM_STUDIO` |
| 日系/日系生活/日杂/无印感/无印风/japanese lifestyle/muji style | japanese-lifestyle | 已落地（公开 Beta `DRAFT`；`通勤日系穿搭`只命中本包,不靠裸「通勤」强塞 office；`日系简约男装`则按最长完整触发词归 cityboy） |
| 美式/美式街头/街拍/vibe 街头/美式复古街头/american street | american-street | 已落地（裸「街头」已移除,避免与 §6 `街头国风`→guochao-street 碰撞） |
| 老钱/old money/old-money/世家/低调奢华/名媛世家 | old-money | 已落地 |
| quiet luxury/quiet-luxury/静奢风/静奢穿搭/当代静奢 | quiet-luxury | 已落地（触发与 old-money「低调奢华」/韩系「安静奢华」隔离,裸「静奢」因是「安静奢华」子串故排除） |
| preppy/美式学院/常春藤风/ivy style/校园学院风/varsity prep | preppy | 已落地（v1 静态;美式学院 lane;与 british-heritage 视觉可融合,但同时显式命中仍先 hold） |
| 英伦传承/传统英伦/british heritage/heritage tailoring/tweed country/英式复古 | british-heritage | 已落地（v1 静态;英伦传承 lane;与 preppy 同时显式命中仍先 hold） |
| 极简基础/极简版型/基础款/clean fit/简约基础/minimal basic | clean-fit | 已落地（Wave 2;冷调极简基础 lane;裸『极简』**不直路由**、只作 §5 SILH_MINIMAL_CLEAN 评分词(→clean-fit/nordic 共候选);暖调无印→japanese,『北欧/性冷淡极简』归 nordic;同时显式命中仍先 hold） |
| 北欧极简/性冷淡极简/nordic minimal/scandi minimal/斯堪的纳维亚/冷淡北欧 | nordic-minimal | 已落地（v1 静态;与 clean-fit 视觉可融合但同时显式命中仍先 hold,裸『极简』仍只作 §5 评分词） |
| gorpcore/山系/户外机能/机能户外/山系机能/outdoor technical | gorpcore | 已落地（v1 静态;机能户外 lane） |
| 运动风/瑜伽/athleisure/运动休闲/健身穿搭/sporty chic | athleisure | 已落地（Wave 2;『机能/户外/山系』仍归 gorpcore,裸『运动』『松弛感』排除——松弛属 french/street SILH_RELAXED） |
| balletcore/芭蕾风/芭蕾柔美/纱裙轻盈/ballet mood/soft ballet | balletcore | 已落地（v1 静态;与 gorpcore/cyber/workwear/street 等互斥见 §3） |
| Y2K/千禧风/千禧辣妹/复古千禧/y2k millennium/millennium style | y2k-millennium | 已落地（v1 静态;与 old-money/quiet-luxury 互斥见 §3） |
| 新中式/立领盘扣/neo chinese/modern chinese/东方极简/中式现代 | neo-chinese | 已落地（v1 静态;禁古装 cosplay,见 recognition §3.7） |
| 国潮街头/街头国风/guochao street/国风街头/潮流国风/新国潮 | guochao-street | 已落地（v1 静态;国风街头 lane） |
| 品牌大片/杂志感/editorial | korean-cold / italian-luxe(按事实) | editorial 族(§5 USE_EDITORIAL 共享评分词,**不直路由**、按识别事实细分;italian-luxe 已落地见下行) |
| 意式奢华/意式优雅/米兰风/意大利风格/italian luxe/italian luxury | italian-luxe | 已落地（Wave 2;暖调意式奢华 editorial lane;『品牌大片/杂志感/editorial』不进本行、只作 §5 USE_EDITORIAL 评分词→korean-cold/italian-luxe 共候选;与 athleisure/gorpcore 互斥见 §3） |
| 男装 + 各风格 | korean-menswear / cityboy / workwear-vintage / gorpcore | 性别横切共享识别事实,**不直路由**;须继续命中下方具体 pack 或按识别事实评分 |
| cityboy/都市男孩/宽松男装/男装通勤/casual menswear/city casual/日系简约男 | cityboy | 已落地（v1 静态;都市宽松男装 lane;`日系简约男装`按最长完整触发词归本包,淘汰 japanese 的裸`日系`） |
| korean menswear/韩国男装/韩式男装/冷感男装/首尔男装/seoul menswear | korean-menswear | 已落地（v1 静态;韩式冷感男装 lane） |
| 复古工装/workwear/工装复古/heritage workwear/vintage utility/rugged workwear | workwear-vintage | 已落地（v1 静态;复古工装 lane） |
| 职场通勤/OL通勤/商务女装/office commute/office lady style/通勤女装 | office-commute-women | 已落地（v1 静态;女性职场通勤 lane;男装通勤归 cityboy） |
| 度假风/resort/海岛度假/沙滩度假/resort vacation/假日度假 | resort-vacation | 已落地（v1 静态;旺季泳装/连衣裙时仍叠 safety-core R4） |
| coquette/千金风/甜美名媛/ladylike coquette/coquette style/精致淑女 | coquette-ladylike | 已落地（v1 静态;高客单甜美名媛 lane;禁幼态化/性化） |
| 童装/儿童/亲子 | 儿童版风格 + safety-core R1 | 敏感主体通道(非独立 pack;不因风格包放宽 R1) |
| 泳装/内衣/比基尼 | resort-vacation / clean-fit + safety-core R4 | 高风险通道(共享识别事实,不直路由;R4 优先) |

> **注册表 slug 必须与 `references/styles/<slug>.pack.yaml` 文件名一致,每个单 pack 行的触发词集合必须与该 pack `trigger_words` 完全一致**(`pack-lint` 机械校验)。v1 静态风格库已落地 24 个 pack;**后续新增未落地风格命中时,router 回落 §6 推荐并提示"该风格尚在路线图"**,不报错不默认韩系。

### 6.1 用户可见完整风格选择面板

当风格尚未确认时,推荐区后必须展示完整注册包目录,让推荐与用户选择权同时成立:

- 标题写 `全部可选风格(N)`,N 必须等于当前通过 pack-lint 的已落地 pack 数;当前为 24。数据只取上方 §6 注册表/对应 pack `name+slug`,不得凭记忆漏包、增包或把路线图风格混入。
- 每个 pack 恰好出现一次,使用 `中文短名 (slug)`;按界面导航可压成 4 行/组,分组只为阅读,不代表自动融合、成熟度或安全等级。
- 主推和两个备选在完整目录中加 `AI主推`/`备选`标记;完整目录仍允许用户选择其它任一**单一主风格**。固定表达等价语义:`推荐只是建议,不是替你决定;你可以从全部N个风格中自由选择。`
- 已有单一有效显式风格时直接确认该选择,不重复铺满目录或延迟合法动作;只需说明仍可从 N 个风格中改选。多 pack 冲突仍按 §2 停 `style-conflict-hold`,不因完整目录而静默挑一个。
- 童装/儿童输入可从 24 个 pack 选择视觉方向,但**可选择不等于可放宽**:R1 始终优先,成人化、性感化、暴露或危险元素必须过滤;pack 与童装事实/`anti_categories` 有张力时先说明并确认,敏感童装品类按 core 推荐非人像安全形态。
- 该面板属于免费文字交互,不调用 `image_gen`;风格确认后仍须模式/动作与付费授权门禁。

## 7. trigger-eval(L1 发现 + L2 路由)
`evals/trigger-evals.json` 覆盖 core L1 发现与人读 L2 期望;`evals/style-route-evals.json` 由 `tools/trigger-eval.py` 对真实 query 执行规范化、同包别名折叠、最长匹配与 route/hold/none 判定。正负各列:L1 正(法式/日系/老钱/电商/男装/童装 → 触发 core)、L1 负(带货文案配图→xhs;狗粮→非服饰)、L2 确定性归属、L2 多 pack hold、L2 真兜底、L2 假 trace 检测、互抢隔离。
