# ThreadTruth Studio

**Source-faithful fashion portrait production for Codex**

ThreadTruth Studio is an independent, community-maintained Codex Plugin that turns a real garment photograph into a governed fashion-portrait workflow. It recognizes visible garment facts, routes among 24 style packs, requires explicit approval before image generation, delivers six independent images serially, and closes with commercial QA. The project is preparing for the [Codex for Open Source](https://learn.chatgpt.com/community/codex-for-oss) program; it has not applied or been accepted.

![A real white hooded puffer vest source beside six independent Korean Cold Editorial results](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/hero.jpg)

> Public release status: `v1.0.0-beta.1` release candidate. The runtime, regression suite, Plugin lifecycle, and first rights-cleared primary demo are complete. The 30-day external Beta begins only when the GitHub Release is published. This repository is not an OpenAI product or endorsement.

## See the governed result

The first primary case uses four authorized photographs of one real white hooded puffer vest and delivers six independent Korean Cold Editorial B1 images. Every public source and result has a recorded SHA-256 digest, the user closed the visual QA review, and the case identifies the results as AI-generated media.

- [Open the complete source-to-six-image case](docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/README.md)
- [Browse the 24-style evidence index](docs/demo/STYLES.md) — currently `1/24` styles have public visual evidence; planned cards do not pretend otherwise.
- [Review media rights and limitations](docs/demo/RIGHTS.md)

## Why it exists

Most image workflows optimize for visual novelty. ThreadTruth optimizes for source truth: the uploaded garment remains authoritative for color, material appearance, silhouette, length, construction, pattern, logo placement, and accessories. Style changes the visual treatment, never the product facts.

The project adds four controls that are often missing from prompt collections and thin API wrappers:

- a real-garment input gate;
- deterministic routing across 24 versioned styles;
- a separate, explicit paid-generation consent gate;
- a six-image closed set with identity anchoring, canvas checks, and evidence-backed QA.

## Boundaries

Use it for apparel model portraits, fashion editorial, and ecommerce portrait sets. Do not use it for non-apparel product images, text-only concept generation, general virtual try-on or API integration. It does not promise CAD-grade garment geometry, exact virtual-fit simulation, unattended commercial delivery, platform approval, or sales performance.

There is no runtime telemetry, MCP server, external connector, API-key flow, or network fallback. Image generation uses only the host's native capability after explicit user approval. Without that capability, the workflow stops at `tool-blocked` and can still provide recognition or prompts.

## Repository layout

```text
.codex-plugin/plugin.json          Plugin manifest
skills/threadtruth-studio/         Runtime payload only
evals/                             Trigger and behavior fixtures
tests/                             Repository and release contracts
tools/                             Development validation and packaging
docs/                              Public evidence and project notes
USER-GUIDE.html                    Offline bilingual-friendly guide
```

The development-only [demo evidence workflow](docs/demo/README.md) governs both authorized primary cases and The Met Open Access CC0 auxiliary candidates. Institutional candidates enter an ignored local quarantine and require metadata, JPEG, hash, expiry, state-transition, and human-rights review before promotion. Auxiliary media never substitutes for a primary real-garment case. Apache-2.0 covers code and documentation, not demo media; see the [media policy](docs/demo/MEDIA-POLICY.md).

## Local validation

Python 3.10+ is sufficient for the repository tests and tools.

```bash
python3 -m unittest discover -s tests -v
python3 tools/pack-lint.py --strict skills/threadtruth-studio/references/styles/*.pack.yaml
python3 tools/trigger-eval.py
python3 tools/build-release.py
```

The generated release archive is allowlist-built into `dist/`; development evals, tests, and audit tools are excluded from the Plugin runtime payload.

## Install for local testing

Clone the source into your local plugins directory. Do not install the inner skill directory directly: the distributable unit is the repository containing `.codex-plugin/plugin.json`.

```bash
git clone https://github.com/2278091160dg-rgb/threadtruth-studio.git "$HOME/plugins/threadtruth-studio"
```

The first Beta Release will add the final marketplace command after a clean-environment installation proves it. Until then, use the local Plugin source workflow and select this repository root. See [USER-GUIDE.html](USER-GUIDE.html) for the interaction model and [MIGRATION.md](MIGRATION.md) for safe coexistence and rollback.

## Development status

- Runtime identity and 24 style packs: implemented.
- Static, trigger, privacy, and allowlist packaging checks: implemented.
- Public repository and required GitHub Actions checks: active and passing.
- Maintainer-machine Plugin lifecycle: install, discovery, upgrade, uninstall, and legacy rollback verified; `v1.0.0-beta.1` restored and enabled.
- Rights-cleared primary demo: one `image-ready` source-to-six-image case is public.
- 24-style visual evidence: `1/24` ready; the remaining cards are explicitly marked planned and require fresh source rights plus per-style generation approval.
- Reproducible The Met CC0 auxiliary-media evidence pipeline: implemented; one human-approved case is promoted as auxiliary evidence.
- External clean-environment validation: pending; the maintainer preflight does not count toward Beta adoption.
- Known runtime issue: a minimal implicit missing-image request may skip Skill loading; see [Issue #1](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/1). Explicit invocation is the Beta workaround.
- GitHub Release and published checksums: release candidate assets are being prepared; publication starts the external Beta clock.
- Codex for Open Source application: not submitted; requires stable `v1.0.0`, threshold evidence, and final user authorization.

## Community

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), the [roadmap](ROADMAP.md), and the [competitive boundary](docs/COMPETITIVE-LANDSCAPE.md). GitHub Issues and Discussions are the public support channels.

Licensed under [Apache-2.0](LICENSE).
