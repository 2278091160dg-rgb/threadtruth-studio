# Single-style preview v2 — local verification

Date: 2026-09-13. Scope: T11 development collector, gallery template, public-evidence validation and current documentation. Implementation commits: `75c1b40`, `76f4def`, `3594c6d`. This is an unreleased local change, not a replacement for immutable beta.1 or beta.2 artifacts.

## Correct contract

One authorized white vest, 24 registered styles, one native six-pose sheet per style. Each entry binds its actual pack, runtime action-0 rules, exact prompt, source authorization, observed image metadata and separate six-pose human review. Whole-sheet thumbnails link to the same image without cropping or upscaling. Preview evidence never counts as six independent finals or a complete new workflow.

Historical four-board v1 records remain read-only and cannot be promoted or packaged as corrected previews. Runtime Skill/reference bytes are unchanged. No native image, real approval or public promotion was produced by this development task.

## Verification

- TDD first failed against the old schema (`1.0` instead of `2.0`). Synthetic success/refusal tests cover 24 unique styles and 144 canonical pose records, source/rule/pack/prompt drift, unique native calls and hashes, incomplete review, v1 refusal, whole-sheet projection and six-final isolation.
- Independent review initially found four functional issues and one stale instruction. Each is fixed: gallery approval revalidates live image bytes; display cannot enlarge sheets; repeated promotion validates/repairs public projections transactionally; full audit identifies unapproved styles; Growth uses the implemented template. Independent fault injection confirmed rollback for first and repeated promotion. Final task spec and quality verdicts: PASS, no open findings.
- Controller final repository suite: **95 tests passed**. Pack lint: **24/24 passed**, with three existing informational longest-match neighbors covered by regressions. Trigger regression: **132 ownership + 22 query + 3 score + 47 style-target + 13 style-conflict + 1 core-conflict assertions passed**.
- Official Plugin validation, system Skill validation, production source/runtime strict checks and eval/changelog checks passed. The current dated-unreleased heading was corrected for the governance parser; published changelog history was retained.
- JSON, YAML and Python source parsing, local Markdown link targets, public-tree/full reachable-history scanning and diff hygiene passed. Allowlist staging excludes local candidates, native receipts, review drafts and development tools/tests/evals. All 35 staged runtime files match source bytes.
- Actual headless Chromium 148.0.7778.96 rendered full gallery, scoped gallery and offline guide at 1440, 390 and 320 px. All nine variants passed overflow, image loading/aspect/no-enlargement where applicable, keyboard traversal, whole-sheet keyboard navigation, print-content visibility and no console/page errors or network requests. Screenshots use synthetic color fixtures, never public demo examples. This is a scoped render check, not a claim of exhaustive accessibility certification.
- An isolated installer test exercised actual beta.1 source registration, beta.2 backed-up replacement and beta.1 restoration. It did not activate Codex on a fresh host and does not count as an external lifecycle test.

## Remaining gates

Correct native previews: **generated 0/24, human-approved 0/24, public 0/24**. Accepted independent-final style coverage remains **1/24**, complete primary workflows **1/3**, consenting non-maintainer installers **0/5**, external lifecycle **0/1**, external-feedback patch **0/1**. The input packet is instructions, not evidence of completed external work.

Next native action is one separately authorized Korean Cold Editorial action-0 pilot. All six poses need source comparison and actual maintainer review; retries, other styles and publication retain their stated gates. Passing static checks does not establish visual quality, runtime maturity, external adoption, stable-release readiness or application acceptance. See [the task register](../WORK-STATUS.md) and [Beta acceptance packet](../BETA-ACCEPTANCE.md).
