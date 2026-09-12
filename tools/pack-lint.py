#!/usr/bin/env python3
"""pack-lint.py — 风格包单向安全 linter（G3,已收口 Codex G3 审计 P0/P1）。

校验 styles/<slug>.pack.yaml：必填字段齐全、禁用工具/凭证/网络 token、
禁放宽安全短语、禁自然语言凭证 fallback（API key / native-generation-unavailable fallback）、
安全只增不减（safety_delta.cannot_relax 必须为布尔 True 且位于正确层级）、
slug 与文件名一致、model_persona 不得声明年龄/性化主体。
传入正式 pack 时还会校验 `references/style-router.md` 单 pack 注册行与 `trigger_words` 完整集合一致。

抗绕过（Codex P0#2）：在原文 + Unicode 同形归一 + 拆词折叠 + base64 解码 四个视图上扫描禁用 token。
结构强校验（Codex P0#1 / B5）：优先 PyYAML；无 PyYAML 时用内置 nested-aware 解析器，
仍能定位 safety_delta.cannot_relax 的真实层级，不被 notes.cannot_relax 之类错位声明欺骗。

退出码：0=PASS（可含 WARN）；1=FAIL（≥1 HARD）；2=用法/解析错误。
依赖：仅标准库。安装 PyYAML 时自动启用更强类型校验。
"""
import sys
import os
import re
import base64
import unicodedata

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_ROOT = os.path.join(REPO_ROOT, "skills", "threadtruth-studio")
ROUTER_PATH = os.path.join(SKILL_ROOT, "references", "style-router.md")

# ---------------------------------------------------------------------------
# schema：允许的顶层键（= 必填集合;出现集合外顶层键 → WARN，防 notes.cannot_relax 类错位）
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = [
    "name", "slug", "version", "maturity", "depends_on_core",
    "trigger_words", "suitable_categories", "anti_categories",
    "visual_language", "model_persona", "scenes", "lighting_palette",
    "pose_masters", "default_mode",
    "negative_delta_add", "safety_delta",
    "d0_preview", "d1_final", "d3_prompts", "qa_extra",
    "samples_required", "evals",
]
ALLOWED_TOP_KEYS = set(REQUIRED_FIELDS)

