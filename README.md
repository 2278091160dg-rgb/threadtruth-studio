# ThreadTruth Studio

[English](README.md) | [简体中文](README.zh-CN.md)

**Source-faithful fashion portrait production for Codex**

ThreadTruth Studio is an independent, community-maintained Codex Plugin. It reads visible facts from a real garment photo, routes among 24 style packs, waits for explicit approval before paid image generation, and governs a six-image delivery with commercial QA. It is not an OpenAI product or endorsement.

![A real white hooded puffer vest source beside six independent Korean Cold Editorial results](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/hero.jpg)

This is a real, rights-cleared source-to-six-result case: four photos of one white hooded puffer vest produced six independent Korean Cold Editorial B1 images, with SHA-256 records and closed human review. [Open the case](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/README.md) · [Media rights](docs/demo/RIGHTS.md)

## Install and try recognition

Download the Plugin ZIP and its separate checksum from the [Releases page](https://github.com/2278091160dg-rgb/threadtruth-studio/releases). `v1.0.0-beta.1` is immutable; the beta.2 package has passed static, archive, checksum, version, and source-registration checks. New-host CLI activation remains a separately disclosed compatibility gap, not a patch-release blocker. Follow the complete matching [installation guide](docs/INSTALL.md).

After installation, start a **new Codex task**, upload a garment image first, then enter exactly:

```text
请用 $threadtruth-studio 识别并推荐风格，不要生图
```

Expected: a garment recognition card, primary and alternative recommendations, and the full 24-style catalogue. This prompt does **not** authorize image generation.

Installed it? Share a sanitized result through the [installation feedback form](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/new?template=installation-feedback.yml). Use [GitHub Issues](https://github.com/2278091160dg-rgb/threadtruth-studio/issues) for bugs or [Discussions](https://github.com/2278091160dg-rgb/threadtruth-studio/discussions) for questions. Do not post private garments, customer data, credentials, or full logs. Maintainer: [DENGGUI](https://github.com/2278091160dg-rgb) · WeChat: `Lvmusic0930`.

## What is public today

- Independent six-final coverage: `1/24`, the real case above.
- Single-style preview coverage: **3 historical native attempts; 1/24 machine-layout checked, 0/24 human-approved, 0/24 public**. The target remains **24 previews of the same white vest: ONE style and SIX poses each**. The development-only schema `4.0` workflow preserves the native sheet and creates a clearly labeled layout derivative: a square `1200×1200` board with six `360×480` (`3:4`) cards. Complete pose images are fitted without stretching, upscaling or subject cropping; padding and locally rendered labels are disclosed, not claimed as native model precision. Historical schema 1–3 records remain read-only and retain their original failed geometry findings. The registered Korean C image has been composed and machine-checked with no new native call; visual acceptance remains pending; after human acceptance, the other 23 styles need separate generation authorization. Full counts and remaining gates: [work register](docs/WORK-STATUS.md).
- Gendered and culturally named styles translate atmosphere, styling language, lighting, and setting only. They never infer identity, ethnicity, nationality, body, or gender from the garment or wearer.

[Browse the 24-style evidence index](docs/demo/STYLES.md). A six-tile board is a direction preview, not six independent finals and not a completed workflow.

<!-- STYLE_PREVIEWS:START -->

No human-approved preview gallery yet. / 暂无已获人工批准的预览图库。

<!-- STYLE_PREVIEWS:END -->

## Why it exists and its boundaries

The uploaded garment remains authoritative for color, material appearance, silhouette, length, construction, pattern, logo placement, and accessories. Style changes treatment, never product facts. The workflow adds a real-garment input gate, deterministic style routing, a separate paid-generation consent gate, serial six-image delivery, identity anchoring, canvas checks, and evidence-backed QA.

Use it for apparel portraits, fashion editorial, and ecommerce portrait sets. Do not use it for non-apparel products, text-only concept generation, general virtual try-on, CAD-grade fit simulation, API integration, or unattended commercial delivery. It does not promise exact small text/logo reproduction, platform approval, or sales performance.

There is no runtime telemetry, MCP server, external connector, API-key flow, or network fallback. Native image generation is used only after explicit approval. Without that host capability, recognition and prompt work can continue, but generation stops at `tool-blocked`.

## Release and compatibility status

The public Beta began with [`v1.0.0-beta.1`](https://github.com/2278091160dg-rgb/threadtruth-studio/releases/tag/v1.0.0-beta.1). The beta.2 prerelease adds a release-owned personal-source installer; its focused tests passed in a mock home, but a new-host CLI activation has not yet been verified. Audited host: macOS `26.6.2`, `codex-cli 0.144.1`. Codex desktop build: unavailable, not inferred. See [compatibility](docs/COMPATIBILITY.md) and the [30-day Beta register](docs/BETA.md).

The project's own exit targets are at least 30 days, five non-maintainer installations, and three authorized complete cases; these are project targets, not OpenAI admission rules. Codex for Open Source application details live only in [docs/CODEX-FOR-OSS.md](docs/CODEX-FOR-OSS.md).

## Development

```bash
python3 -m unittest discover -s tests -v
python3 tools/pack-lint.py --strict skills/threadtruth-studio/references/styles/*.pack.yaml
python3 tools/trigger-eval.py
python3 tools/build-release.py
```

Runtime lives under `skills/threadtruth-studio/`; repository tests, evals, release tooling, and evidence stay outside it. Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [USER-GUIDE.html](USER-GUIDE.html), [MIGRATION.md](MIGRATION.md), and [PROVENANCE.md](PROVENANCE.md). Apache-2.0 covers code and documentation, not demo media.
