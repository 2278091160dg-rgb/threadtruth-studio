# Public demo

Primary status: one `image-ready` public case. Auxiliary status: one `auxiliary-demo-ready` case.

The first primary case is the [white hooded puffer vest in Korean Cold Editorial B1](primary-cases/white-hooded-puffer-vest-korean-cold/README.md). It includes four authorized source photographs, six independent accepted results, file hashes, canvas evidence, a closed human QA review, and an AI-generated-media disclosure. Original PNG results are distributed separately as a checksummed GitHub Release asset; the repository carries optimized display JPEGs.

A complete demo must contain:

1. original real garment source image(s);
2. recognition card;
3. style recommendation, full 24-style choice surface, and selected route trace;
4. one labeled `preview-grid` or a separately recorded single-image direction test;
5. six independently generated images with distinct hashes and one canvas contract;
6. per-image and set-level QA conclusion;
7. user confirmation closing every `qa-user-review` item;
8. completed rights record in `RIGHTS.md`, including the AI-generated-media label where applicable.

The [24-style evidence index](STYLES.md) distinguishes ready visual evidence from planned cards. A style receives a representative image only after its source rights and generation approval have been recorded; one approval never authorizes unattended generation across the index.

The optional The Met pipeline can create reproducible CC0 auxiliary cases, but it cannot replace a primary case or count toward Beta adoption. Candidate files stay in ignored local quarantine and need a complete human review before promotion. See [MEDIA-POLICY.md](MEDIA-POLICY.md).

## Single-style preview operator workflow (schema 4.0)

This development-only collector preserves native content and creates disclosed fixed-card presentation. It never calls image generation or fills human approval. The runtime Skill's action0 and six-independent-final behavior remain unchanged.

Exact `3:4` describes the display **card frame**, not the source photograph. Display boards are `1200×1200`, with six `360×480` cards at x=44/420/796 and y=140/636. Complete pose images fit inside each card using uniform downscaling and padding; no stretch, upscale, generative fill or crop of the model/garment. Only original gutters and text regions are excluded when extracting the observed six panels. If a native pose is already cropped or distorted, layout cannot repair it.

The registered complete bilingual style name and mode subtitle are rendered in separate header bands. The footer is:

```text
AI生成 · 排版衍生预览 · 非成片 / PREVIEW ONLY — NOT FINAL
```

Use a readable local Chinese font with `--font`. Its basename/hash is evidence; the font binary and absolute local path are not public assets. Missing fonts or text that cannot fit cause failure, not silent truncation.

### Prepare, ingest and compose

Start a new run. Schema1–3 runs remain read-only with their original findings and cannot be upgraded in place or inherit current approval. The unchanged native prompt binding allows reuse of a registered schema3 original and its real call record in a fresh run; it does not create a new generation call.

```bash
python3 tools/style-preview.py prepare --run-id white-vest-cards-v4
python3 tools/style-preview.py ingest --run-id white-vest-cards-v4 --style korean-cold-editorial --image /path/to/original.png --generation-record /path/to/actual-generation.json
python3 tools/style-preview.py compose --run-id white-vest-cards-v4 --style korean-cold-editorial --layout-json /path/to/observed-layout.json --font /path/to/local-cjk-font.ttc
python3 tools/style-preview.py audit --run-id white-vest-cards-v4 --style korean-cold-editorial
python3 tools/style-preview.py gallery --run-id white-vest-cards-v4 --style korean-cold-editorial
```

The generation record contains the real authorized call ID, observed generation time and exact prepared prompt hash. Never rewrite an old prompt hash to match a new plan.

`layout-json` has `original_sha256` and `cells`: exactly six row-major `[x,y,width,height]` rectangles observed in the retained native image. Bind the actual original hash; do not infer boundaries from the square board. Rectangles must be integer, positive, in bounds, non-overlapping and in the six-pose order. Different native panel ratios are allowed. Framing remains full-body for poses1/2/4/6, half-body permitted for3/5.

Compose keeps the native whole-sheet JPEG and creates a display JPEG plus whole-display thumbnail. Evidence records source authorization, native original and optimized hashes, actual call/prompt/pack/rule bindings, extraction rectangles, fit transforms, fixed-card geometry, font identity and derivative hashes. Identical repeated composition is idempotent; changed content is not a silent overwrite.

### Human review and publication

Machine layout checks prove fixed cards and artifact integrity only. They cannot prove visual fidelity, correctly observed boundaries, readable Chinese glyphs or human consent.

The review template remains pending. A real reviewer must compare the source and display: six complete poses, same garment/model, style, full-body framing where required, no content loss through extraction, padding, correct bilingual labels and AI disclosure. Review binds current source/display/evidence hashes. Missing, null, pending or failed checks are not approval.

```bash
python3 tools/style-preview.py approve --run-id white-vest-cards-v4 --style korean-cold-editorial --review /path/to/completed-human-review.json
```

After the Korean pilot is accepted, obtain each remaining style's explicit generation instruction and repeat ingest/compose/review. No automatic retry or batch authorization is implied. Only after all24real reviews:

```bash
python3 tools/style-preview.py audit --run-id white-vest-cards-v4
python3 tools/style-preview.py gallery --run-id white-vest-cards-v4
python3 tools/style-preview.py promote --run-id white-vest-cards-v4
```

Public promotion includes only registered native whole-sheet JPEGs, layout derivatives, thumbnails and generated evidence/pages. It updates rights, style pages and the README thumbnail slots transactionally. Raw originals, local receipts, font files and review drafts remain private. A failed/unapproved preview cannot enter public artifacts; no preview counts as an independent final, complete workflow or `image-ready` set.

## The Met auxiliary-media operator workflow

```bash
python3 tools/demo-media.py search --query coat --limit 8
python3 tools/demo-media.py fetch --run <run-id>
python3 tools/demo-media.py audit --run <run-id>
python3 tools/demo-media.py gallery --run <run-id>
```

For this separate The Met pipeline, approval and promotion are intentionally separate commands; its exact commands and checklist are printed in its offline gallery. Every new primary case and every additional style image still requires publication-authorized source media and a separate, explicit native-generation instruction.
