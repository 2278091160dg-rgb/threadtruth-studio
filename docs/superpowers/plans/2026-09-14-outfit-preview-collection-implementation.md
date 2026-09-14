# Outfit 24-Style Preview Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second, rights-governed 24-style six-pose preview collection for one real coordinated outfit while preserving the released white-vest collection byte-for-byte and keeping generation, publication and release behind separate authorization gates.

**Architecture:** Keep the existing development-only `style_preview.py` pipeline and deterministic `preview_cards.py` compositor. Add explicit schema dispatch: public v4 is frozen and validated against a golden manifest; new mutable runs use v5 with a selected source case, batch authorization bindings and outfit-specific 24×6 human review. Public projection separates all collections from the sole white-vest representative mapping so the new outfit gallery never overwrites style-index evidence.

**Tech Stack:** Python 3 standard library, Pillow already used by the repository, JSON Schema documents, `unittest`, existing repository validators and release builder.

**Spec:** `docs/superpowers/specs/2026-09-14-outfit-preview-collection-design.md`

## Global Constraints

- Starting commit: `96736ee203b97519b94c1cf18b59e389d22963c2` on branch `docs/preview-task-schedule`.
- Source case ID: `beige-blazer-denim-outfit`; collection/run ID: `beige-blazer-denim-outfit-24-v1`.
- Original source SHA-256: `40163fcb0aeae44b1e9b690de9fec047bd517a0764260a4d3f1d014dbfc16d5a`.
- Media license: `ThreadTruth-Demo-Only-1.0`; never label this source or its generated/derived media Apache-2.0 or CC0.
- Runtime Skill behavior and the action-0/action-1 contract remain unchanged.
- Existing public `white-vest-24-v1` schema-v4 directory must remain byte-identical.
- New generation uses the current Codex native image-generation channel documented as `gpt-image-2` on 2026-09-14; evidence records `per_call_model: unavailable`.
- Four batches cover all 24 styles, with 1–6 ordered styles per batch, serial calls, no automatic retry and a new targeted authorization for every retry.
- No generation call, GitHub push, tag or Release is authorized by this implementation plan.
- Keep the implementation small: no service, database, API client, telemetry or new runtime dependency.

---

### Task 1: Freeze the Released v4 Collection

**Files:**
- Create: `tests/fixtures/white-vest-24-v1-beta3.sha256.json`
- Modify: `tools/style_preview.py`
- Modify: `tests/test_style_preview.py`

**Interfaces:**
- Produces: `validate_frozen_v4(root: Path, directory: Path, record: dict) -> None`.
- Produces: `FROZEN_PUBLIC_SCHEMA = "4.0"`, `CURRENT_SCHEMA = "5.0"`, and `HISTORICAL_SCHEMAS = {"1.0", "2.0", "3.0"}`.
- Consumes: the existing public directory `docs/demo/style-previews/white-vest-24-v1/`.

- [ ] **Step 1: Write the failing frozen-v4 tests**

Add tests that load the manifest, require every path/hash/byte count to match, and verify every mutation entry point refuses schema v4:

```python
def test_released_v4_collection_matches_golden_manifest(self):
    manifest = json.loads((ROOT / "tests/fixtures/white-vest-24-v1-beta3.sha256.json").read_text())
    public = ROOT / "docs/demo/style-previews/white-vest-24-v1"
    self.assertEqual(sorted(p.relative_to(public).as_posix() for p in public.rglob("*") if p.is_file()), sorted(manifest))
    for relative, expected in manifest.items():
        data = (public / relative).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), expected["sha256"])
        self.assertEqual(len(data), expected["bytes"])

def test_schema_v4_is_public_read_only_and_all_mutations_refuse_it(self):
    public = ROOT / "docs/demo/style-previews/white-vest-24-v1"
    record = json.loads((public / "evidence.json").read_text())
    self.assertEqual(record["schema_version"], "4.0")
    with self.assertRaisesRegex(ValueError, "schema 4.0 is frozen"):
        self.m.approve(ROOT, "white-vest-24-v1", record["previews"][0]["style"], {})
```

