# Outfit 24-style preview collection design

Date: 2026-09-14  
Status: approved in chat; written review pending  
Scope: development evidence and public demo only; runtime generation behavior stays unchanged

## Outcome

Add a second public 24-style preview collection showing that ThreadTruth Studio can preserve a coordinated physical outfit, not only one garment. The existing white-vest collection remains intact. The new collection uses one authorized source image and produces one six-pose action-0 sheet for each of the 24 registered styles.

## Source contract

- Case slug: `beige-blazer-denim-outfit-24-v1`.
- The public source is the supplied 3:4 flat-lay image, SHA-256 `40163fcb0aeae44b1e9b690de9fec047bd517a0764260a4d3f1d014dbfc16d5a`.
- Maintainer attestation: the image shows a real physical outfit, is not a pure AI concept image, and the project has sufficient rights to use the image and depicted apparel, footwear, bag and accessories for generation and public GitHub demonstration.
- Outfit truth: beige single-breasted blazer with notched lapels, white crew-neck top, dark indigo straight-leg jeans, olive structured tote, dark-brown loafers, watch and restrained gold jewelry. Prompts must not invent brands, logos, text or replacement garments.
- The accepted white-vest `look-1` may be supplied as identity-only guidance for one adult female model. It cannot override any outfit fact.

## Minimal implementation

1. Add one public preview-source case containing the optimized source image, structured rights record and concise README.
2. Extend `tools/style_preview.py` with a required source-case selector for new schema-v5 runs. Schema v4 and the released white-vest evidence remain read-only and valid.
3. Parameterize only the currently hard-coded values: source files, rights record, outfit name/facts, source count, label subtitle and identity anchor. Do not add a service, database, API client or new runtime dependency.
4. Allow several approved preview collections to coexist. Keep the white-vest collection as the representative link on existing individual style pages; expose the outfit collection through its own bilingual gallery and the repository home page.
5. Add ChatGPT/Codex invocation wording to documentation: ChatGPT uses `@threadtruth-studio`; Codex uses `$threadtruth-studio`. Do not claim official marketplace listing.

## Generation and evidence flow

- Use the installed ThreadTruth Studio Plugin in the current Codex host and the native image-generation capability documented as `gpt-image-2` on 2026-09-14.
- Prepare all 24 prompts from the registered style packs. Each prompt applies exactly one style to the same complete outfit and requests one 2×3 six-pose action-0 preview sheet.
- Run four separately authorized batches of at most six native calls. Calls are serial. No automatic retry is allowed; a failed sheet remains failed until a new targeted authorization is given.
- For every call, retain the actual prompt hash, call identifier when exposed, generation time, native image hash and observed dimensions. Do not claim a model ID that the host does not expose per call.
- Apply the existing deterministic 1200×1200 display composition after generation: six 360×480 (3:4) card frames, no stretching, no upscaling and no subject/garment cropping. Local labels provide the exact bilingual style name and the disclosure `AI生成 · 排版衍生预览 · 非成片`.
- Machine audit cannot approve visual fidelity. The maintainer must review all six cells for the same complete outfit, adult model consistency, usable anatomy, style distinction and unobstructed disclosure.

## Public presentation

- Add a dedicated outfit collection page with the authorized source, 24 whole-sheet thumbnails, links to each complete display board, generation-model disclosure and limitations.
- Update English and Chinese README pages to present two distinct proofs: `single garment · 24 styles` and `coordinated outfit · 24 styles`.
- Register source, native sheets, display derivatives and thumbnails in the generated rights index with full hashes and parent-child derivation.
- Keep all previews separate from primary six-independent-image cases and from runtime maturity evidence.
- After 24/24 machine audit and 24/24 human approval, request separate authorization before GitHub push and a non-destructive `v1.0.0-beta.4` Release.

## Validation

- TDD covers variable source counts, outfit-fact prompt binding, schema-v4 immutability, schema-v5 validation, duplicate collections, collection selection and refusal of unapproved promotion.
- Existing white-vest evidence, style pages and beta.3 release contracts must remain green.
- Release checks must reject missing rights, changed hashes, unapproved sheets, preview/final conflation, local candidate data and private absolute paths.
- Final verification includes all repository tests, 24/24 pack lint, Skill/Plugin validation, production strict/runtime checks, privacy/history scan and archive inspection.

## Explicit non-goals

- No GPT-Image-2.5 API path, API key, third-party generator, telemetry or automatic retry.
- No redesign of the runtime action-0/action-1 workflow.
- No replacement of the existing white-vest gallery or beta.1–beta.3 artifacts.
- No claim that 24 previews equal 24 independent commercial finals or satisfy external adoption requirements.
