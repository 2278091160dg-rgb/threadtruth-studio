# Preview Layout and Style Label Contract Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development; follow TDD, task review, and final verification. This file records the maintainer-approved scope from the conversation and is its implementation specification.

**Goal:** Close the demonstrated development-demo gaps before another native call: each of 24 same-white-vest sheets has one style, six canonical poses, 3:4 cells, a square board, readable style identification and unobstructive AI disclosure.

**Architecture:** Extend the existing offline preview collector and its release/rights consumers, not the runtime Skill. Separate measurable geometry from human visual attestations. Historical records remain intact and cannot inherit new acceptance.

**Tech stack:** existing Python standard library and Pillow, unittest, local static HTML; no new dependency, OCR service, image API or generated image in this implementation.

## Global Constraints

- Runtime `skills/threadtruth-studio/` stays byte-identical to starting HEAD. No global install, network probe, image generation/edit, human approval, media promotion, push, release or application submission.
- Same authorized four garment sources and adult female; accepted look-1 remains identity-only. One style per native sheet, six canonical poses in fixed top-row 1–3/bottom-row 4–6 order. Full-body framing for poses 1/2/4/6; half-body permitted for 3/5.
- Every pose cell is 3:4. Whole board is 1:1 with separate title/subtitle/footer whitespace. Exact square is machine-checked from native and retained JPEG metadata, never repaired with crop/stretch/padding.
- Text is generated natively with the image: full registered Chinese/English style name at top, `同款白马甲 · <mode> <Chinese mode name> · 六姿势预览` below it, and `AI生成 · 方向预览 · 非成片` plus the existing English preview-only disclosure in the footer. No label overlaps model, garment, shoes, bag or pose. Gallery also derives its heading from the registered style name.
- Registration is not acceptance. Agents never fill real human reviews; synthetic test reviews are explicitly fixtures. Missing/incorrect text, uncertain geometry, image-hash mismatch or overlap must block acceptance and promotion.
- Preserve original images, prompts and receipts. The known Korean C pilot is a generated attempt, not a qualified sheet: qualified0/24, approved0/24, public0/24. Its earlier narrow machine audit is historical, not new-layout compliance.
- Current published beta.1/beta.2 are immutable. No expansion to runtime-wide preview design, extra styles, external providers, auto-retry, or unattended image scheduling.

## Task 1: Enforce and test the layout/label evidence boundary

**Own:** `tools/style_preview.py`, a small dedicated development geometry/label helper if needed, `tests/test_style_preview.py`, and only release/rights consumers/tests directly affected by the contract. Do not edit runtime or docs in this task.

- [ ] Inspect current preparation, receipt binding, review validation, gallery and public release validation; record the shared interfaces before editing.
- [ ] Write regressions first. The old implementation must fail for accepting non-square native output, failing to require label/layout review, and allowing old-schema acceptance. Save actual RED output.
- [ ] New preparations use schema `3.0`. Add immutable `layout_contract` and `label_contract` to each planned preview, include them in exact prompts and existing receipt/review bindings. Do not mutate old runs to upgrade them.
- [ ] Layout contract records square board, 2 rows/3 columns, 3:4 cells, canonical framing, independent label bands. Prompt explicitly requests all of these and exact label text; keep source-first style filtering and original action0 mark semantics. Do not add contradictory global `no text` instructions.
- [ ] Add a human-review geometry section containing six ordered observed cell rectangles `[x,y,width,height]` in actual retained-image pixels, and observed title/subtitle/footer rectangles. Templates leave all rectangles unset and checks pending. These are observations, not automatically generated coordinates assumed to match the image.
- [ ] Validate finite integer coordinates (reject booleans), positive extents, bounds within actual image, no overlaps, actual row/column ordering/alignment and equal cell sizes (at most 1-pixel rounding). Require `abs(4*width-3*height) <= 4` for cells, allowing only one pixel of raster-edge rounding. Require title then subtitle wholly above both rows, footer below both rows, with distinct non-overlapping text bands. Never infer cells from board dimensions alone.
- [ ] Add explicit human checks for observed boundaries, correct full bilingual title, correct subtitle, correct/readable AI footer, no text-subject overlap, and full-body framing where required. Missing/pending/fail checks reject approval; real judgments remain human attestations, not OCR/object-detector claims. Human signs actual geometry/text checks against current image and evidence hash.
- [ ] Preserve native bytes before a square check can discard them: wrong-shape originals remain locally inspectable, never get a success claim, and cannot be approved/promoted. Do not overwrite prior native files or receipts. Prefer ingest retaining a rejected/awaiting-review candidate followed by audit failure to throwing away native evidence.
- [ ] Existing schema1/2 records are read-only history. Audit clearly reports noncompliance with current display standard; all mutations (prepare existing/ingest/approve/promote) reject old schema. Historical gallery remains available but always says legacy/not approved for current standard, never borrows old pass labels. Do not run current `_plan` equality checks on legacy records as if they were current.
- [ ] Selective audit can report metadata evidence without claiming human layout/text approval. Full approval/release validation requires all layout, label, six-pose and original rights gates. Preserve duplicate-call/hash, source/pack drift, atomic public projection, no-upscale and six-finals isolation protections.
- [ ] Test square board with bad cell geometry, out-of-bounds/overlap/reversed cells, inconsistent sizes, malformed numeric fields, missing/incorrect text attestation, missing framing, pending checks, hash-tampered image/review, old-schema direct promotion, and transactional promotion idempotence. Use actual synthetic rectangular layouts with known coordinates, not a self-mirroring contract assertion. Existing primary six-final tests remain green.
- [ ] Run focused tests while iterating; run full repository suite once before commit. Keep synthetic images out of real candidate/public directories. Self-review, commit only this task's files, and write report with RED/GREEN commands/results and limitations.

