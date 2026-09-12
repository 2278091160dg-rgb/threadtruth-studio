# ThreadTruth Studio

**Source-faithful fashion portrait production for Codex**

ThreadTruth Studio is an independent, community-maintained Codex Plugin that turns a real garment photograph into a governed fashion-portrait workflow. It recognizes visible garment facts, routes among 24 style packs, requires explicit approval before image generation, delivers six independent images serially, and closes with commercial QA. The project is preparing for the [Codex for Open Source](https://learn.chatgpt.com/community/codex-for-oss) program; it has not applied or been accepted.

> Public release status: `v1.0.0-beta.1` candidate. The runtime and regression suite are implemented; the rights-cleared public demo and 30-day external Beta evidence are still pending. This repository is not an OpenAI product or endorsement.

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
- Rights-cleared public demo: `sample-blocked`, awaiting maintainer-owned source images.
- Global old-skill migration: not performed; requires separate authorization.
- GitHub Release and published checksums: pending the rights-cleared demo and clean installation gate.
- Codex for Open Source application: not submitted; requires stable `v1.0.0`, threshold evidence, and final user authorization.

## Community

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), the [roadmap](ROADMAP.md), and the [competitive boundary](docs/COMPETITIVE-LANDSCAPE.md). Issues and Discussions will become the public support channels after the repository is published.

Licensed under [Apache-2.0](LICENSE).
