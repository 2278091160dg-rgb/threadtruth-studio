# Demo media policy

ThreadTruth Studio uses a **CC0-only** policy for institution-sourced auxiliary demo media. The first supported source is The Metropolitan Museum of Art Open Access API. CC BY, CC BY-SA, NC, ND, unknown licenses, and media copied from informal web pages are not eligible.

Primary demo media follows a separate authorization path. The maintainer must retain a publication-rights declaration for every real-garment source and for any identifiable model shown in it. Generated results must be disclosed as AI-generated media and may be offered under CC0 only to the extent the project can grant those rights.

Acquisition does not equal publication. The development tool stores each candidate in the ignored `.threadtruth/` quarantine, verifies source metadata and file evidence, and produces an offline review gallery. Promotion still requires human review confirming that the image contains no identifiable person, logo or trademark, watermark, or sensitive cultural context and that it depicts a physical garment. The reviewer must replace the gallery placeholder with their own public GitHub handle; copying another maintainer's identity is not valid evidence.

Every promoted case retains the authoritative object URL, raw source metadata, metadata and image hashes, reviewer handle, checklist, and license notices. Use of an Open Access object does not imply endorsement by The Metropolitan Museum of Art or any other source institution.

Apache-2.0 does not cover media. Source media and project-generated demo media are offered under CC0 only to the extent the project can grant rights. CC0 does not remove possible trademark, privacy, personality, moral, or cultural rights.

An institution-sourced case is always marked `auxiliary-demo-ready`. It does not replace the maintainer-owned real-garment main case, does not count toward the 30-day Beta, and does not count as a non-maintainer installation or complete authorized real workflow.

Runs expire at the seven-day boundary. An expired candidate cannot be approved or promoted. A previously approved candidate may still be explicitly rejected so its run can be removed by `prune --expired`; promoted evidence is retained.

The candidate schema is versioned at `tools/schemas/demo-candidate-v1.schema.json`; promoted auxiliary records use `rights-v1.schema.json`; promoted primary records use `primary-rights-v1.schema.json`. Release builds fail closed when a public case lacks required evidence, uses an incompatible license, omits required AI labeling, has an unregistered asset, or has a hash mismatch.
