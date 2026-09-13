# Codex for Open Source readiness packet

Official target: [**Codex for Open Source**](https://learn.chatgpt.com/community/codex-for-oss), using the [official application form](https://openai.com/form/codex-for-oss/). Application submission is an external action and must not occur until the stable release and final maintainer authorization.

## Eligibility narrative

Use this base copy only after replacing bracketed metrics with facts measured on the submission date:

> ThreadTruth Studio is an Apache-2.0 Codex Plugin for source-faithful apparel portrait production. It turns real garment photos into governed six-image sets through 24 deterministic style routes, explicit paid-generation consent, identity-only anchoring, canvas validation, and public regression QA. As of [date], [testers] non-maintainers completed installation, [cases] authorized workflows were documented, and [releases] public releases incorporated [issues] external feedback items.

Keep the final answer under the form's current character limit and verify the form again on submission day.

## Planned form selections

- Role: Primary maintainer
- Interest: API credits for my project
- Codex Security: not requested

API credits would be used only for open-source regression evaluation, pull-request review, and release automation. They would not add an API fallback to the runtime Skill.

## Submission-day facts

Record only public, auditable values:

| Field | Source | Value |
|---|---|---|
| Non-maintainer installs | opt-in Beta records | 0 of 5 required at Beta publication |
| Authorized complete cases | `docs/demo/RIGHTS.md` + case reports | 1 of 3 required |
| Release downloads | GitHub Release insights | 0 at `2026-09-13T04:59:28Z` publication baseline |
| Stars | GitHub repository | pending |
| External issues/discussions | GitHub | pending |
| Feedback-driven release | changelog + linked issue | pending |
| Open high-severity issues | security/issue triage | pending |

## Private form fields

Name, ChatGPT email, GitHub username, and OpenAI Organization ID are collected only in the official form after the user provides them. They must never be committed to this repository.

## Status vocabulary

- `application-ready`: stable release and every threshold met; form not submitted.
- `applied`: the official form was submitted after final authorization.
- `accepted`: OpenAI sent an acceptance notice.
- `not-selected`: OpenAI declined or the application expired.

Never infer `accepted` from a successful form submission.
