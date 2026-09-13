# Single-style Preview Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and exhibit 24 native preview contact sheets of the same white vest, each containing ONE registered style and SIX canonical poses, then continue the evidence-backed Beta tasks.

**Architecture:** Reuse runtime action 0 unchanged. Replace only the development collector's wrong four-mixed-style abstraction with a versioned per-style evidence model, connect it to existing rights/style/release checks, and keep generation and human review outside scripts. Do not confuse this target with six independently generated final images.

**Tech Stack:** Existing Python standard library/Pillow development tooling, JSON records, Markdown/offline HTML, host-native image generation, existing tests and GitHub CI.

**Spec:** The maintainer's correction on 2026-09-13 is captured in [the canonical task register](../../WORK-STATUS.md), especially the corrected preview definition. Original action 0 is specified in `skills/threadtruth-studio/references/prompt-build.md` section 4.2. Earlier four-board execution instructions are superseded, not approval to generate the corrected collection.

## Global Constraints

- Target runtime: `skills/threadtruth-studio`; development evidence root: repository root. Runtime bytes remain unchanged for this correction.
- Same authorized source images 6/7/8/14, white hooded vest, adult female. Existing accepted look-1 is identity-only, never garment authority.
- Exactly 24 registered style slugs, one per native contact sheet. Each sheet uses pose templates 1–6 in row-major three-column/two-row order, not six different styles.
- Unknown or incompatible style details must not redesign clothing. Retain approved atmosphere-only translation for gendered/cultural tension styles.
- No script/API/fallback image generation. Each style is a separate explicitly authorized action-0 call; no hidden batch, extra retry or full-image generation.
- Keep `preview-grid` separate from `image-ready`. Public approval is a separate attestation, not a change into final-image status.
- No sub-image crop/upscale/removal of preview markings. A thumbnail is an aspect-preserving rendering of the whole sheet, linked to that same sheet.
- Keep beta.1/beta.2 assets and historical evidence immutable. No legacy four-board draft may be relabeled or counted as a v2 preview.
- No invented testers/feedback/recording/application. No global install, community post, publication or application submission without the relevant authority.
- Numeric progress, owners, target dates and dependencies are maintained in WORK-STATUS, not copied into runtime SKILL instructions.

## Task 1 — Replace the wrong development evidence model (T11)

**Files:** Modify `tools/style_preview.py`, its CLI wrapper, `tools/primary_demo.py`, `tests/test_style_preview.py` and `tests/test_build_release.py`; add a v2 preview schema alongside the historical v1 schema. Update current guide/index wording and source CHANGELOG in the same change.

**Interface decisions:** Keep prepare/ingest/audit/gallery/approve/promote operations and the existing run directory. A new run uses schema version 2.0 and `previews`: a list of 24 entries. Each entry owns `style`, one `pack` reference/hash, one `prompt_sha256`, six numbered `poses`, and eventually one native-output receipt, image metadata and human review. It must not put six style slugs on six cells. The CLI selector becomes `--style <registered-slug>`; `--board A/B/C/D` must fail clearly, not silently map to a style. Audit/gallery may inspect incomplete runs; promotion requires all 24 approved entries.

- [ ] Write a failing contract test in the existing PreviewTests harness:

```python
def test_prepare_builds_24_single_style_six_pose_previews(self):
    run = self.prepare()
    self.assertEqual(run['schema_version'], '2.0')
    self.assertEqual(len(run['previews']), 24)
    self.assertEqual(len({p['style'] for p in run['previews']}), 24)
    for preview in run['previews']:
        self.assertEqual([pose['ordinal'] for pose in preview['poses']], list(range(1, 7)))
        self.assertTrue(all('style' not in pose for pose in preview['poses']))
```

