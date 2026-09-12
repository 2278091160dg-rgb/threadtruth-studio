# Migration from `clothing-portrait-studio`

The active public identity is now `threadtruth-studio`. The legacy name exists here only to explain migration and is not an active trigger or second installed Skill.

## Safe migration sequence

1. Keep the legacy installation unchanged as a rollback source.
2. Install the new Plugin in a controlled test environment.
3. Temporarily disable, but do not delete, the legacy Skill.
4. Run explicit invocation, positive implicit trigger, negative isolation, paid-gate, clean uninstall, and rollback tests.
5. If the new version fails, disable it and restore the legacy installation.
6. If all checks pass, archive the legacy directory without deleting it.

Changing global Skill state is intentionally not performed by the repository tooling and requires separate user authorization.

## Behavior continuity

The migration preserves the real-garment input gate, 24-style routing, explicit action authorization, serial six-image closed set, identity-only look-1 anchor, canvas validation, commercial QA, state vocabulary, and no-fallback rule. Model-specific runtime wording was removed; the Plugin uses whatever native image capability the host provides.
