#!/usr/bin/env python3
"""trigger-eval.py — 触发词归属与真实 query 路由的可执行断言检查。

near-miss / trigger-isolation eval 里写结构化 `assert_triggers`,本工具据**真实 pack `trigger_words`**
(flow 与 block 两种 YAML 写法都支持)验证每条 contains/excludes:
  - contains: 该 pack 的 trigger_words 必须含此词(归一后精确)。缺 → FAIL。
  - excludes: 该 pack 的 trigger_words 必须不含此词(为触发隔离刻意排除的近邻/过宽词)。含 → FAIL(归属泄漏)。
锚数据层、不依赖 router 打分实现;补 pack-lint(结构 + 跨包精确重复)之外的"归属回归"层。
未落地 pack 的断言跳过(无 pack 文件可验)并记 INFO。

`evals/style-route-evals.json` 进一步执行确定性显式路由:
  - NFKC + casefold；trigger 内部空白/连字符/下划线可等价,但 ASCII trigger 保留词边界；
  - 同 slug 等价别名折叠；
  - 严格子串命中淘汰短 trigger；
  - 最终 0/1/≥2 个 slug 分别判 none/route/hold。
  - 可选 `rule_hits` 还会机械断言同 pack `STYLE_EXPLICIT` 只加权一次,
    以及未被显式 trigger 消费的 `USE_ECOM_STUDIO` 用途命中。

退出码:0=PASS;1=FAIL(≥1 断言不成立);2=用法错。依赖:仅标准库。
"""
import sys
import os
import re
import glob
import json
import unicodedata

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_ROOT = os.path.join(REPO_ROOT, "skills", "threadtruth-studio")
PACK_GLOB = os.path.join(SKILL_ROOT, "references", "styles", "*.pack.yaml")
EVAL_GLOB = os.path.join(REPO_ROOT, "evals", "**", "*.json")
STYLE_ROUTE_EVAL = os.path.join(REPO_ROOT, "evals", "style-route-evals.json")
SEPARATOR_PATTERN = r"[\s_\-‐‑‒–—]*"
ASCII_WORD = re.compile(r"[a-z0-9]")

def norm(s):
    text = unicodedata.normalize("NFKC", str(s)).casefold()
    return re.sub(r"[\s_\-‐‑‒–—]+", "", text)


def trigger_pattern(term):
    """为 query 编译 trigger regex。

    只对 trigger 自身内已声明的分隔位允许空白/连字符/下划线等价;
    ASCII 首尾必须落在 ASCII 词边界,避免 `presort` 误命中 `resort`,
    也避免 `show Korea` 跨词拼成 `W Korea`。
    """
    text = unicodedata.normalize("NFKC", str(term)).casefold().strip()
    if not text:
        return None
    parts = [part for part in re.split(r"[\s_\-‐‑‒–—]+", text) if part]
    if not parts:
        return None
    body = SEPARATOR_PATTERN.join(re.escape(part) for part in parts)
    left = r"(?<![a-z0-9])" if ASCII_WORD.fullmatch(parts[0][0]) else ""
    right = r"(?![a-z0-9])" if ASCII_WORD.fullmatch(parts[-1][-1]) else ""
    return re.compile(left + body + right)


def extract_triggers(path):
    """抽 trigger_words:flow `[...]` 与 block `- item` 两种写法(与 pack-lint 一致)。"""
    try:
        txt = open(path, encoding="utf-8").read()
    except OSError:
        return []
    m = re.search(r"^trigger_words\s*:\s*\[(.*?)\]", txt, re.M | re.S)
    if m:
        return [w.strip().strip("'\"") for w in m.group(1).split(",") if w.strip()]
    m = re.search(r"^trigger_words\s*:\s*(#.*)?$", txt, re.M)
    if m:
        out = []
        for ln in txt[m.end():].splitlines():
            s = re.sub(r"\s+#.*$", "", ln).rstrip()
            if s.strip() == "":
                continue
            bm = re.match(r"^(\s+)-\s*(.+?)\s*$", s)
            if bm:
                out.append(bm.group(2).strip().strip("'\""))
            else:
                break
        return out
    return []


def load_landed_packs():
    packs = {}
    for p in sorted(glob.glob(PACK_GLOB)):
        slug = os.path.basename(p).split(".")[0]
        if slug == "_TEMPLATE":
            continue
        raw = extract_triggers(p)
        packs[slug] = {"raw": raw, "norm": {norm(w) for w in raw}}
    return packs