- [ ] **Step 2: Run the focused tests and confirm the new assertions fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview.PreviewTests.test_released_v4_collection_matches_golden_manifest tests.test_style_preview.PreviewTests.test_schema_v4_is_public_read_only_and_all_mutations_refuse_it -v`

Expected: FAIL because the golden manifest and schema dispatch do not exist.

- [ ] **Step 3: Generate and review the golden manifest once**

Use this calculation to produce the JSON object, inspect its stdout, then add those exact measured values with `apply_patch`:

```python
public = Path("docs/demo/style-previews/white-vest-24-v1")
manifest = {
    path.relative_to(public).as_posix(): {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": len(path.read_bytes()),
    }
    for path in sorted(public.rglob("*"))
    if path.is_file()
}
print(json.dumps(manifest, indent=2, sort_keys=True))
```

The committed file must contain every current regular file under the v4 directory. Do not write a manifest inside the frozen directory.

- [ ] **Step 4: Add explicit read-only v4 validation and mutation refusal**

Implement dispatch without regenerating v4 from the new v5 planner:

```python
HISTORICAL_SCHEMAS = {"1.0", "2.0", "3.0"}
FROZEN_PUBLIC_SCHEMA = "4.0"
CURRENT_SCHEMA = "5.0"

def _require_mutable_v5(record):
    schema = record.get("schema_version")
    if schema == FROZEN_PUBLIC_SCHEMA:
        raise ValueError("preview schema 4.0 is frozen public evidence; mutation is forbidden")
    if schema in HISTORICAL_SCHEMAS:
        raise ValueError(_legacy_error(schema))
    if schema != CURRENT_SCHEMA:
        raise ValueError("unsupported preview schema")
```

`validate_frozen_v4` must verify the golden manifest, validate the checked-in record/assets with the existing v4 structural rules, and never call `_plan_v5`.

- [ ] **Step 5: Run the focused tests and commit**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview -v`

Expected: all preview tests PASS.

Commit:

```bash
git add tools/style_preview.py tests/test_style_preview.py tests/fixtures/white-vest-24-v1-beta3.sha256.json
git commit -m "test(previews): freeze beta3 white vest evidence"
```

### Task 2: Add the Demo-Only Outfit Source Case

**Files:**
- Create: `docs/demo/preview-source-v1.schema.json`
- Create: `docs/demo/preview-sources/beige-blazer-denim-outfit/source.jpg`
- Create: `docs/demo/preview-sources/beige-blazer-denim-outfit/rights.json`
- Create: `docs/demo/preview-sources/beige-blazer-denim-outfit/README.md`
- Modify: `tools/demo_media.py`
- Modify: `tests/test_demo_media.py`
- Modify: `tests/test_repository_contract.py`

**Interfaces:**
- Produces: `validate_preview_sources(root: Path) -> list[str]`.
- Produces: a validated source record consumed by Task 3 through `load_preview_source(root, case_id)`.

- [ ] **Step 1: Write failing source-case tests**

Assert exactly one controlled preview source directory, JPEG metadata integrity, original-to-public derivation and license text:

```python
def test_outfit_preview_source_is_demo_only_and_hash_bound(self):
    rights = json.loads((ROOT / "docs/demo/preview-sources/beige-blazer-denim-outfit/rights.json").read_text())
    self.assertEqual(rights["schema_version"], "1.0")
    self.assertEqual(rights["case_id"], "beige-blazer-denim-outfit")
    self.assertEqual(rights["license"]["id"], "ThreadTruth-Demo-Only-1.0")
    self.assertEqual(rights["original"]["sha256"], "40163fcb0aeae44b1e9b690de9fec047bd517a0764260a4d3f1d014dbfc16d5a")
    self.assertNotIn("CC0", json.dumps(rights))
    self.assertEqual(demo_media.validate_preview_sources(ROOT), [])
```

