# Security Policy

## Supported versions

Security fixes target the latest published Beta or stable release. Prior beta.1 assets are preserved; consult the [Releases page](https://github.com/2278091160dg-rgb/threadtruth-studio/releases) for the latest published version.

## Reporting a vulnerability

Use a [private GitHub vulnerability report](https://github.com/2278091160dg-rgb/threadtruth-studio/security/advisories/new) as the primary channel for credential exposure, unsafe file access, authorization bypass, prompt-injection persistence, or policy-gate bypass. Do not include real secrets, customer media, private prompts, or complete logs in a public Issue, Discussion, commit, or reproduction archive. Use synthetic or redacted samples and state the affected version and impact.

If GitHub temporarily cannot create a private report, retain it locally and contact [DENGGUI](https://github.com/2278091160dg-rgb) (WeChat `Lvmusic0930`) only to arrange a private channel; do not send vulnerability details in a public post or unsolicited first message.

## Runtime security contract

- No API key, token, credential, environment-variable, or hidden-file access.
- No MCP server, external connector, runtime telemetry, or API/network fallback. Explicitly approved image references and prompts are processed by the host's native image provider; host account policies govern that processing.
- Native image generation requires explicit user approval and is capped at six calls per request.
- Ambiguous permission is treated as no permission.
- Customer content and private evidence are excluded from public source and releases.