def route_query(packs, query):
    """按 style-router §2 第 0 步返回确定性显式风格路由结果。"""
    query_text = unicodedata.normalize("NFKC", str(query)).casefold()
    # 先按 (slug,规范化 trigger,query span) 折叠同包等价别名；同一个短词在
    # query 的独立位置必须保留，不能因为它也出现在另一处长词内部就被全局淘汰。
    occurrences = {}
    for slug, pdata in packs.items():
        for term in pdata["raw"]:
            nt = norm(term)
            pattern = trigger_pattern(term)
            if not nt or pattern is None:
                continue
            for match in pattern.finditer(query_text):
                pos, end = match.span()
                occurrences.setdefault(
                    (slug, nt, pos, end),
                    {"slug": slug, "term": term, "norm": nt, "start": pos, "end": end},
                )

    matches = list(occurrences.values())
    # 只有短命中的 query span 被同一位置的更长命中完整覆盖时才淘汰。不同位置
    # 的显式短词保留，例如“美式和美式学院融合”应留下两个 slug 并进入 hold。
    surviving_occurrences = [
        item for item in matches
        if not any(
            item["norm"] != other["norm"]
            and other["start"] <= item["start"]
            and item["end"] <= other["end"]
            for other in matches
        )
    ]
    # 同一 slug/规范化 trigger 即使在 query 重复出现，也只记一个显式 hit。
    longest = {}
    for item in sorted(
        surviving_occurrences,
        key=lambda x: (x["start"], x["end"], x["slug"], x["term"].casefold()),
    ):
        longest.setdefault((item["slug"], item["norm"]), item)
    longest = sorted(
        longest.values(),
        key=lambda item: (item["slug"], item["norm"], item["start"], item["term"].casefold()),
    )
    slugs = sorted({item["slug"] for item in longest})
    decision = "none" if not slugs else ("route" if len(slugs) == 1 else "hold")
    return {"decision": decision, "slugs": slugs, "matches": longest}


def score_rule_hits(packs, query, routed):
    """执行已纳入静态回归的最小评分契约;未覆盖完整 §5 推荐器。"""
    hits = []
    for slug in routed["slugs"]:
        matched_terms = sorted({m["term"] for m in routed["matches"] if m["slug"] == slug})
        hits.append({
            "slug": slug,
            "rule_id": "STYLE_EXPLICIT",
            "weight": 100,
            "matched_terms": matched_terms,
        })

    # 这些词故意不是 ecommerce-studio trigger;只有未显式命中该 pack 时才记用途分。
    if "ecommerce-studio" not in routed["slugs"]:
        use_terms = ["商品上架", "店铺首图", "白底商品照", "详情页展示"]
        matched_terms = [term for term in use_terms if trigger_pattern(term).search(
            unicodedata.normalize("NFKC", str(query)).casefold()
        )]
        if matched_terms:
            hits.append({
                "slug": "ecommerce-studio",
                "rule_id": "USE_ECOM_STUDIO",
                "weight": 20,
                "matched_terms": matched_terms,
            })
    return sorted(hits, key=lambda item: (item["slug"], item["rule_id"]))


