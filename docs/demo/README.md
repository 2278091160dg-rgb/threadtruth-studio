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

## Single-style preview operator workflow (schema 3.0)

This development-only collector is separate from `demo-media.py`. It does not call native image generation, repair an image, infer visual acceptance, or fill a human review. Current schema `3.0` is enforced by `tools/style_preview.py`; the retained v1/v2 JSON Schema documents describe historical evidence only, and there is no separate v3 JSON Schema file.

For every style, the native image must be one square `1:1` board. The top title, subtitle, six-cell picture area, and footer all fit inside that square; the picture area is not itself the whole board. The six equal portrait cells are each `3:4`, ordered poses 1–3 on the top row and 4–6 on the bottom row. Poses 1, 2, 4 and 6 must be full-body; poses 3 and 5 may be half-body. The image, prompt and receipt are preserved. Do not crop, stretch, pad, enlarge, or use a script to replace or repair native text.

The native generator must render these labels, with the registered bilingual style name substituted exactly:

```text
<registered Chinese / English style name>
同款白马甲 · <mode> <Chinese mode name> · 六姿势预览
AI生成 · 方向预览 · 非成片 / PREVIEW ONLY — NOT FINAL
```

For example, Korean Cold Editorial uses `韩系冷感杂志风 / Korean Cold Editorial`, then `同款白马甲 · C 场景版 · 六姿势预览`, then the exact footer above. All three text bands must be distinct, readable, inside the square, and clear of the model, garment, face, shoes, bag, and poses.

Start a fresh run ID for current evidence; never reuse or upgrade a schema `1.0` or `2.0` run:

```bash
python3 tools/style-preview.py prepare --run-id white-vest-layout-v3
python3 tools/style-preview.py ingest --run-id white-vest-layout-v3 --style korean-cold-editorial --image /path/to/native-output.png --generation-record /path/to/native-generation.json
python3 tools/style-preview.py audit --run-id white-vest-layout-v3 --style korean-cold-editorial
python3 tools/style-preview.py gallery --run-id white-vest-layout-v3 --style korean-cold-editorial
```

The generation record must come from the actual authorized native call and bind that style's prepared prompt hash; do not invent a call ID, timestamp, or hash. A scoped `audit --style` checks the retained file, receipt, hashes, native/optimized dimensions, and current plan binding. With no human review it does not claim layout, label, pose, or approval success. An unscoped `audit` is the full collection gate and correctly fails until all 24 sheets exist and are approved.

Ingest writes `review-template-<style>.json` with null rectangles, `pending` checks, and `public_use_approved: false`. A human reviewer must inspect the retained image and enter observed pixel rectangles as `[x, y, width, height]`; the tool never derives them from a nominal grid. Integers must be in bounds, non-overlapping and correctly ordered. Cell widths/heights may differ by at most one pixel, and each cell must satisfy `abs(4*width - 3*height) <= 4`, the one-pixel raster-rounding allowance.

The following is a deliberately synthetic fragment for a disposable `900x900` test board. It is not a coordinate template for a real image and is not an approvable review:

```json
{
  "public_use_approved": false,
  "geometry": {
    "cells": [
      [90, 120, 210, 280], [345, 120, 210, 280], [600, 120, 210, 280],
      [90, 420, 210, 280], [345, 420, 210, 280], [600, 420, 210, 280]
    ],
    "title": [60, 20, 780, 35],
    "subtitle": [60, 70, 780, 30],
    "footer": [90, 750, 720, 50]
  },
  "checks": {
    "observed_boundaries": "pending",
    "full_bilingual_title": "pending",
    "correct_subtitle": "pending",
    "readable_ai_footer": "pending",
    "text_subject_non_overlap": "pending"
  }
}
```

The real review also has six ordered pose entries; each requires explicit `pass` for `product`, `pose_layout`, `identity_style`, `ai_disclosure`, and `framing`, plus a real reviewer identity, review time, exact confirmation, current preview/evidence hashes, and an explicit public-use decision. Null, missing, `pending`, or `fail` values are not consent. There is intentionally no command that auto-fills an all-pass review.

Only after the human has completed the actual review may the operator approve that style:

```bash
python3 tools/style-preview.py approve --run-id white-vest-layout-v3 --style korean-cold-editorial --review /path/to/completed-human-review.json
```

Repeat ingest, observed review, and approval separately for every registered style. Only then run the full collection gates:

```bash
python3 tools/style-preview.py audit --run-id white-vest-layout-v3
python3 tools/style-preview.py gallery --run-id white-vest-layout-v3
python3 tools/style-preview.py promote --run-id white-vest-layout-v3
```

`promote` remains blocked until all 24 current-schema previews pass machine validation and their own human approval. Schema v1/v2 runs remain inspectable as legacy galleries but cannot be prepared, ingested, approved, or promoted under the current standard.

## The Met auxiliary-media operator workflow

```bash
python3 tools/demo-media.py search --query coat --limit 8
python3 tools/demo-media.py fetch --run <run-id>
python3 tools/demo-media.py audit --run <run-id>
python3 tools/demo-media.py gallery --run <run-id>
```

For this separate The Met pipeline, approval and promotion are intentionally separate commands; its exact commands and checklist are printed in its offline gallery. Every new primary case and every additional style image still requires publication-authorized source media and a separate, explicit native-generation instruction.