# ---------------------------------------------------------------------------
# 禁用 token（工具/凭证/网络/生成入口）。带分隔符的原始形态，用于原文/同形视图逐行扫描。
# ---------------------------------------------------------------------------
HARD_TOKEN_PATTERNS = [
    r"image_gen", r"imagegen", r"OPENAI_API_KEY", r"api\.openai\.com",
    r"\bopenai\b", r"\bcurl\b", r"\bwget\b", r"requests\.", r"subprocess",
    r"os\.environ", r"os\.getenv", r"\.env\b",
    r"moderation\s*=\s*low", r"input_fidelity",
    r"api[\s_.\-]?key",  # api key / api-key / api_key / apikey（凭证引用,pack 一律禁）
]
# 去分隔符后的紧凑形态，用于"拆词折叠"视图（i m a g e _ g e n → imagegen）。
COMPACT_TOKENS = [
    "imagegen", "openaiapikey", "apiopenaicom", "openai", "curl", "wget",
    "requests", "subprocess", "osenviron", "osgetenv", "moderationlow",
    "inputfidelity",
    "apikey", "keyfallback",  # 拆词绕过 a p i k e y / k e y f a l l b a c k
]
# 放宽安全/越权短语。
HARD_PHRASE_PATTERNS = [
    r"忽略门禁", r"跳过门禁", r"绕过", r"bypass", r"ignore\s+core",
    r"disable\s+safety", r"关闭安全", r"无需授权", r"不需授权",
    r"直接生图", r"cannot_relax\s*:\s*false",
    r"negative_delta_remove", r"safety_override",
]
# 自然语言"生成能力 fallback"检测（Codex G3 复审 finding-N + 复确认收口）。
# pack 只管视觉轴,不得规定任何凭证/远程/生成端点退路（基线 #17 禁 fallback 红线)。
# 在"换行折叠 + 同形归一"全文视图上扫描,跨行不漏(见 fallback_scan)。
# (1) 凭证/远程/外部生成基础设施名词 —— style pack 永无正当理由出现,独立命中即 HARD。
#     denylist 只保证确定性命中;泛化靠下方 (4) 二要素共现规则。
FALLBACK_HARD_NOUNS = [
    r"\bendpoint\b", r"remote\s+renderer", r"remote\s+generator",
    r"credential\s+route", r"backup\s+credential", r"\bkey\s+(path|route|vault|store)\b",
    r"relay\s+server", r"\bproxy\b", r"external\s+service",
    r"hosted\s+model", r"cloud\s+render(er)?", r"off-?site\s+generation",
    r"render\s+service",
    # 中文外部基础设施
    r"外部接口", r"代理服务器?", r"云端渲染", r"渲染服务", r"中转服务", r"内置生图能力",
]
# (2) 生成能力缺失短语 —— 暗示需要 fallback,独立命中即 HARD：
FALLBACK_HARD_CAPLOSS = [
    r"cannot\s+draw", r"can'?t\s+draw", r"unable\s+to\s+draw",
    r"drawing\s+is\s+(un)?(available|blocked)", r"native\s+generation\s+unavailable",
    r"generation\s+(is\s+)?unavailable", r"cannot\s+generate", r"generation\s+cannot\s+run",
    # 中文
    r"不能画图", r"无法生成", r"原生[^，。\n]{0,8}不可用",
]
# (3) fallback 同窗上下文词（≤60 字符）。**不含裸 key**——避免 "fallback color … key light" 误报。
FALLBACK_CONTEXT = (
    r"(api|openai|credential|token|secret|\bauth\b|native|generat\w*|"
    r"endpoint|remote|renderer|provider|\bservice\b|drawing|\brender\b)"
)
# (4) 二要素共现（Codex v0.2.2 复审收口:堵同义/中文,泛化超出 denylist）：
#     "生成能力缺失" × "外部路由" 同窗(≤80)且全文含"生成动作" → HARD。
#     注意:render/draw 只入 FB_GEN(门控),**不入 FB_ROUTE**——否则 "blocked…render" 等正常视觉句误杀。
FB_LOSS = (r"(unavailable|blocked|fail(s|ed|ing)?|missing|cannot|can'?t|unable|"
           r"无法|不能|不可用|没有|缺少|失败|"
           r"[跑画生做出成搞]不[动出了来到定])")  # 中文"动词+不+结果"能力缺失;结果字白名单避开成语(一成不变/纹丝不动)
# ROUTE 用复合词避免裸 `平台`(防 `平台鞋` 厚底鞋)/裸 `工具` 误伤;`外部`/`远程` 已覆盖 外部工具/外部平台 等。
# 这些词只在二要素 ROUTE 用、不升独立 HARD noun:有 LOSS×ROUTE 门控护着,`third-party styling`
# / `vendor-style moodboard` 等正常风格参考词(无能力缺失词同窗)不会被误杀。
FB_ROUTE = (r"(relay|proxy|external|hosted|off-?site|cloud|\bserver\b|provider|\bservice\b|"
            r"endpoint|third[- ]?party|\bcompute\b|\bvendor\b|another\s+tool|other\s+tool|outsourc\w*|"
            r"代理|外部|云端|中转|远程|外接|"
            r"第三方|算力|计算资源|他处|转交|交给|供应商|别家|另找|"
            r"别的平台|别的工具|别的服务|其他平台|其他工具|换(平台|工具|服务))")
# 成像/绘制 仅作生成动作门控(摄影常说"镜头成像锐利",但 GEN 不单独触发,须 LOSS×ROUTE 邻接才 HARD)。
FB_GEN = r"(generat|render|draw|image\s+creation|生图|生成|画图|渲染|出图|成像|绘制)"
# 拆词折叠视图也要查的 fallback 名词紧凑形（拦 `e n d p o i n t fallback`）。
COMPACT_FALLBACK_NOUNS = [
    "endpoint", "relayserver", "proxyprovider", "externalservice",
    "hostedmodel", "cloudrender", "cloudrenderer", "offsitegeneration",
    "renderservice", "remoterenderer", "remotegenerator",
    "credentialroute", "backupcredential",
]
# SOFT：core 状态词不应在 pack 中重定义（preview-grid 是合法 samples 产物名，不列入）。
SOFT_STATUS_WORDS = [r"tool-blocked", r"gate-blocked", r"image-ready", r"image-draft"]

