# Security Policy

## Supported versions

Security fixes target the latest published Beta or stable release. `v1.0.0-beta.1` is the current immutable public baseline; beta.2 remains a candidate until published and verified.

## Reporting a vulnerability

Use a [private GitHub vulnerability report](https://github.com/2278091160dg-rgb/threadtruth-studio/security/advisories/new) as the primary channel for credential exposure, unsafe file access, authorization bypass, prompt-injection persistence, or policy-gate bypass. Do not include real secrets, customer media, private prompts, or complete logs in a public Issue, Discussion, commit, or reproduction archive. Use synthetic or redacted samples and state the affected version and impact.

If GitHub temporarily cannot create a private report, retain it locally and contact [DENGGUI](https://github.com/2278091160dg-rgb) (WeChat `Lvmusic0930`) only to arrange a private channel; do not send vulnerability details in a public post or unsolicited first message.

## Runtime security contract

- No API key, token, credential, environment-variable, or hidden-file access.
- No MCP server, connector, runtime telemetry, external upload, or network fallback.
- Native image generation requires explicit user approval and is capped at six calls per request.
- Ambiguous permission is treated as no permission.
- Customer content and private evidence are excluded from public source and releases.
