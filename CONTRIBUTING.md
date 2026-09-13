# Contributing to ThreadTruth Studio

Thank you for improving source-faithful fashion portrait production.

## Before opening a change

1. Open an [Issue](https://github.com/2278091160dg-rgb/threadtruth-studio/issues) describing the user problem, trigger boundary, and expected state transition, or use [Discussions](https://github.com/2278091160dg-rgb/threadtruth-studio/discussions) for exploratory proposals.
2. Keep runtime code under `skills/threadtruth-studio/`; keep evals, audit tools, CI, and evidence at repository root.
3. Do not add external connectors, API-key flows, telemetry, network fallback, or paid actions without a separately reviewed design.
4. Never commit customer content, secrets, private logs, personal paths, or media without documented publication rights.

## Development loop

Behavior changes require a failing regression fixture first, then the smallest runtime change, then the full suite:

```bash
python3 -m unittest discover -s tests -v
python3 tools/pack-lint.py --strict skills/threadtruth-studio/references/styles/*.pack.yaml
python3 tools/trigger-eval.py
python3 tools/build-release.py
```

Contributions must also pass the repository CI.

## Pull requests

Include:

- what changed and why;
- new or updated regression coverage;
- affected statuses and permission gates;
- validation commands and results an independent reviewer can rerun;
- rights information for every added image;
- a `CHANGELOG.md` entry for user-visible behavior.

Reviews resolve each finding as `open`, `fixed`, `deferred(issue)`, or `wontfix(reason)`. A passing checker does not replace human review of safety, source fidelity, or trigger scope.

By submitting a contribution, you agree that it is licensed under Apache-2.0.

Maintainer: [DENGGUI](https://github.com/2278091160dg-rgb) · WeChat: `Lvmusic0930`. Never send secrets or private customer media through public channels; security reports belong in the private channel described by [SECURITY.md](SECURITY.md).