# model_persona 禁词（Codex P1#7）：年龄主体由 core 按性别年龄轴注入，pack 不得声明；性化词一律禁。
PERSONA_AGE_TERMS = [
    r"\badult\b", r"\bgrown[- ]?up\b", r"\bmature\b", r"\bteen\b", r"\bteenage[r]?\b",
    r"\badolescent\b", r"\bminor\b", r"\bchild(ren)?\b", r"\bkid[s]?\b", r"\bbaby\b",
    r"\btoddler\b", r"\binfant\b", r"\byouth\b", r"\bschool ?girl\b", r"\bschool ?boy\b",
    r"\bunderage\b", r"\bloli\b",
    r"成人", r"成年", r"儿童", r"小孩", r"宝宝", r"婴", r"未成年", r"少女", r"少年", r"萝莉",
]
PERSONA_SEXUAL_TERMS = [
    r"\bsexy\b", r"\bseductive\b", r"\bsensual\b", r"\bnude\b", r"\bnaked\b",
    r"\berotic\b", r"\balluring\b", r"\bprovocative\b", r"\bsultry\b", r"\bflirt",
    r"性感", r"挑逗", r"情色", r"裸", r"诱惑", r"暧昧",
]

# Unicode 同形（Cyrillic/Greek lookalike → Latin），用于反同形绕过。
CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "ѕ": "s", "і": "i", "ј": "j", "ԁ": "d", "ɡ": "g", "ⅼ": "l", "ո": "n",
    "А": "A", "Е": "E", "О": "O", "Р": "P", "С": "C", "Х": "X", "М": "M",
    "Т": "T", "В": "B", "Н": "H", "К": "K",
    "ο": "o", "α": "a", "ρ": "p", "ε": "e", "τ": "t", "υ": "u", "ι": "i", "κ": "k",
}


def deobfuscate(text):
    """NFKC 归一 + 同形字映射 → Latin，用于反 Unicode 同形绕过。"""
    t = unicodedata.normalize("NFKC", text)
    return "".join(CONFUSABLES.get(ch, ch) for ch in t)


def collapse_spaced(text):
    """提取"单字符 + 分隔符"重复序列并折叠，反拆词绕过。

    仅匹配多个单字符被 [空格/.​_-] 分隔的片段（正常多字母单词不会命中），
    避免合并正常散文导致误报。
    """
    out = []
    for m in re.finditer(r"(?:[A-Za-z0-9][ \t._\-]+){3,}[A-Za-z0-9]", text):
        out.append(re.sub(r"[ \t._\-]+", "", m.group(0)).lower())
    return out


def base64_scan(text):
    """扫描长 base64 片段:解码含禁用 token → HARD;解码为二进制大块 → WARN(可疑)。"""
    hard, soft = [], []
    for m in re.finditer(r"[A-Za-z0-9+/]{12,}={0,2}", text):
        s = m.group(0)
        try:
            dec = base64.b64decode(s + "===", validate=False)
        except Exception:
            continue
        ds = dec.decode("utf-8", "ignore")
        printable_ratio = (sum(c.isprintable() or c.isspace() for c in ds) / len(ds)) if ds else 0
        if ds and printable_ratio > 0.8:
            low = deobfuscate(ds).lower()
            for pat in HARD_TOKEN_PATTERNS:
                if re.search(pat, low, re.IGNORECASE):
                    hard.append(f"base64 解码命中禁用 token /{pat}/：{s[:24]}… → {ds[:40]!r}")
                    break
        elif len(s) >= 32:
            soft.append(f"可疑 base64/二进制串（pack 不应含编码载荷）：{s[:32]}…")
    return hard, soft