Add tampering tests for a changed JPEG hash, wrong license ID, absolute path, missing outfit fact and unregistered sibling file.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_demo_media tests.test_repository_contract -v`

Expected: FAIL because the source schema/directory and validator are absent.

- [ ] **Step 3: Add the schema and optimized source**

Generate `source.jpg` from `maintainer-provided-source-attachment` without altering content or aspect ratio, then construct the rights record from measured bytes:

```python
source_jpg = root / "docs/demo/preview-sources/beige-blazer-denim-outfit/source.jpg"
public_data = source_jpg.read_bytes()
record = {
    "schema_version": "1.0",
    "case_id": "beige-blazer-denim-outfit",
    "status": "approved-for-preview",
    "license": {
        "id": "ThreadTruth-Demo-Only-1.0",
        "scope": "Display and distribution only as part of ThreadTruth Studio repository and releases; no standalone reuse, resale, relicensing or CC0 dedication.",
    },
    "original": {
        "sha256": "40163fcb0aeae44b1e9b690de9fec047bd517a0764260a4d3f1d014dbfc16d5a",
        "width": 1086,
        "height": 1448,
        "mime": "image/png",
    },
    "public_asset": {
        "path": "source.jpg",
        "sha256": hashlib.sha256(public_data).hexdigest(),
        "bytes": len(public_data),
        "width": 1086,
        "height": 1448,
        "mime": "image/jpeg",
        "derivation": "EXIF-transposed RGB JPEG transcode; metadata removed",
    },
    "outfit": {
        "name_en": "Beige blazer and dark-denim outfit",
        "name_zh": "米色西装与深色牛仔套装",
        "core_items": ["beige single-breasted notched-lapel blazer", "white crew-neck top", "dark indigo straight-leg jeans", "olive structured tote", "dark-brown loafers"],
        "optional_when_visible": ["watch", "restrained gold jewelry"],
        "forbidden": ["brand invention", "logo invention", "text invention", "replacement garment"],
    },
}
```

- [ ] **Step 4: Extend the public demo allowlist and validator**

Add `preview-source-v1.schema.json` to `DEMO_ROOT_FILES`, `preview-sources` to `DEMO_ROOT_DIRS`, and call `validate_preview_sources` from `validate_public_cases`. Reject symlinks, unknown files/directories, non-JPEG public assets, mismatched dimensions/hashes, wrong license, unsafe text and any case ID outside the explicit source allowlist.

- [ ] **Step 5: Run focused tests and commit**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_demo_media tests.test_repository_contract -v`

Expected: PASS.

Commit:

```bash
git add docs/demo/preview-source-v1.schema.json docs/demo/preview-sources tools/demo_media.py tests/test_demo_media.py tests/test_repository_contract.py
git commit -m "feat(demo): register demo-only outfit source"
```

### Task 3: Implement Independent Schema-v5 Planning

**Files:**
- Create: `docs/demo/style-preview-v5.schema.json`
- Modify: `tools/style_preview.py`
- Modify: `tools/style-preview.py`
- Modify: `tests/test_style_preview.py`

**Interfaces:**
- Produces: `load_preview_source(root: Path, case_id: str) -> tuple[dict, dict | None]`.
- Produces: `_plan_v5(root: Path, run_id: str, source_case: str) -> dict`.
- Changes: `prepare(root, run_id, source_case)` requires `source_case` for new v5 runs.
- CLI: `python3 tools/style-preview.py prepare --run-id beige-blazer-denim-outfit-24-v1 --source-case beige-blazer-denim-outfit`.

- [ ] **Step 1: Write failing v5 planner tests**

Assert variable source counts, selected source binding, outfit prompt facts and identity-only anchor separation:

```python
def test_v5_outfit_plan_binds_one_source_and_every_outfit_fact(self):
    run = self.m.prepare(self.root, "outfit-run", "beige-blazer-denim-outfit")
    self.assertEqual(run["schema_version"], "5.0")
    self.assertEqual(run["source"]["case_id"], "beige-blazer-denim-outfit")
    self.assertEqual(len(run["source"]["assets"]), 1)
    for preview in run["previews"]:
        prompt = (self.m.run_dir(self.root, "outfit-run") / "prompts" / f"{preview['style']}.txt").read_text()
        for fact in run["source"]["outfit"]["core_items"]:
            self.assertIn(fact, prompt)
        self.assertIn("complete coordinated outfit", prompt)
        self.assertNotIn("same one white hooded puffer vest", prompt)
```

Also test missing `--source-case`, unknown cases, source hash drift, and schema-v5 validation independent from v4.

