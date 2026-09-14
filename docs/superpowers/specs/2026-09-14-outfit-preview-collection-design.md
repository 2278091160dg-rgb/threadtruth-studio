# Outfit 24-style preview collection design

Date: 2026-09-14

Status: revised after independent audit; written review pending

Scope: development evidence and public demo only; runtime generation behavior stays unchanged

## Outcome

Add a second public 24-style preview collection showing that ThreadTruth Studio can preserve a coordinated physical outfit, not only one garment. The existing white-vest collection remains intact. The new collection uses one authorized source image and produces one six-pose action-0 sheet for each of the 24 registered styles.

## Source contract

- Case slug: `beige-blazer-denim-outfit-24-v1`.
- The public source is the supplied 3:4 flat-lay image, SHA-256 `40163fcb0aeae44b1e9b690de9fec047bd517a0764260a4d3f1d014dbfc16d5a`.
- Maintainer attestation: the image shows a real physical outfit, is not a pure AI concept image, and the project has sufficient rights to use the image and depicted apparel, footwear, bag and accessories for generation and public GitHub demonstration.
- License scope: `ThreadTruth-Demo-Only-1.0`. Rights remain with their respective holders. The source and this collection's generated/derived media may be displayed and distributed as part of ThreadTruth Studio's repository and releases, but no standalone reuse, resale, relicensing or CC0 dedication is granted. The notice does not waive trademark, privacy, personality or cultural rights.
- Outfit truth: beige single-breasted blazer with notched lapels, white crew-neck top, dark indigo straight-leg jeans, olive structured tote, dark-brown loafers, watch and restrained gold jewelry. Prompts must not invent brands, logos, text or replacement garments.
- The accepted white-vest `look-1` may be supplied as identity-only guidance for one adult female model. It cannot override any outfit fact.

## Minimal implementation

1. Add one controlled public source case at `docs/demo/preview-sources/beige-blazer-denim-outfit/`, containing the optimized source image, structured rights record and concise README. Add `preview-source-v1.schema.json` and admit only this validated directory type through the existing demo allowlist.
2. Extend `tools/style_preview.py` with a required source-case selector for new schema-v5 runs. Version dispatch is explicit: v1–v3 remain historical and forbidden from public promotion; v4 receives a frozen public read-only validator and every mutation command rejects it; v5 has an independent plan and validator. A golden file/hash manifest proves that the released white-vest v4 directory remains byte-identical.
3. Parameterize only the currently hard-coded values: source files, rights record, outfit name/facts, source count, label subtitle and identity anchor. Do not add a service, database, API client or new runtime dependency.
4. Separate `all_preview_collections()` from `representative_preview_links()`. Set the sole `representative_collection_id` to `white-vest-24-v1`; allow the same style in different collections while rejecting duplicate collection IDs. Existing style-index entries and individual style pages continue to use the white-vest representative. The outfit collection appears only in its dedicated bilingual gallery and repository home page.
5. Add host-specific invocation wording without claiming one syntax works everywhere: ChatGPT can use the plugin picker or `@threadtruth-studio`; supported Codex surfaces can use the skill picker or `$threadtruth-studio`, and Codex CLI can inspect `/skills`. Do not claim official marketplace listing.

## Generation and evidence flow

- Use the installed ThreadTruth Studio Plugin in the current Codex host and the native image-generation capability documented as `gpt-image-2` on 2026-09-14.
- Prepare all 24 prompts from the registered style packs. Each prompt applies exactly one style to the same complete outfit and requests one 2×3 six-pose action-0 preview sheet.
- Before generation, create four immutable batch manifests. Each has a unique batch ID, an ordered list of one to six styles, maximum call count, authorization-text hash, authorization time and the explicit `no_auto_retry` scope. Public evidence stores only the authorization hash and non-sensitive scope; the user-authored text remains private conversation evidence.
- Run only a separately authorized batch. Calls are serial, and every generation record binds the batch ID and authorization hash. A failed sheet reaches a retained failure state; any retry requires a new targeted authorization and records the complete replaced-call chain.
- For every call, retain the actual prompt hash, call identifier when exposed, generation time, native image hash and observed dimensions. The collection records the official model-documentation URL and verification date with `per_call_model=unavailable`; it does not pretend the host returned a per-call model ID.
- Apply the existing deterministic 1200×1200 display composition after generation: six 360×480 (3:4) card frames, no stretching, no upscaling and no subject/garment cropping. Local labels provide the exact bilingual style name and the disclosure `AI生成 · 排版衍生预览 · 非成片`.
- Machine audit cannot approve visual fidelity. The v5 review binds the structured outfit facts and evaluates all 24×6 cells. Blazer, top, jeans, tote and loafers must not be replaced or contradicted; the intended complete outfit must remain visible in every cell. Watch and jewelry are checked when visible and may be recorded as `not-visible-no-contradiction`, rather than forcing invented detail. Every sheet also requires one adult model identity, usable anatomy, distinguishable registered style and unobstructed disclosure. Any failed core item blocks promotion.

## Public presentation

- Add a dedicated outfit collection page with the authorized source, 24 whole-sheet thumbnails, links to each complete display board, generation-model disclosure and limitations.
- Update English and Chinese README pages to present two distinct public demonstrations: `single garment · 24 styles` and `coordinated outfit · 24 styles`. Do not generalize two examples into proof that every garment or outfit is already covered.
- Register the original PNG hash, optimized public source hash/dimensions/MIME, metadata-removal/transcode derivation, native sheets, display derivatives and thumbnails in the generated rights index. Every item in this collection carries `ThreadTruth-Demo-Only-1.0`; Apache-2.0 and CC0 do not cover it.
- Keep all previews separate from primary six-independent-image cases and from runtime maturity evidence.
- After 24/24 machine audit and 24/24 human approval, request separate authorization before GitHub push and a non-destructive `v1.0.0-beta.4` Release.

## Validation

- TDD covers variable source counts, outfit-fact prompt binding, schema-version dispatch, schema-v4 mutation refusal and byte-level golden preservation, schema-v5 validation, duplicate collection IDs, representative collection selection, batch authorization binding and refusal of unapproved promotion.
- Existing white-vest evidence, style pages and beta.3 release contracts must remain green.
- Release checks must assert that the white-vest collection still contains its unchanged 72 registered JPEG assets and that the outfit collection contains its own 72 registered preview derivatives plus the separately governed source case. They must reject missing rights, changed hashes, unapproved sheets, receipts/candidates, preview/final conflation and private absolute paths.
- Final verification includes all repository tests, 24/24 pack lint, Skill/Plugin validation, production strict/runtime checks, privacy/history scan and archive inspection.

## Explicit non-goals

- No GPT-Image-2.5 API path, API key, third-party generator, telemetry or automatic retry.
- No redesign of the runtime action-0/action-1 workflow.
- No replacement of the existing white-vest gallery or beta.1–beta.3 artifacts.
- No claim that 24 previews equal 24 independent commercial finals or satisfy external adoption requirements.