- [ ] Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_style_preview.py -v`; retain the expected failure against the old four-board model.
- [ ] Change preparation to load the actual registry/packs and the existing action-0 pose/head-gaze/negative rules. Each stored prompt names only its own style; source truth, canonical poses and readable preview mark remain explicit. Store the source rule/pack hashes so prompt regeneration cannot silently change evidence.
- [ ] Add `--style` selection to ingest, scoped audit and approval. Full audit reports missing/unapproved style IDs without pretending the collection is complete. Gallery renders ungenerated entries as text, not mock images. Only native image receipts with the exact submitted prompt hash can register generated evidence.
- [ ] Bind human review to each whole-sheet hash plus all six pose checks (product, pose/layout, identity/style, AI disclosure). Do not pre-fill real approval. Existing hash/source/pack drift, duplicate call/hash, unsafe path, overwrite and idempotence checks must remain. Full promotion requires 24 unique, approved styles and writes the public index atomically enough to leave no half-approved gallery.
- [ ] Reject legacy v1 records in the new promote path with a clear superseded-format error; retain historical read-only inspection. Do not migrate the rejected mixed-style output into a new single-style slot.
- [ ] Keep actual pixel metadata. Apply action-0 preview layout checks; do not inherit independent-final batch canvas rules or assert a native pixel size without observing it. Do not rely on divisibility by three to prove six-pose layout: layout/content require visual review. Never stretch an image to force acceptance.
- [ ] Add negative tests for six styles in one sheet, missing/duplicate pose IDs, reused native call/hash, missing source authorization, incomplete human review and preview-as-final promotion. Add a positive synthetic 24-sheet collection fixture with human attestations explicitly limited to tests. Verify the original six-final workflow still rejects five/seven images and any preview.
- [ ] Run the complete test suite, pack lint, trigger regressions, Plugin/Skill/governor checks and public scan. Obtain independent spec/quality review. Commit only development changes, with runtime byte parity verified. Do not publish a new Release here.

## Task 2 — One pilot, then 23 individual previews (T12)

**Inputs:** Validated Task 1 collector, authorized source photos, exact per-style prompt/pack and recorded mode. **Output:** 24 native contact sheets and receipts, not 144 separate photos.

- [ ] First request the explicit Korean Cold Editorial action-0 generation gate. Default mode is A (runtime recommends B/C/D); record the resolved mode before calling. Show the source recognition/route and preview-only intent, not a new style questionnaire.
- [ ] Generate only that one native preview. Save the original non-destructively, register its exact prompt/output hashes and actual dimensions, inspect all six poses, and show DENGGUI the whole sheet. If product/pose/layout fails, stop and seek a targeted retry authorization; do not regenerate merely because file copying failed.
- [ ] After pilot acceptance, process remaining styles one at a time through the same gate. Planning order: ecommerce-studio, clean-fit, nordic-minimal, athleisure, gorpcore; old-money, quiet-luxury, french-effortless, british-heritage, italian-luxe, preppy; american-street, y2k-millennium, workwear-vintage, cityboy, korean-menswear, office-commute-women; japanese-lifestyle, balletcore, coquette-ladylike, resort-vacation, neo-chinese, guochao-street.
- [ ] After each operation report style, generated/accepted counts, call count and visible limitations. Planned capacity is at most four styles per working day, not authorization for four unattended calls. Initial budget is 24 successful calls if there are no failures; the earlier wrong call and any retries are separate accounting.

## Task 3 — Human approval, whole-sheet gallery and beta.3 (T13)

**Interfaces:** Each style-index preview link must point to its own single-style contact sheet and optional full-sheet thumbnail, never to a tile in a shared mixed-style board. Rights records bind every native parent and any optimized whole-sheet derivative.

- [ ] Obtain actual maintainer six-pose review for each sheet, retaining the preview-only state and public-media consent. The accepted-final case's earlier sign-off does not approve new previews.
- [ ] Implement 24 bilingual cards/style pages with entire-sheet thumbnails, nonempty alt text, retained AI mark and clickable full preview. Do not create cropped single-pose thumbnails or inflate independent-final coverage from 1/24.
- [ ] Add tests proving 24 unique per-style preview parents, all 144 pose review entries, parent/derivative hash lineage and refusal of unapproved/misclassified media. Verify mobile/keyboard/offline/local links and build exclusion of local candidate images/receipts.
- [ ] When all24 pass, regenerate rights/style indexes and run full release gates. Obtain required release authority, publish beta.3 with new ZIP/checksum and truthful notes. Verify remote asset digest; retain beta.1/beta.2 intact and keep the Beta clock unchanged.

## Task 4 — In parallel: recipient and adoption evidence (T14–T19)

- [ ] Arrange one consenting non-maintainer clean environment; record host/build/OS/plugin versions and actual install, discovery, recognition-only first call, upgrade, uninstall and rollback. Keep private images/logs out of the public register.
- [ ] Capture the real workflow, redact account details and private content, and obtain publication approval. A checklist, mocked browser or synthetic narration is not a recording.
- [ ] Present concrete channel/message drafts to DENGGUI before posting. Use opt-in feedback to collect five deduplicated non-maintainer installations; do not use download or clone counters as people.
- [ ] Obtain two new product rights declarations for ecommerce-studio and american-street. Each needs separate test/final generation gates and a complete human-approved six-final workflow; white-vest previews and the Met auxiliary example do not count.
- [ ] Reproduce the first real external report, retain its regression and fix, and link the release to that feedback. Do not invent an issue to satisfy the milestone.
- [ ] Keep weekly snapshots in the existing ignored evidence directory, review aggregates before public entry, and re-triage public/private high-severity concerns before Beta exit. Never sum overlapping 14-day traffic windows.

## Task 5 — Stable release and application (T20–T21)

- [ ] Wait until at least 2026-10-13T04:59:28Z and all project exit criteria actually pass. If not, record the unmet IDs and extend Beta.
- [ ] Refresh policies, compatibility and all release checks; publish stable1.0.0 only after the evidence/authority gates. Digital signing is optional backlog unless separately requested; do not introduce key handling as a hidden prerequisite.
- [ ] Recheck the official application on submission day, use current public adoption/maintenance evidence and its current character limits, collect private account fields only for the form, show all answers to DENGGUI, and obtain final submission authorization. Submission is `applied`, not `accepted`.

## Scope check and current execution status

This is an execution schedule, not a background worker or permission escalation. Foundation T01–T10 is retained. Only the status audit and current-document/hand-off correction were performed while writing this plan; Tasks1–5 above still have their recorded gates. The corrected collector is **not implemented**, the correct collection is **0/24**, and no new images were generated during this planning/status task.