- [ ] **Step 2: Run focused planner tests and confirm failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview -v`

Expected: FAIL on the new v5 expectations.

- [ ] **Step 3: Parameterize only source-dependent prompt fields**

Use a source contract with `case_id`, `rights_ref`, `rights_sha256`, `assets`, `outfit`, `subtitle`, and optional `identity_anchor`. For this source set:

```python
source = {
    "case_id": "beige-blazer-denim-outfit",
    "rights_ref": "docs/demo/preview-sources/beige-blazer-denim-outfit/rights.json",
    "assets": [{"path": "docs/demo/preview-sources/beige-blazer-denim-outfit/source.jpg", "role": "outfit-source", "sha256": public_sha256}],
    "subtitle": "同款完整套装",
    "outfit": rights["outfit"],
}
```

The prompt must identify attached source images by their actual count, repeat all core facts, say that the complete outfit remains visible in all six cells, and state that style may change only mood/background/lighting/pose treatment. It must never infer or invent a brand.

- [ ] **Step 4: Dispatch public validation by schema**

`validate_public_previews` must call `validate_frozen_v4` for `4.0`, `_validate_public_v5` for `5.0`, and reject `1.0`–`3.0`. Every mutation command calls `_require_mutable_v5` before writing.

- [ ] **Step 5: Run preview tests and commit**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview -v`

Expected: PASS, including unchanged public v4 validation.

Commit:

```bash
git add docs/demo/style-preview-v5.schema.json tools/style_preview.py tools/style-preview.py tests/test_style_preview.py
git commit -m "feat(previews): add source-selected schema v5 plans"
```

### Task 4: Bind Four Immutable Authorization Batches

**Files:**
- Modify: `tools/style_preview.py`
- Modify: `tools/style-preview.py`
- Modify: `docs/demo/style-preview-v5.schema.json`
- Modify: `tests/test_style_preview.py`

**Interfaces:**
- Produces: `register_batch(root: Path, run_id: str, manifest: dict) -> dict`.
- CLI example: `python3 tools/style-preview.py register-batch --run-id beige-blazer-denim-outfit-24-v1 --manifest /tmp/outfit-batch-01.json`.
- Changes v5 generation record to include `batch_id`, `authorization_sha256`, `model_docs_url`, `model_docs_verified_at`, and `per_call_model`.

- [ ] **Step 1: Write failing batch and generation-binding tests**

Use this exact manifest contract:

```python
manifest = {
    "schema_version": "1.0",
    "batch_id": "outfit-batch-01",
    "run_id": "outfit-run",
    "styles": [p["style"] for p in run["previews"][:6]],
    "maximum_calls": 6,
    "authorization_sha256": "a" * 64,
    "authorized_at": "2026-09-14T08:00:00Z",
    "scope": "serial-native-generation;no-auto-retry",
}
```

Tests must reject an overlapping style, reordered/tampered manifest, more than six styles, a fifth batch, missing authorization hash, generation for a style outside its batch, wrong authorization hash, a second call without correction authorization and any call after `maximum_calls` is consumed.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview -v`

Expected: FAIL because batch registration/binding is absent.

- [ ] **Step 3: Implement immutable local batch registration**

Write manifests under `.threadtruth/style-previews/{run_id}/batches/{batch_id}.json` using `_atomic_json`. A repeated identical registration is idempotent; any byte-level semantic difference refuses overwrite. The union of four registered batches must equal the ordered 24-style plan before promotion.

- [ ] **Step 4: Extend v5 generation and correction evidence**

Accept this model disclosure exactly, with hashes read from the planned preview and registered manifest:

```python
generation = {
    "tool": "native-imagegen",
    "call_id": None,
    "generated_at": "2026-09-14T08:10:00Z",
    "prompt_sha256": preview["prompt_sha256"],
    "batch_id": manifest["batch_id"],
    "authorization_sha256": manifest["authorization_sha256"],
    "model_docs_url": "https://learn.chatgpt.com/docs/image-generation",
    "model_docs_verified_at": "2026-09-14",
    "per_call_model": "unavailable",
}
```

Allow `call_id` to be null when the host does not expose it. Duplicate detection still applies to non-null IDs and every native/output hash. A retry remains invalid unless the existing targeted-correction record also binds a new authorization hash and the full replaced-call/image chain.

- [ ] **Step 5: Run tests and commit**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview -v`

Expected: PASS.

Commit:

```bash
git add tools/style_preview.py tools/style-preview.py docs/demo/style-preview-v5.schema.json tests/test_style_preview.py
git commit -m "feat(previews): bind generation to immutable batches"
```

### Task 5: Enforce Outfit-Specific 24×6 Human QA

**Files:**
- Modify: `tools/style_preview.py`
- Modify: `docs/demo/style-preview-v5.schema.json`
- Modify: `tests/test_style_preview.py`

**Interfaces:**
- Produces: `outfit_review_template(record: dict, style: str) -> dict`.
- Changes: `_check_review` dispatches by the source record's `review_contract`.

