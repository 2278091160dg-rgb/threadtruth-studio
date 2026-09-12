# Demo media policy

ThreadTruth Studio uses a **CC0-only** policy for institution-sourced auxiliary demo media. The first supported source is The Metropolitan Museum of Art Open Access API. CC BY, CC BY-SA, NC, ND, unknown licenses, and media copied from informal web pages are not eligible.

Acquisition does not equal publication. The development tool stores each candidate in the ignored `.threadtruth/` quarantine, verifies source metadata and file evidence, and produces an offline review gallery. Promotion still requires human review confirming that the image contains no identifiable person, logo or trademark, watermark, or sensitive cultural context and that it depicts a physical garment.

Every promoted case retains the authoritative object URL, raw source metadata, metadata and image hashes, reviewer handle, checklist, and license notices. Use of an Open Access object does not imply endorsement by The Metropolitan Museum of Art or any other source institution.

Apache-2.0 does not cover media. Source media and project-generated demo media are offered under CC0 only to the extent the project can grant rights. CC0 does not remove possible trademark, privacy, personality, moral, or cultural rights.

An institution-sourced case is always marked `auxiliary-demo-ready`. It does not replace the maintainer-owned real-garment main case, does not count toward the 30-day Beta, and does not count as a non-maintainer installation or complete authorized real workflow.

The candidate schema is versioned at `tools/schemas/demo-candidate-v1.schema.json`; promoted public records use `rights-v1.schema.json`. Release builds fail closed when a public case lacks required evidence, uses a non-CC0 license, or has a hash mismatch.