def run_style_route_evals(packs):
    hard = []
    try:
        with open(STYLE_ROUTE_EVAL, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return 0, 0, [f"style-route eval 无法读取: {exc}"]
    if not isinstance(data, list):
        return 0, 0, ["style-route eval 顶层必须是 JSON list"]

    checked = score_checked = 0
    seen_ids = set()
    for entry in data:
        checked += 1
        if not isinstance(entry, dict):
            hard.append(f"style-route eval #{checked}: entry 必须是 object")
            continue
        eid = entry.get("id", f"#{checked}")
        if eid in seen_ids:
            hard.append(f"style-route eval id 重复: {eid}")
        seen_ids.add(eid)
        query = entry.get("query")
        expected = entry.get("expected")
        if not isinstance(query, str) or not isinstance(expected, dict):
            hard.append(f"{eid}: 必须含 string query 与 object expected")
            continue
        want_decision = expected.get("decision")
        want_slugs = expected.get("slugs")
        if want_decision not in {"route", "hold", "none"} or not isinstance(want_slugs, list):
            hard.append(f"{eid}: expected.decision 必须为 route/hold/none 且 expected.slugs 必须为 list")
            continue
        expected_slug_count = len(set(str(slug) for slug in want_slugs))
        if ((want_decision == "none" and expected_slug_count != 0)
                or (want_decision == "route" and expected_slug_count != 1)
                or (want_decision == "hold" and expected_slug_count < 2)):
            hard.append(f"{eid}: expected.decision={want_decision} 与 slugs={want_slugs} 数量不一致")
            continue
        got = route_query(packs, query)
        want_slugs = sorted(str(slug) for slug in want_slugs)
        mismatch = got["decision"] != want_decision or got["slugs"] != want_slugs
        want_count = expected.get("style_hit_count")
        if want_count is not None and (not isinstance(want_count, int) or len(got["matches"]) != want_count):
            mismatch = True
        want_rule_hits = expected.get("rule_hits")
        got_rule_hits = score_rule_hits(packs, query, got)
        if want_rule_hits is not None:
            score_checked += 1
            if not isinstance(want_rule_hits, list):
                hard.append(f"{eid}: expected.rule_hits 必须为 list")
                continue
            want_ledger = sorted(
                (str(hit.get("slug")), str(hit.get("rule_id")), hit.get("weight"))
                for hit in want_rule_hits if isinstance(hit, dict)
            )
            got_ledger = sorted(
                (hit["slug"], hit["rule_id"], hit["weight"])
                for hit in got_rule_hits
            )
            if len(want_ledger) != len(want_rule_hits) or got_ledger != want_ledger:
                mismatch = True
        if mismatch:
            terms = [f"{m['slug']}:{m['term']}" for m in got["matches"]]
            hard.append(
                f"{eid}: query={query!r} expected decision={want_decision},slugs={want_slugs},"
                f"style_hit_count={want_count!r}; got decision={got['decision']},slugs={got['slugs']},"
                f"style_hit_count={len(got['matches'])},matches={terms},rule_hits={got_rule_hits}"
            )
    return checked, score_checked, hard


def main(argv):
    packs = load_landed_packs()
    hard, info = [], []
    checked = 0
    iso_total = iso_asserted = style_conflict_checked = core_conflict_checked = 0
    style_target_checked = 0
    for ef in sorted(glob.glob(EVAL_GLOB, recursive=True)):
        try:
            data = json.load(open(ef, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and isinstance(data.get("evals"), list):
            data = data["evals"]
        elif not isinstance(data, list):
            continue
        style_eval_slug = None
        if os.path.basename(os.path.dirname(ef)) == "styles":
            candidate = os.path.basename(ef)[:-5]
            if candidate != "_TEMPLATE":
                style_eval_slug = candidate
        for entry in data:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") == "trigger-isolation":
                iso_total += 1
                if "assert_triggers" in entry:
                    iso_asserted += 1
            if entry.get("type") == "style-conflict":
                style_conflict_checked += 1
                eid = entry.get("id", "?")
                query = entry.get("input")
                if not isinstance(query, str):
                    hard.append(f"{eid}: style-conflict eval 必须含 string input")
                else:
                    got = route_query(packs, query)
                    if got["decision"] != "hold":
                        hard.append(
                            f"{eid}: style-conflict eval 必须真实命中≥2 个已落地 pack;"
                            f"got decision={got['decision']},slugs={got['slugs']}"
                        )
            if entry.get("category") == "style_conflict":
                core_conflict_checked += 1
                eid = entry.get("id", "?")
                query = entry.get("prompt")
                if not isinstance(query, str):
                    hard.append(f"core eval {eid}: category=style_conflict 必须含 string prompt")
                else:
                    got = route_query(packs, query)
                    if got["decision"] != "hold":
                        hard.append(
                            f"core eval {eid}: category=style_conflict 必须真实命中≥2 个已落地 pack;"
                            f"got decision={got['decision']},slugs={got['slugs']}"
                        )
            if style_eval_slug and entry.get("type") in {"happy-path", "style-routing"}:
                style_target_checked += 1
                eid = entry.get("id", "?")
                query = entry.get("input")
                if not isinstance(query, str):
                    hard.append(f"{eid}: {entry.get('type')} eval 必须含 string input")
                else:
                    got = route_query(packs, query)
                    if got["decision"] != "route" or got["slugs"] != [style_eval_slug]:
                        hard.append(
                            f"{eid}: {entry.get('type')} eval 必须唯一路由至所属 pack "
                            f"{style_eval_slug};got decision={got['decision']},slugs={got['slugs']}"
                        )
            at = entry.get("assert_triggers")
            if not isinstance(at, dict):
                continue
            eid = entry.get("id", "?")
            for slug, rules in at.items():
                if slug not in packs:
                    info.append(f"{eid}: pack '{slug}' 未落地,跳过(无 pack 文件可验)")
                    continue
                trig = packs[slug]["norm"]
                for t in rules.get("contains", []):
                    checked += 1
                    if norm(t) not in trig:
                        hard.append(f"{eid}: '{slug}' 应**含**触发词 «{t}»,实际不含")
                for t in rules.get("excludes", []):
                    checked += 1
                    if norm(t) in trig:
                        hard.append(f"{eid}: '{slug}' 应**排除**触发词 «{t}»,实际含(归属泄漏 = 触发隔离失效)")
    route_checked, score_checked, route_hard = run_style_route_evals(packs)
    hard.extend(route_hard)
    print("=== trigger-eval: 触发词归属 + query 路由断言检查 ===")
    print(f"落地 pack={len(packs)} ; 断言条数={checked} ; "
          f"trigger-isolation eval 带 assert_triggers={iso_asserted}/{iso_total} ; "
          f"style-route eval={route_checked} ; 评分账本断言={score_checked} ; "
          f"style happy/routing 目标断言={style_target_checked} ; "
          f"style-conflict 可执行断言={style_conflict_checked} ; "
          f"core style_conflict 断言={core_conflict_checked}")
    for h in hard:
        print(f"  [FAIL] {h}")
    for s in info:
        print(f"  [INFO] {s}")
    gap = iso_total - iso_asserted
    if gap > 0:
        print(f"  [INFO] {gap} 条 trigger-isolation eval 尚无 assert_triggers(建议补,纳入机械回归)")
    if not hard:
        print(
            f"  ✓ 全部 {checked} 条归属 + {route_checked} 条 query 路由 + "
            f"{score_checked} 条评分账本 + {style_target_checked} 条 style 目标 + "
            f"{style_conflict_checked} 条 style-conflict + {core_conflict_checked} 条 core conflict 断言成立"
        )
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