- [ ] **Step 1: Write failing outfit review tests**

Require every one of six cells to include:

```python
expected_cell = {
    "ordinal": 1,
    "core_items": {
        "blazer": "pass",
        "top": "pass",
        "jeans": "pass",
        "tote": "pass",
        "loafers": "pass"
    },
    "optional_items": {
        "watch": "not-visible-no-contradiction",
        "jewelry": "not-visible-no-contradiction"
    },
    "complete_outfit_visible": "pass",
    "adult_identity": "pass",
    "anatomy": "pass",
    "pose_layout": "pass",
    "registered_style_distinct": "pass",
    "ai_disclosure": "pass",
    "framing": "pass"
}
```

For each core item, test missing, `pending`, `fail`, and `not-visible-no-contradiction` are rejected. Optional items allow only `pass` or `not-visible-no-contradiction`. Test that a 23-sheet approval cannot promote and that a changed display/native/review hash invalidates approval.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview -v`

Expected: FAIL because v5 still uses the single-garment review shape.

- [ ] **Step 3: Implement the minimal review dispatch**

Keep the existing v4 review validator private to frozen validation. For v5, derive stable item keys from the source record (`blazer`, `top`, `jeans`, `tote`, `loafers`, `watch`, `jewelry`) and require six exact ordinal records. Machine composition remains `geometry_scope: deterministic-display-cards-only`; it cannot fill or approve these visual fields.

- [ ] **Step 4: Run tests and commit**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview -v`

Expected: PASS.

Commit:

```bash
git add tools/style_preview.py docs/demo/style-preview-v5.schema.json tests/test_style_preview.py
git commit -m "feat(previews): require cell-level outfit QA"
```

### Task 6: Support Multiple Collections Without Replacing Representatives

**Files:**
- Modify: `tools/style_preview.py`
- Modify: `tools/primary_demo.py`
- Modify: `tests/test_style_preview.py`
- Modify: `tests/test_primary_demo.py`

**Interfaces:**
- Produces: `all_preview_collections(root: Path) -> dict[str, dict]`.
- Produces: `representative_preview_links(root: Path) -> dict[str, dict]`.
- Constant: `REPRESENTATIVE_COLLECTION_ID = "white-vest-24-v1"`.
- Removes internal use of ambiguous `preview_links`; callers use one of the two explicit interfaces.

- [ ] **Step 1: Write failing multi-collection tests**

Create synthetic approved v4/v5 collection fixtures and assert:

```python
collections = self.m.all_preview_collections(self.root)
self.assertEqual(set(collections), {"white-vest-24-v1", "beige-blazer-denim-outfit-24-v1"})
links = self.m.representative_preview_links(self.root)
self.assertEqual({link["run_id"] for link in links.values()}, {"white-vest-24-v1"})
```