def fallback_scan(text):
    """检测 pack 内"生成能力/凭证/远程 fallback"。

    在"换行折叠 + 同形归一"全文视图上扫描,使跨行 fallback(被 40 字符行内窗口切断)不漏;
    裸 key 不入上下文,避免 "fallback color … key light" 等正常摄影词误报(Codex 复确认收口)。
    """
    hard = []
    flat = re.sub(r"\s+", " ", deobfuscate(text)).lower()  # 换行→空格 + 同形归一
    for pat in FALLBACK_HARD_NOUNS + FALLBACK_HARD_CAPLOSS:
        if re.search(pat, flat, re.IGNORECASE):
            hard.append(f"凭证/远程/生成 fallback 信号: /{pat}/（pack 不得规定生成能力退路,属 core 工具门禁）")
    # key 紧邻 fallback（凭证义）。FP 例 "fallback color … key light" 中两词不相邻,不命中。
    if re.search(r"key\s*fallback|fallback\s*key\b", flat):
        hard.append("凭证 fallback: key↔fallback 相邻")
    # fallback + 生成/凭证语境同窗（≤60 字符,换行已折叠)。
    for m in re.finditer(r"fallback", flat):
        w = flat[max(0, m.start() - 60): m.end() + 60]
        cm = re.search(FALLBACK_CONTEXT, w, re.IGNORECASE)
        if cm:
            hard.append(f"自然语言 fallback + 生成/凭证语境(命中 {cm.group(0)}): «…{w.strip()[:60]}…»")
            break
    # 二要素共现：生成能力缺失 × 外部路由 同窗(≤80),且全文含生成动作 → HARD(泛化同义/中文)。
    if re.search(FB_GEN, flat, re.IGNORECASE):
        for m in re.finditer(FB_LOSS, flat, re.IGNORECASE):
            w = flat[max(0, m.start() - 80): m.end() + 80]
            rm = re.search(FB_ROUTE, w, re.IGNORECASE)
            if rm:
                hard.append(
                    f"生成能力缺失({m.group(0)}) × 外部路由({rm.group(0)})共现 → "
                    f"禁'生成 fallback'(退路决策属 core 工具门禁)")
                break
    return list(dict.fromkeys(hard))  # 去重保序


# ---------------------------------------------------------------------------
# 解析：优先 PyYAML;否则内置 nested-aware 解析器（支持顶层标量/块映射/行内 flow 映射）。
# ---------------------------------------------------------------------------
def _strip_comment(line):
    """去掉 YAML 行内注释（' #...'），保守处理不含引号内 # 的常见情形。"""
    if line.lstrip().startswith("#"):
        return ""
    m = re.search(r"\s#", line)
    return line[: m.start()] if m else line


def _parse_inline_map(s):
    """解析行内 flow 映射 {k: v, ...} → dict（值保留为字符串）。"""
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    inner = s[1:-1].strip()
    d = {}
    if not inner:
        return d
    for part in inner.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            d[k.strip()] = v.strip()
    return d


def _fallback_parse(text):
    """内置降级解析：返回顶层 dict;safety_delta 解析为嵌套 dict;字符串标量保留。

    关键:正确区分 safety_delta.cannot_relax 与 notes.cannot_relax(错位)，
    闭合 Codex P0#1 / B5（无 PyYAML 时仍能层级校验）。
    """
    data = {}
    lines = text.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        raw = _strip_comment(lines[i])
        if not raw.strip():
            i += 1
            continue
        m = re.match(r"^(\s*)([A-Za-z_][\w-]*)\s*:(.*)$", raw)
        if not m or len(m.group(1)) != 0:  # 只在顶层启动键;缩进行由块逻辑消费
            i += 1
            continue
        key = m.group(2)
        rest = m.group(3).strip()
        if rest.startswith("{"):
            data[key] = _parse_inline_map(rest) or {}
            i += 1
        elif rest in (">", "|", ">-", "|-", ""):
            # 块标量或块映射:消费后续更深缩进行
            block, j = [], i + 1
            while j < n:
                bl = lines[j]
                if bl.strip() == "":
                    block.append(bl)
                    j += 1
                    continue
                indent = len(bl) - len(bl.lstrip())
                if indent == 0:
                    break
                block.append(bl)
                j += 1
            # 判定块是映射(含 'subkey:')还是标量
            sub = {}
            is_map = False
            for bl in block:
                bm = re.match(r"^\s+([A-Za-z_][\w-]*)\s*:(.*)$", _strip_comment(bl))
                if bm and not bl.lstrip().startswith("-"):
                    is_map = True
                    sub[bm.group(1)] = bm.group(2).strip()
            if rest in (">", "|", ">-", "|-"):
                data[key] = " ".join(b.strip() for b in block if b.strip())
            elif is_map:
                data[key] = sub
            else:
                # 块序列或空 → 保留原始文本片段
                data[key] = "\n".join(b.strip() for b in block).strip()
            i = j
        else:
            data[key] = rest
            i += 1
    return data