## Task 2: Synchronize operator docs and honest work status

**Own:** current preview guide, `docs/WORK-STATUS.md`, applicable README/Chinese/offline guide preview text, and source `CHANGELOG.md`. Preserve historical release notes. Wait for Task1 interface before final command examples, but inspect current docs in parallel.

- [ ] Explain whole-board1:1 versus per-cell3:4; titles/footer included in square, picture area is not itself the whole board. Explain exact native text and six-pose framing; no crop/enlargement or scripted text repair.
- [ ] Document new review JSON with clearly synthetic example coordinates, observed-boundary requirement, one-pixel rounding, explicit pending/approval distinction, v1/v2 historical-only treatment and new run ID creation.
- [ ] Work status before completion is10done/1rework/2in-progress/8pending; after verified software closure it becomes11done/2in-progress/8pending. Never add this documentation/test work to qualified-image counts. Keep attempt1, qualified0, approved0, public0; prior wrong mixed-style board separate.
- [ ] Next native gate is one corrected Korean C preview retry, not already authorized by this software plan. It must pass before 23 remaining styles; every4 is review checkpoint, not day limit. New native work requires initial24 calls if no retry fails (one corrected pilot +23); already-consumed pilot is separate, failures need additional authority.
- [ ] Preserve broader work: external lifecycle0/1, installers0/5, full primarycases1/3, external-feedback fix0/1; unchanged Beta origin and separate release/form authority. Do not imply static repair certifies the real image or the full project.
- [ ] Update changelog with user-discovered missing ratio/style label/overlap checks, before/after behavior, regressions and verification limitations. Avoid stale current-facing claims that v2 or old0attempt count is the current state.
- [ ] Run affected docs/contracts/link tests, commit docs, and submit task review.

## Task 3: Verify, prepare the gated retry packet and hand off

**Owner:** controller; independent final reviewer checks the combined current change and integration risks, without redoing completed unrelated work.

- [ ] Full tests,24pack lint, trigger regression, system Skill/Plugin checks, source/runtime standard, JSON/YAML/Python parsing, public-tree and history scan, safe release staging, unchanged runtime comparison.
- [ ] Render actual current and legacy galleries in isolated local Chromium at desktop/mobile widths; verify nonempty body, correct status/labels, no remote requests/errors, keyboard image links and no enlargement. Test fixtures do not count as real previews.
- [ ] Preserve existing actual pilot directory; prepare a new ignored run `white-vest-layout-v3` with24newprompts and zero images/reviews. Audit the original pilot read-only to show it does not pass current standard. Never synthesize missing coordinates or approvals for it.
- [ ] Save a concise verification report and update ignored handoff. Report local-only software done separately from actual image readiness. No native call until a new explicit Korean retry authorization; no publication.
- [ ] Any blocking review finding is fixed and re-reviewed before software completion; residual out-of-scope findings are documented with disposition. Keep worktree/old evidence available for the pending native/human/publication phases.
