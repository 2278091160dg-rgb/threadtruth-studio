# Public demo

Primary status: one `image-ready` public case. Auxiliary status: one `auxiliary-demo-ready` case.

The first primary case is the [white hooded puffer vest in Korean Cold Editorial B1](primary-cases/white-hooded-puffer-vest-korean-cold/README.md). It includes four authorized source photographs, six independent accepted results, file hashes, canvas evidence, a closed human QA review, and an AI-generated-media disclosure. Original PNG results are distributed separately as a checksummed GitHub Release asset; the repository carries optimized display JPEGs.

A complete demo must contain:

1. original real garment source image(s);
2. recognition card;
3. style recommendation, full 24-style choice surface, and selected route trace;
4. one labeled `preview-grid` or a separately recorded single-image direction test;
5. six independently generated images with distinct hashes and one canvas contract;
6. per-image and set-level QA conclusion;
7. user confirmation closing every `qa-user-review` item;
8. completed rights record in `RIGHTS.md`, including the AI-generated-media label where applicable.

The [24-style evidence index](STYLES.md) distinguishes ready visual evidence from planned cards. A style receives a representative image only after its source rights and generation approval have been recorded; one approval never authorizes unattended generation across the index.

The optional The Met pipeline can create reproducible CC0 auxiliary cases, but it cannot replace a primary case or count toward Beta adoption. Candidate files stay in ignored local quarantine and need a complete human review before promotion. See [MEDIA-POLICY.md](MEDIA-POLICY.md).

```bash
python3 tools/demo-media.py search --query coat --limit 8
python3 tools/demo-media.py fetch --run <run-id>
python3 tools/demo-media.py audit --run <run-id>
python3 tools/demo-media.py gallery --run <run-id>
```

Approval and promotion are intentionally separate commands. The exact commands and checklist are printed in the offline gallery. Every new primary case and every additional style image still requires publication-authorized source media and a separate, explicit native-generation instruction.