def parse_pack(text):
    """返回 (data:dict, used_pyyaml:bool)。解析失败返回 (None, ...)。"""
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data, True
        return None, True
    except ImportError:
        return _fallback_parse(text), False
    except Exception:
        # PyYAML 存在但语法错 → 退化到内置解析尽量给出结构性反馈
        return _fallback_parse(text), False


def _truthy(v):
    return v is True or (isinstance(v, str) and v.strip().lower() == "true")


def lint_file(path):
    hard, soft = [], []
    if not os.path.isfile(path):
        return 2, [f"文件不存在: {path}"], []
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    data, used_yaml = parse_pack(text)
    norm = deobfuscate(text)  # 同形归一视图

    # 1. 顶层键集合（解析优先;解析不可用时回退正则抓顶层键）
    if isinstance(data, dict):
        top_keys = set(data.keys())
    else:
        top_keys = set(re.findall(r"^([A-Za-z_][\w-]*)\s*:", text, re.MULTILINE))

    # 2. 必填字段
    for field in REQUIRED_FIELDS:
        if field not in top_keys:
            hard.append(f"缺必填字段: {field}")

    # 3. 未知顶层键（防 notes.cannot_relax 类错位声明）
    for k in sorted(top_keys - ALLOWED_TOP_KEYS):
        soft.append(f"未知顶层键: {k}（schema 外字段;cannot_relax 等只在 safety_delta 内有效）")

    # 4. slug 与文件名一致
    fname_slug = os.path.basename(path).split(".")[0]
    slug_val = data.get("slug") if isinstance(data, dict) else None
    if not slug_val:
        m = re.search(r"^slug\s*:\s*([A-Za-z0-9-]+)", text, re.MULTILINE)
        slug_val = m.group(1) if m else None
    if slug_val and str(slug_val).strip() != fname_slug:
        hard.append(f"slug({slug_val}) 与文件名({fname_slug}) 不一致")

    # 5. 禁用 token / 放宽短语 —— 原文 + 同形视图逐行扫描（同形视图用于 Unicode 绕过）
    seen = set()
    def scan_lines(src, tag):
        for i, line in enumerate(src.splitlines(), 1):
            for pat in HARD_TOKEN_PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    key = (pat, line.strip()[:60])
                    if key not in seen:
                        seen.add(key)
                        hard.append(f"{tag}L{i} 禁用 token: /{pat}/ → {line.strip()[:80]}")
            for pat in HARD_PHRASE_PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    key = (pat, line.strip()[:60])
                    if key not in seen:
                        seen.add(key)
                        hard.append(f"{tag}L{i} 放宽安全/越权: /{pat}/ → {line.strip()[:80]}")
            for pat in SOFT_STATUS_WORDS:
                if re.search(pat, line, re.IGNORECASE):
                    soft.append(f"{tag}L{i} 重定义 core 状态词: /{pat}/（应由 core 管）")
    scan_lines(text, "")
    if norm != text:
        scan_lines(norm, "[同形归一]")

    # 6. 拆词折叠视图（i m a g e _ g e n → imagegen;e n d p o i n t → endpoint）
    for seg in collapse_spaced(norm):
        for tok in COMPACT_TOKENS:
            if tok in seg:
                hard.append(f"拆词折叠命中禁用 token: {tok}（来自 «{seg[:40]}»）")
        for tok in COMPACT_FALLBACK_NOUNS:
            if tok in seg:
                hard.append(f"拆词折叠命中 fallback 基础设施名词: {tok}（来自 «{seg[:40]}»）")

    # 7. base64 解码视图
    b64_hard, b64_soft = base64_scan(text)
    hard += b64_hard
    soft += b64_soft

    # 7b. 自然语言"生成能力 fallback"扫描(换行折叠全文视图,跨行不漏;裸 key 不误报)
    hard += fallback_scan(text)

    # 8. 安全只增不减:safety_delta.cannot_relax 必须为 True 且在正确层级（P0#1 强校验）
    if isinstance(data, dict):
        sd = data.get("safety_delta")
        if not isinstance(sd, dict):
            if "safety_delta" in top_keys:
                hard.append("safety_delta 必须是映射且含 cannot_relax: true（当前非映射/为空）")
        else:
            if not _truthy(sd.get("cannot_relax")):
                hard.append("safety_delta.cannot_relax 必须显式为布尔 true（不放宽 core 安全）")
            for k in sd:
                if k != "cannot_relax" and re.search(r"relax|override|remove|disable|放宽|关闭", str(k), re.IGNORECASE):
                    hard.append(f"safety_delta 含放宽类键: {k}（仅允许 extra_constraints / cannot_relax）")
        # 顶层错位 cannot_relax（不在 safety_delta 内）→ 提示
        if "cannot_relax" in top_keys:
            soft.append("cannot_relax 出现在顶层（仅 safety_delta.cannot_relax 有效）")
    else:
        # 解析不可用时退回正则:至少要求出现 cannot_relax: true（弱保证,已尽力）
        if not re.search(r"cannot_relax\s*:\s*true", text):
            hard.append("safety_delta.cannot_relax 必须显式为 true（解析降级,正则未命中）")

    # 9. model_persona 净化（P1#7）:不得声明年龄/性化主体
    persona = data.get("model_persona") if isinstance(data, dict) else None
    if persona is None:
        m = re.search(r"^model_persona\s*:\s*(.+)$", text, re.MULTILINE)
        persona = m.group(1) if m else ""
    persona_norm = deobfuscate(str(persona))
    for pat in PERSONA_AGE_TERMS:
        if re.search(pat, persona_norm, re.IGNORECASE):
            hard.append(f"model_persona 含年龄词 /{pat}/（年龄主体由 core 按性别年龄轴注入,pack 禁声明）")
    for pat in PERSONA_SEXUAL_TERMS:
        if re.search(pat, persona_norm, re.IGNORECASE):
            hard.append(f"model_persona 含性化词 /{pat}/（违反去性感化,pack 禁声明）")

    # 10. SOFT：anti_categories 为空 / evals 文件缺失
    anti = data.get("anti_categories") if isinstance(data, dict) else None
    if (isinstance(anti, list) and not anti) or re.search(r"^anti_categories\s*:\s*\[\s*\]", text, re.MULTILINE):
        soft.append("anti_categories 为空（多数风格都有不适配品类）")
    ev = data.get("evals") if isinstance(data, dict) else None
    if not ev:
        me = re.search(r"^evals\s*:\s*(\S+)", text, re.MULTILINE)
        ev = me.group(1) if me else None
    if ev:
        ep = os.path.join(os.path.dirname(path), str(ev))
        # Public Plugin releases keep evals outside the runtime payload. A
        # repo:// URI explicitly addresses the development evidence root and
        # cannot be mistaken for a runtime-relative file.
        repo_ep = None
        if str(ev).startswith("repo://"):
            repo_ep = os.path.join(SKILL_ROOT, "..", "..", str(ev)[len("repo://") :])
        if not os.path.isfile(ep) and not os.path.isfile(str(ev)) and not (repo_ep and os.path.isfile(repo_ep)):
            soft.append(f"evals 指向文件不存在: {ev}（交付前必补）")

    code = 1 if hard else 0
    return code, hard, soft