Also assert the same 24 style slugs can exist across collections, duplicate collection IDs fail closed, and style-index/style pages remain byte-identical when only the outfit collection is promoted.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview tests.test_primary_demo -v`

Expected: FAIL because current `preview_links` rejects repeated style slugs.

- [ ] **Step 3: Implement explicit collection and representative projections**

`all_preview_collections` validates every directory and returns collection metadata keyed by `run_id`. `representative_preview_links` selects only `white-vest-24-v1` and returns its 24 style links. Update `validate_style_index`, style-page rendering and README style-grid rendering to consume only the representative mapping.

- [ ] **Step 4: Make outfit promotion transactional without projecting style pages**

When promoting v5, write only its public collection directory, collection gallery and rights index. Do not mutate `docs/demo/style-index.json` or `docs/demo/styles/*.md`. If any validation fails, remove the staged outfit directory and restore all tracked projections.

- [ ] **Step 5: Run tests and commit**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview tests.test_primary_demo -v`

Expected: PASS.

Commit:

```bash
git add tools/style_preview.py tools/primary_demo.py tests/test_style_preview.py tests/test_primary_demo.py
git commit -m "feat(previews): separate collections from representatives"
```

### Task 7: Add Bilingual Gallery, Rights Index and Release Gates

**Files:**
- Modify: `tools/style_preview.py`
- Modify: `tools/primary_demo.py`
- Modify: `tools/demo_media.py`
- Modify: `tools/build-release.py`
- Modify: `tests/test_style_preview.py`
- Modify: `tests/test_primary_demo.py`
- Modify: `tests/test_build_release.py`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `docs/demo/README.md`
- Modify: `docs/demo/MEDIA-POLICY.md`
- Modify: `docs/demo/RIGHTS.md` only through the renderer

**Interfaces:**
- Produces one bilingual outfit collection `index.html` and one collection `README.md` after promotion.
- Adds the source, native sheets, display boards and thumbnails to the generated rights index with `ThreadTruth-Demo-Only-1.0`.
- Release validation accepts zero or one approved outfit collection and requires exactly 72 registered JPEG preview assets when it exists.

- [ ] **Step 1: Write failing presentation and release tests**

Tests must assert:

```python
self.assertIn("single garment · 24 styles", (ROOT / "README.md").read_text())
self.assertIn("coordinated outfit · 24 styles", (ROOT / "README.md").read_text())
self.assertIn("单件服饰 · 24种风格", (ROOT / "README.zh-CN.md").read_text())
self.assertIn("完整套装 · 24种风格", (ROOT / "README.zh-CN.md").read_text())
```

The generated outfit gallery must contain the source image, 24 whole-sheet thumbnails, 24 full display links, the model-doc URL, verification date, demo-only notice and limitations. It must contain no remote image/script/font resources and no absolute path. Release tests must preserve 72 white-vest JPEG hashes and reject outfit collections with 71/73 JPEGs, missing source rights, an unapproved style, CC0 wording, receipt/candidate files, or a preview recorded as a final.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview tests.test_primary_demo tests.test_build_release -v`

Expected: FAIL on new gallery, rights and release assertions.

- [ ] **Step 3: Render the dedicated collection presentation**

Use local relative links only. The public copy must say both:

```text
AI-generated · locally composed direction preview · not final imagery
AI生成 · 排版衍生方向预览 · 非成片
```

The repository home pages describe the two examples as demonstrations, not proof of universal apparel coverage. Add accurate host wording: ChatGPT plugin picker or `@threadtruth-studio`; supported Codex skill picker or `$threadtruth-studio`; Codex CLI `/skills`. Explicitly say the project is not claiming official marketplace listing.

- [ ] **Step 4: Extend rights and release validation**

Rights rows for this collection use `ThreadTruth-Demo-Only-1.0` for source/native/display/thumbnail assets. The release validator must inspect the frozen v4 golden manifest, v5 evidence approval, 72 v5 JPEGs, the separate source record and absence of `.threadtruth`, native receipts, layouts, absolute paths and review drafts.

- [ ] **Step 5: Run the focused suite and commit**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_style_preview tests.test_primary_demo tests.test_build_release -v`

Expected: PASS.

Commit:

```bash
git add tools/style_preview.py tools/primary_demo.py tools/demo_media.py tools/build-release.py tests README.md README.zh-CN.md docs/demo
git commit -m "feat(demo): present governed outfit preview collection"
```

### Task 8: Complete Static Verification and Stop at the Generation Gate

**Files:**
- Modify only if a test reveals a scoped defect: files already named in Tasks 1–7.
- Do not modify: `skills/threadtruth-studio/` unless a pre-existing regression is proven; the design requires runtime behavior unchanged.

**Interfaces:**
- Produces: a clean implementation branch ready for four separately authorized native-generation batches.

- [ ] **Step 1: Run the full repository suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 tools/pack-lint.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/trigger-eval.py
PYTHONDONTWRITEBYTECODE=1 python3 <skill-creator-dir>/scripts/quick_validate.py skills/threadtruth-studio
PYTHONDONTWRITEBYTECODE=1 python3 <production-governor-dir>/scripts/quick_validate.py skills/threadtruth-studio
PYTHONDONTWRITEBYTECODE=1 python3 <production-governor-dir>/scripts/check_skill_standard.py skills/threadtruth-studio --evidence-dir . --strict
PYTHONDONTWRITEBYTECODE=1 python3 <production-governor-dir>/scripts/check_skill_standard.py skills/threadtruth-studio --profile runtime --strict
PYTHONDONTWRITEBYTECODE=1 python3 tools/public-scan.py --root .
git diff --check
```

Expected: every command exits 0; pack lint reports 24/24.

- [ ] **Step 2: Build and inspect the current beta.3 archive**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 tools/build-release.py --root . --output /tmp/threadtruth-outfit-preflight`

Inspect the ZIP and assert it includes the new schemas/source documentation, retains the exact beta.3 white-vest assets, and excludes `.threadtruth/`, test fixtures, receipts, layouts, absolute paths and the original PNG attachment.

- [ ] **Step 3: Prepare the v5 run but do not register fake authorization**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/style-preview.py --root . prepare --run-id beige-blazer-denim-outfit-24-v1 --source-case beige-blazer-denim-outfit
PYTHONDONTWRITEBYTECODE=1 python3 tools/style-preview.py --root . gallery --run-id beige-blazer-denim-outfit-24-v1
```

Expected: 24 prompt files and a local review gallery exist under ignored `.threadtruth/`; no batch, image, approval or public outfit collection exists.

- [ ] **Step 4: Verify branch cleanliness and commit any test-only scoped fixes**

Run: `git status --short`, `git log --oneline 96736ee..HEAD`, and `git diff --check`.

Expected: tracked worktree clean, with small reviewable commits from Tasks 1–7.

- [ ] **Step 5: Stop and report the exact authorization request**

Report 0/24 generated, 0/24 approved and 0/24 public. Present the four ordered style lists and request explicit authorization containing all four batch IDs, maximum six calls per batch, serial execution and no automatic retry. Do not invoke image generation in this task without that new authorization.

### Task 9: Authorized Generation, Human Approval and Beta.4 Release Gates

**Files:**
- Local evidence first: `.threadtruth/style-previews/beige-blazer-denim-outfit-24-v1/`
- Public after 24/24 approval: `docs/demo/style-previews/beige-blazer-denim-outfit-24-v1/`
- Modify after approval: `.codex-plugin/plugin.json`, `CHANGELOG.md`, `RELEASE.md`, `README.md`, `README.zh-CN.md`, generated demo indexes.

**Interfaces:**
- Consumes: explicit batch authorizations, native image outputs, maintainer-completed 24×6 reviews and separate publication authorization.
- Produces: a verified beta.4 commit and, only after separate authorization, GitHub tag/Release assets.

- [ ] **Step 1: Register only explicitly authorized batches**

Create each manifest from the user authorization hash and timestamp. Verify the four immutable manifests cover the ordered 24 styles exactly once before the first call.

- [ ] **Step 2: Generate serially and ingest one result per style**

For each authorized style: invoke the current Codex native image-generation channel once, record the actual prompt hash/time/call ID if exposed, ingest the native image, measure six panel rectangles, and compose the 1200×1200 board. On failure, retain evidence and stop only the affected batch; never retry automatically.

- [ ] **Step 3: Obtain maintainer review for every sheet and cell**

Provide each composed board plus its source image and structured review template. Record only the maintainer's explicit decisions. Promotion remains blocked until 24 sheets and all 144 cells pass core outfit, adult identity, anatomy, pose, style, disclosure and framing checks.

- [ ] **Step 4: Request and consume separate publication authorization**

After 24/24 approval, show the exact public file set and rights language. Only then run `promote`; verify the white-vest style-index representative links remain unchanged and the outfit appears only in its dedicated gallery/homepage demonstration.

- [ ] **Step 5: Prepare beta.4 without pushing**

Bump the plugin version from `1.0.0-beta.3` to `1.0.0-beta.4`, add an accurate changelog entry, run every Task 8 validation, build ZIP/checksum and inspect archive contents. Read and apply the production governor instructions before claiming release readiness.

- [ ] **Step 6: Request separate GitHub authorization**

Present the release commit, tag, ZIP path, checksum path, validation summary and known limitations. Push, tag and create the GitHub Release only after the user explicitly authorizes those exact external mutations.

## Self-Review Result

- Spec coverage: source rights, v4 immutability, v5 dispatch, batch authorization, model disclosure, outfit QA, multi-collection projection, bilingual gallery, release checks and external gates each map to a task.
- Placeholder scan: no `TBD`, `TODO`, dummy hash or unspecified implementation step remains; measured hashes are calculated from named inputs and authorization values are consumed only after their explicit gate.
- Type consistency: `load_preview_source`, `_plan_v5`, `register_batch`, `all_preview_collections`, `representative_preview_links` and `validate_preview_sources` retain the same names and roles throughout the plan.
- Scope boundary: Tasks 1–8 contain no image-generation or publication authority; Task 9 is explicitly gated.
