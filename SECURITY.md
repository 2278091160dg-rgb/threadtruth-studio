# Security Policy

## Supported versions

Security fixes target the latest published Beta or stable release. No release has been published yet; this checkout is a source candidate.

## Reporting a vulnerability

Use a [private GitHub Security Advisory](https://github.com/2278091160dg-rgb/threadtruth-studio/security/advisories/new) for credential exposure, unsafe file access, authorization bypass, prompt-injection persistence, or policy-gate bypass. Do not include real secrets, customer media, or complete private logs in a public Issue.

If GitHub temporarily cannot create a private advisory, retain the report locally and contact the maintainer through the repository profile without disclosing vulnerability details in public.

## Runtime security contract

- No API key, token, credential, environment-variable, or hidden-file access.
- No MCP server, connector, runtime telemetry, external upload, or network fallback.
- Native image generation requires explicit user approval and is capped at six calls per request.
- Ambiguous permission is treated as no permission.
- Customer content and private evidence are excluded from public source and releases.