def _extract_triggers(path):
    """从 pack 文件抽取 trigger_words(flow 与 block 序列两种合法 YAML 写法都支持;真相源=pack 文件,L18)。

    返回 (triggers:list, declared:bool)。declared = 文件是否声明了 `trigger_words:`(无论能否解析),
    供 cross_pack_check 区分"未声明"与"声明了但解析不出"(后者 → HARD,拒绝未知格式静默绕过冲突检查)。
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        return [], False
    declared = re.search(r"^trigger_words\s*:", txt, re.MULTILINE) is not None
    # (1) flow 写法: trigger_words: [a, b, c]
    m = re.search(r"^trigger_words\s*:\s*\[(.*?)\]", txt, re.MULTILINE | re.DOTALL)
    if m:
        return [w.strip().strip("'\"") for w in m.group(1).split(",") if w.strip()], declared
    # (2) block 序列写法:
    #     trigger_words:
    #       - a
    #       - b
    m = re.search(r"^trigger_words\s*:\s*(#.*)?$", txt, re.MULTILINE)
    if m:
        out = []
        for ln in txt[m.end():].splitlines():
            s = _strip_comment(ln)
            if s.strip() == "":
                continue
            bm = re.match(r"^(\s+)-\s*(.+?)\s*$", s)
            if bm:
                out.append(bm.group(2).strip().strip("'\""))
            else:
                break  # 缩进结束 / 下一个键 → 序列读完
        return out, declared
    return [], declared


def _registry_term_norm(term):
    """Router 镜像表集合比较只折叠大小写/Unicode/重复空白,保留连字符别名差异。"""
    text = unicodedata.normalize("NFKC", str(term)).casefold().strip()
    return re.sub(r"\s+", " ", text)


def _strip_md_code(text):
    text = text.strip()
    if len(text) >= 2 and text.startswith("`") and text.endswith("`"):
        return text[1:-1].strip()
    return text


def router_registry_check(paths, router_path=ROUTER_PATH):
    """校验 style-router §6 单 pack 行与真实 pack trigger_words 的完整集合一致。

    pack `trigger_words` 是数据真相源;router 表是人读镜像。复合/用途行(第二列不是单个
    已落地 slug)不参与集合比较。集合比较保留 `old money`/`old-money` 等原始别名差异,
    避免 router 静默漏掉对外承诺的合法拼写。
    """
    hard = []
    real_paths = [p for p in paths if os.path.basename(p).split(".")[0] != "_TEMPLATE"]
    styles_dir = os.path.join(SKILL_ROOT, "references", "styles")
    all_pack_slugs = {
        name.split(".")[0]
        for name in os.listdir(styles_dir)
        if name.endswith(".pack.yaml") and not name.startswith("_TEMPLATE.")
    }
    try:
        with open(router_path, "r", encoding="utf-8") as f:
            router_text = f.read()
    except OSError as exc:
        return [f"无法读取 router 注册表 {router_path}: {exc}"]

    registry = {}
    for lineno, line in enumerate(router_text.splitlines(), 1):
        m = re.match(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|", line)
        if not m:
            continue
        terms_cell, slug_cell = m.groups()
        slug = _strip_md_code(slug_cell)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            continue
        if slug not in all_pack_slugs:
            hard.append(f"router L{lineno} 注册了不存在的单 pack slug: {slug}")
            continue
        if slug in registry:
            hard.append(f"router 注册表 slug 重复: {slug}（L{registry[slug][0]} 与 L{lineno}）")
            continue
        terms = [_strip_md_code(t) for t in terms_cell.split("/") if _strip_md_code(t)]
        registry[slug] = (lineno, terms)

    for path in real_paths:
        slug = os.path.basename(path).split(".")[0]
        triggers, declared = _extract_triggers(path)
        if not declared or not triggers:
            # 单文件结构检查/跨包检查会给更具体信息;这里不重复猜测未知格式。
            continue
        if slug not in registry:
            hard.append(f"router 注册表缺少 pack 行: {slug}")
            continue
        lineno, router_terms = registry[slug]
        pack_map = {_registry_term_norm(t): t for t in triggers}
        router_map = {_registry_term_norm(t): t for t in router_terms}
        missing = [pack_map[k] for k in sorted(pack_map.keys() - router_map.keys())]
        extra = [router_map[k] for k in sorted(router_map.keys() - pack_map.keys())]
        if missing:
            hard.append(f"{slug}: router L{lineno} 缺 pack trigger_words: {missing}")
        if extra:
            hard.append(f"{slug}: router L{lineno} 多出 pack 未声明词: {extra}")
    return hard


def cross_pack_check(paths):
    """跨包触发词冲突:精确重复(HARD,router 归属歧义)+ 子串近邻(INFO,需最长匹配回归)。

    解析真实 pack `trigger_words`(L18:此前按 §6 手抄清单查漏掉 `quiet luxury` 双归属)。
    归一 = 小写 + 去空格 + 去连字符,故 `quiet luxury` == `quiet-luxury`(同包内变体不算冲突,只判**不同包**)。
    排除 `_TEMPLATE`(占位词)。
    """
    norm = lambda s: s.lower().replace(" ", "").replace("-", "")
    owners = []  # (slug, word, normalized)
    hard, info = [], []
    for p in paths:
        slug = os.path.basename(p).split(".")[0]
        if slug == "_TEMPLATE":
            continue
        trigs, declared = _extract_triggers(p)
        if declared and not trigs:
            # 声明了 trigger_words 却解析不出 → 拒绝静默绕过(否则有效 YAML 格式可逃过冲突检查)
            hard.append(f"{slug}: 声明了 trigger_words 但无法解析其写法（仅支持 flow `[...]` 或 block `- item`）—— 拒绝静默绕过跨包冲突检查")
            continue
        for w in trigs:
            owners.append((slug, w, norm(w)))
    # 精确重复(归一后同词、不同包)
    by_norm = {}
    for slug, w, nw in owners:
        bucket = by_norm.setdefault(nw, [])
        if slug not in {s for s, _ in bucket}:
            bucket.append((slug, w))
    for nw, lst in by_norm.items():
        if len(lst) > 1:
            words = "/".join(sorted({w for _, w in lst}))
            packs = ", ".join(sorted(s for s, _ in lst))
            hard.append(f"跨包精确重复触发词 «{words}» 归属 [{packs}]（router 归属歧义,须二选一收口 + near-miss eval 锁死）")
    # 子串近邻(归一后一方是另一方子串、不同包)→ INFO,不影响退出码
    for s1, w1, n1 in owners:
        for s2, w2, n2 in owners:
            if s1 == s2 or n1 == n2:
                continue
            if n1 in n2:
                info.append(f"跨包子串近邻: «{w1}»({s1}) ⊂ «{w2}»({s2}) —— 确认最长匹配归属/补 style-route eval")
    return hard, list(dict.fromkeys(info))


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    strict = "--strict" in argv
    if not args:
        print("用法: python3 pack-lint.py [--strict] <pack.yaml> [更多...]")
        return 2
    overall = 0
    for path in args:
        code, hard, soft = lint_file(path)
        status = "FAIL" if code == 1 else ("ERROR" if code == 2 else "PASS")
        print(f"\n=== {path} : {status} ===")
        for h in hard:
            print(f"  [HARD] {h}")
        for s in soft:
            print(f"  [WARN] {s}")
        if not hard and not soft:
            print("  ✓ 无问题")
        if code != 0:
            overall = max(overall, code)
        if strict and soft and code == 0:
            overall = max(overall, 1)
            print("  (--strict: WARN 视为失败)")

    # 跨包触发词冲突(传入 ≥2 个非模板 pack 时才有意义;单文件 lint 跳过)
    real_packs = [p for p in args if os.path.basename(p).split(".")[0] != "_TEMPLATE"]
    if len(real_packs) >= 2:
        cp_hard, cp_info = cross_pack_check(args)
        print("\n=== 跨包触发词冲突检查 ===")
        for h in cp_hard:
            print(f"  [HARD] {h}")
        for s in cp_info:
            print(f"  [INFO] {s}")
        if not cp_hard and not cp_info:
            print("  ✓ 跨包 0 精确重复 / 0 子串近邻")
        if cp_hard:
            overall = max(overall, 1)

    if real_packs:
        registry_hard = router_registry_check(real_packs)
        print("\n=== router ↔ pack 注册表一致性检查 ===")
        for h in registry_hard:
            print(f"  [HARD] {h}")
        if not registry_hard:
            print(f"  ✓ {len(real_packs)} 个 pack 的 router 行与 trigger_words 集合一致")
        if registry_hard:
            overall = max(overall, 1)
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv))
