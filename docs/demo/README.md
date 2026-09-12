# Public demo

Primary status: `sample-blocked`. Auxiliary status: no promoted case yet.

The repository does not include a demo image because no maintainer-owned, publication-authorized garment set has been supplied in this public-source workflow. Historical images with unknown or conditional rights are deliberately excluded.

A complete demo must contain:

1. original real garment source image(s);
2. recognition card;
3. style recommendation, full 24-style choice surface, and selected route trace;
4. one labeled `preview-grid` image;
5. six independently generated images with distinct hashes and one canvas contract;
6. per-image and set-level QA conclusion;
7. user confirmation closing every `qa-user-review` item;
8. completed rights row in `RIGHTS.md`.

The optional The Met pipeline can create reproducible CC0 auxiliary cases, but it cannot replace this maintainer-owned main case or count toward Beta adoption. Candidate files stay in ignored local quarantine and need a complete human review before promotion. See [MEDIA-POLICY.md](MEDIA-POLICY.md).

```bash
python3 tools/demo-media.py search --query coat --limit 8
python3 tools/demo-media.py fetch --run <run-id>
python3 tools/demo-media.py audit --run <run-id>
python3 tools/demo-media.py gallery --run <run-id>
```

Approval and promotion are intentionally separate commands. The exact commands and checklist are printed in the offline gallery. Paid native generation for the main demo requires a separate, explicit user instruction after publication-authorized source images are supplied.
