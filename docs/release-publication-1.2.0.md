# Controlled 1.2.0 publication and recovery

Publication is a separate owner decision. The V12-08 branch, its PR, integration
merge, stable integration, tag, GitHub Release and PyPI upload have separate
authorization boundaries. No command below authorizes its execution. Never
repurpose the historical mistaken PR #8, force-push or move an existing tag.

## Candidate policy

Use **1.2.0rc1** consistently in pyproject, application version, literal identity
tests, current installation examples and CI archive names. Historical gate and
release documents retain their historical version. Native schema/report/trace
contracts keep their existing versions. No prerelease upload is implied.

Freeze a clean reviewed commit and public file manifest. Record both Git tree and
the SHA-256 of canonical sorted JSON mapping public names to raw-byte SHA-256.
Acceptance output stays outside that manifest. Source edits invalidate the freeze.
Build without fetching dependencies using the approved setuptools backend:

```text
python -c "from setuptools import build_meta; build_meta.build_wheel('output/artifacts'); build_meta.build_sdist('output/artifacts')"
python tools/audit_release.py output/artifacts/otarchguard-1.2.0rc1-py3-none-any.whl output/artifacts/otarchguard-1.2.0rc1.tar.gz --source-root . --output output/archive-audit.json
```

Use fresh regular installations outside the source tree. Provision approved
dependencies before offline verification, then install each archive separately
with `--no-index --no-deps --no-build-isolation`. Check `pip check`, native console,
`tools/verify_environment.py`, the full suite and all four installed walkthroughs.
`--no-deps` alone proves nothing about dependency availability. CI provisions
the exact approved verification pins; local evidence records its existing closure.

## Review, integration and final source

1. Review the exact diff from merged V12-07 baseline
   `6492143cb5c75f9f1ac51b70a7a305011c9d64fe`.
2. Present the exact commit/refspec and sanitized public-file inventory before
   requesting branch-push authorization. Confirm the remote ref has not changed.
3. After authorization, push only `codex/v12-08-final-release-hardening` and open
   its PR against `v1.2`. Do not enable auto-merge.
4. Require all six PR cells, exact run/attempt/job identities, full/sdist JUnit,
   archive/module audit and artifact upload results. Inspect actual artifacts
   where access permits; missing counts are unknown, not zero.
5. Complete owner review, browser journeys and manual accessibility disposition.
   Obtain explicit authorization for the actual PR merge.
6. Verify the resulting integration commit and tree, main and historical tags.
   Rebuild and rerun all six cells on that exact integration source. A green PR
   does not establish a green merge. Stop on unexpected differences.
7. Only after candidate acceptance and separate release authorization, prepare a
   new release PR into `main`. Change every active version reference to `1.2.0`
   in a reviewed release-only commit and rerun packaging, installed verification,
   browser checks affected by the change and the final six-cell matrix.
8. Obtain explicit merge authorization. Verify resulting stable commit, source
   manifest and newly built stable wheel/sdist. Never relabel rc archives.
9. Obtain separate annotated-tag and GitHub Release authorization. Verify
   `v1.2.0` does not exist, tag only the accepted stable commit, then re-read the
   remote tag object and target. Publish approved notes, hashes and artifacts.
10. PyPI requires separate ownership/account/channel approval. Verify name,
    versions, filename metadata and trusted publishing configuration without
    revealing credentials. Upload only the audited stable artifacts.
11. Download/inspect actual public release artifacts through approved tools,
    compare hashes and install from the intended channel. Declare RELEASED only
    after those receipts exist.

At baseline the public branch API reported both branches unprotected and no
rulesets. The authenticated protection endpoint was unavailable. Workflow checks
run, but governance enforcement must not be inferred. The owner must disposition
that finding; this gate does not modify repository-wide governance.

## Failure classification and recovery

Keep every failed attempt. Classify product assertions, packaging, source
integrity, portability, dependency/toolchain, artifact service, runner resource,
cancellation and unknown failures separately. Rerun a demonstrated transient
infrastructure failure; preserve its logs and exact attempts. Do not suppress
required upload failures or use `continue-on-error` for material checks.

Stop publication on failed browser acceptance, incompatible output, unexpected
main divergence, mismatched source/artifact hashes, missing dependencies or an
incorrect tag target. Correct within V12-08, identify a new candidate and repeat
affected verification. If no irreversible publication occurred, retain the last
known-good v1.1.0 environment and use its executable explicitly.

For partial GitHub/PyPI publication, preserve receipts and identify exactly which
assets are public. Do not overwrite tags or immutable PyPI files. A published
defect needs a reviewed corrective version/advisory, not rewritten history.
Document documentation corrections and retest their commands. Failed uploads
must be reconciled against server state before retrying.

## Retention

Preserve stable history, accepted gate manifests, archive hashes, final CI
receipts, candidate evidence and owner sources. Export essential hosted evidence
before its 30-day retention expires. Keep the V12-08 branch through acceptance
and the corrective-release window. Inventory caches, redundant synthetic sites
and old virtual environments after release; propose exact cleanup paths and sizes
for separate approval. This gate performs no historical deletion.
