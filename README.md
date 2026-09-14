# ThreadTruth Studio

[English](README.md) | [简体中文](README.zh-CN.md)

**Source-faithful fashion portrait production for Codex**

ThreadTruth Studio is an independent, community-maintained Codex Plugin. It reads visible facts from a real garment photo, routes among 24 style packs, waits for explicit approval before paid image generation, and governs a six-image delivery with commercial QA. It is not an OpenAI product or endorsement.

![A real white hooded puffer vest source beside six independent Korean Cold Editorial results](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/hero.jpg)

This is a real, rights-cleared source-to-six-result case: four photos of one white hooded puffer vest produced six independent Korean Cold Editorial B1 images, with SHA-256 records and closed human review. [Open the case](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/README.md) · [Media rights](docs/demo/RIGHTS.md)

## Install and try recognition

Download the Plugin ZIP and its separate checksum from the [`v1.0.0-beta.3` Release](https://github.com/2278091160dg-rgb/threadtruth-studio/releases/tag/v1.0.0-beta.3). beta.1 and beta.2 remain immutable. New-host CLI activation remains a separately disclosed compatibility gap. Follow the complete matching [installation guide](docs/INSTALL.md).

After installation, start a **new Codex task**, upload a garment image first, then enter exactly:

```text
请用 $threadtruth-studio 识别并推荐风格，不要生图
```

Expected: a garment recognition card, primary and alternative recommendations, and the full 24-style catalogue. This prompt does **not** authorize image generation.

Installed it? Share a sanitized result through the [installation feedback form](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/new?template=installation-feedback.yml). Use [GitHub Issues](https://github.com/2278091160dg-rgb/threadtruth-studio/issues) for bugs or [Discussions](https://github.com/2278091160dg-rgb/threadtruth-studio/discussions) for questions. Do not post private garments, customer data, credentials, or full logs. Maintainer: [DENGGUI](https://github.com/2278091160dg-rgb) · WeChat: `Lvmusic0930`.

## What is public today

- Independent six-final coverage: `1/24`, the real case above.
- Single-style preview coverage: **24/24 machine-layout checked, 24/24 maintainer accepted, and 24/24 published in beta.3**. The series uses the same white vest, one style and six poses per sheet. Each native sheet is preserved as an optimized copy beside a labeled `1200×1200` layout derivative with six `360×480` (`3:4`) cards and a whole-board thumbnail. Six maintainer-requested corrections replace their rejected first drafts with explicit hash lineage. Historical schema 1–3 records remain read-only. These are AI-generated direction previews, not independent finals. Full counts and remaining gates: [work register](docs/WORK-STATUS.md).
- Gendered and culturally named styles translate atmosphere, styling language, lighting, and setting only. They never infer identity, ethnicity, nationality, body, or gender from the garment or wearer.

[Browse the 24-style evidence index](docs/demo/STYLES.md). A six-tile board is a direction preview, not six independent finals and not a completed workflow.

<!-- STYLE_PREVIEWS:START -->

| | | | |
|---|---|---|---|
| <a href="docs/demo/style-previews/white-vest-24-v1/american-street-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/american-street-thumb.jpg" alt="American Street — six-pose layout preview, not finals" width="180"></a><br>American Street | <a href="docs/demo/style-previews/white-vest-24-v1/athleisure-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/athleisure-thumb.jpg" alt="Athleisure — six-pose layout preview, not finals" width="180"></a><br>Athleisure | <a href="docs/demo/style-previews/white-vest-24-v1/balletcore-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/balletcore-thumb.jpg" alt="Balletcore — six-pose layout preview, not finals" width="180"></a><br>Balletcore | <a href="docs/demo/style-previews/white-vest-24-v1/british-heritage-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/british-heritage-thumb.jpg" alt="British Heritage — six-pose layout preview, not finals" width="180"></a><br>British Heritage |
| <a href="docs/demo/style-previews/white-vest-24-v1/cityboy-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/cityboy-thumb.jpg" alt="Cityboy — six-pose layout preview, not finals" width="180"></a><br>Cityboy | <a href="docs/demo/style-previews/white-vest-24-v1/clean-fit-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/clean-fit-thumb.jpg" alt="Clean Fit — six-pose layout preview, not finals" width="180"></a><br>Clean Fit | <a href="docs/demo/style-previews/white-vest-24-v1/coquette-ladylike-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/coquette-ladylike-thumb.jpg" alt="Coquette Ladylike — six-pose layout preview, not finals" width="180"></a><br>Coquette Ladylike | <a href="docs/demo/style-previews/white-vest-24-v1/ecommerce-studio-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/ecommerce-studio-thumb.jpg" alt="E-commerce Studio — six-pose layout preview, not finals" width="180"></a><br>E-commerce Studio |
| <a href="docs/demo/style-previews/white-vest-24-v1/french-effortless-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/french-effortless-thumb.jpg" alt="French Effortless — six-pose layout preview, not finals" width="180"></a><br>French Effortless | <a href="docs/demo/style-previews/white-vest-24-v1/gorpcore-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/gorpcore-thumb.jpg" alt="Gorpcore — six-pose layout preview, not finals" width="180"></a><br>Gorpcore | <a href="docs/demo/style-previews/white-vest-24-v1/guochao-street-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/guochao-street-thumb.jpg" alt="Guochao Street — six-pose layout preview, not finals" width="180"></a><br>Guochao Street | <a href="docs/demo/style-previews/white-vest-24-v1/italian-luxe-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/italian-luxe-thumb.jpg" alt="Italian Luxe — six-pose layout preview, not finals" width="180"></a><br>Italian Luxe |
| <a href="docs/demo/style-previews/white-vest-24-v1/japanese-lifestyle-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/japanese-lifestyle-thumb.jpg" alt="Japanese Lifestyle — six-pose layout preview, not finals" width="180"></a><br>Japanese Lifestyle | <a href="docs/demo/style-previews/white-vest-24-v1/korean-cold-editorial-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/korean-cold-editorial-thumb.jpg" alt="Korean Cold Editorial — six-pose layout preview, not finals" width="180"></a><br>Korean Cold Editorial | <a href="docs/demo/style-previews/white-vest-24-v1/korean-menswear-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/korean-menswear-thumb.jpg" alt="Korean Menswear — six-pose layout preview, not finals" width="180"></a><br>Korean Menswear | <a href="docs/demo/style-previews/white-vest-24-v1/neo-chinese-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/neo-chinese-thumb.jpg" alt="Neo Chinese — six-pose layout preview, not finals" width="180"></a><br>Neo Chinese |
| <a href="docs/demo/style-previews/white-vest-24-v1/nordic-minimal-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/nordic-minimal-thumb.jpg" alt="Nordic Minimal — six-pose layout preview, not finals" width="180"></a><br>Nordic Minimal | <a href="docs/demo/style-previews/white-vest-24-v1/office-commute-women-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/office-commute-women-thumb.jpg" alt="Office Commute Women — six-pose layout preview, not finals" width="180"></a><br>Office Commute Women | <a href="docs/demo/style-previews/white-vest-24-v1/old-money-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/old-money-thumb.jpg" alt="Old Money — six-pose layout preview, not finals" width="180"></a><br>Old Money | <a href="docs/demo/style-previews/white-vest-24-v1/preppy-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/preppy-thumb.jpg" alt="Preppy — six-pose layout preview, not finals" width="180"></a><br>Preppy |
| <a href="docs/demo/style-previews/white-vest-24-v1/quiet-luxury-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/quiet-luxury-thumb.jpg" alt="Quiet Luxury — six-pose layout preview, not finals" width="180"></a><br>Quiet Luxury | <a href="docs/demo/style-previews/white-vest-24-v1/resort-vacation-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/resort-vacation-thumb.jpg" alt="Resort Vacation — six-pose layout preview, not finals" width="180"></a><br>Resort Vacation | <a href="docs/demo/style-previews/white-vest-24-v1/workwear-vintage-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/workwear-vintage-thumb.jpg" alt="Workwear Vintage — six-pose layout preview, not finals" width="180"></a><br>Workwear Vintage | <a href="docs/demo/style-previews/white-vest-24-v1/y2k-millennium-display.jpg"><img src="docs/demo/style-previews/white-vest-24-v1/y2k-millennium-thumb.jpg" alt="Y2K Millennium — six-pose layout preview, not finals" width="180"></a><br>Y2K Millennium |

<!-- STYLE_PREVIEWS:END -->

## Why it exists and its boundaries

The uploaded garment remains authoritative for color, material appearance, silhouette, length, construction, pattern, logo placement, and accessories. Style changes treatment, never product facts. The workflow adds a real-garment input gate, deterministic style routing, a separate paid-generation consent gate, serial six-image delivery, identity anchoring, canvas checks, and evidence-backed QA.

Use it for apparel portraits, fashion editorial, and ecommerce portrait sets. Do not use it for non-apparel products, text-only concept generation, general virtual try-on, CAD-grade fit simulation, API integration, or unattended commercial delivery. It does not promise exact small text/logo reproduction, platform approval, or sales performance.

There is no runtime telemetry, MCP server, external connector, API-key flow, or network fallback. Native image generation is used only after explicit approval. Without that host capability, recognition and prompt work can continue, but generation stops at `tool-blocked`.

## Release and compatibility status

The public Beta began with [`v1.0.0-beta.1`](https://github.com/2278091160dg-rgb/threadtruth-studio/releases/tag/v1.0.0-beta.1). [`v1.0.0-beta.3`](https://github.com/2278091160dg-rgb/threadtruth-studio/releases/tag/v1.0.0-beta.3) is the newest public download; it adds the accepted 24-style preview gallery without changing runtime behavior. Audited host: macOS `26.6.2`, `codex-cli 0.144.1`. Codex desktop build: unavailable, not inferred. See [compatibility](docs/COMPATIBILITY.md) and the [30-day Beta register](docs/BETA.md).

The project's own exit targets are at least 30 days, five non-maintainer installations, and three authorized complete cases; these are project targets, not OpenAI admission rules. Codex for Open Source application details live only in [docs/CODEX-FOR-OSS.md](docs/CODEX-FOR-OSS.md).

## Development

```bash
python3 -m unittest discover -s tests -v
python3 tools/pack-lint.py --strict skills/threadtruth-studio/references/styles/*.pack.yaml
python3 tools/trigger-eval.py
python3 tools/build-release.py
```

Runtime lives under `skills/threadtruth-studio/`; repository tests, evals, release tooling, and evidence stay outside it. Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [USER-GUIDE.html](USER-GUIDE.html), [MIGRATION.md](MIGRATION.md), and [PROVENANCE.md](PROVENANCE.md). Apache-2.0 covers code and documentation, not demo media.
