# Owner-only v1.1.0 publication and recovery

These are planned **owner actions**, not executed gate operations. Gate V11-6
does not authorize Codex to commit, contact remotes, merge, tag, upload, publish
or deploy. GitHub Release is the existing documented destination; package-index
publication is a separate decision. Version 1.1.0 metadata does not publish it.

Phases A–D below preserve the **historical Gate V11-6 integration procedure**;
do not repeat them as pending work. Candidate commit
`cca018ef585b056424f534b937f125be2d21d838` was integrated into local main at
`ee6436277c364803eea7f5be8b956131705f77e4`. Neither SHA automatically identifies
a later corrected release. For subsequent corrections, the owner reviews, commits
and integrates the approved branch with current six-way CI before phase E. Record
the actual accepted release SHA after all required corrections are integrated.

## A. Local acceptance (historical)

Review `codex/gate-v11-6` against accepted main
`bfa94942c185ad8ba677ea0ca567dc1672c836dd`: the [dossier](v1.1/gate-v11-6.md),
release notes, exact-version tests, comparison tool, manifests and ignored
`output/gate-v11-6/handoff.json` / `release-candidate-manifest.json`.
Recalculate archive hashes and inspect actual test/package receipts. Dirty-tree
content requires file hashes as well as HEAD. Confirm version 1.1.0, contracts 1,
unchanged analytical modules, root, stable tag, licenses and notices. Resolve all
local Critical/High blockers before advancing.

## B. Owner commit, push and PR (historical)

After explicit owner acceptance, the owner can run these commands outside this
gate. Review every staged file; the explicit manifest excludes ignored evidence.

```powershell
git switch codex/gate-v11-6
git diff --check
$approvedPublicFiles = Get-Content tools/public-files.txt
git add -- $approvedPublicFiles
git diff --cached --stat
git diff --cached
git commit -m "release: prepare unpublished OT-ArchGuard 1.1.0 candidate"
git push -u origin codex/gate-v11-6
```

Open a PR against `main` in the GitHub interface. Describe the version-only
production change, actual local results, strict compatibility, provenance and
pending hosted checks. Bind results to the exact committed source. Candidate
archives are not automatically the final post-merge assets.

## C. Hosted verification (historical integration requirements)

Require all six unique Windows/Ubuntu/macOS × Python 3.12/3.14 combinations on
the reviewed current PR commit. Duplicate push/PR runs are acceptable. Inspect
root checks, regular installs, Ruff/format/strict mypy/dependencies, offline full
suite/examples, exact package audits and fixed benchmark artifacts. Keep the
Unix child help environment `NO_COLOR=1`, `TERM=dumb`. Never disable a failing
job, assertion or network-isolation check. Earlier V11-5 results do not accept
V11-6. Any executable correction requires applicable tests/current hosted CI.

## D. Owner merge and synchronization (historical)

After approval and required checks, merge through the GitHub interface. On a
clean authoritative checkout the owner may switch to main and use their reviewed
fast-forward-only pull workflow. Stop for unexpected changes/divergence. Record
the exact accepted main SHA and its reviewed candidate/root/help-fix ancestry.
No merge or pull is performed during this gate.

## E. Post-merge source and package audit

Build from the exact clean accepted main in a new ignored directory; preserve
this gate's evidence. Record backend, interpreter/dependencies and public-source
hashes. Re-run installed provenance, package audit and extracted-sdist rebuild.
From the clean accepted checkout, set `$BuildPython` to the absolute path of an
approved build environment interpreter with `setuptools>=77` already installed.
The following commands require that environment; they acquire no dependencies:

```powershell
& $BuildPython -c "from setuptools import build_meta; build_meta.build_wheel('output/release-1.1.0'); build_meta.build_sdist('output/release-1.1.0')"
& $BuildPython tools/audit_release.py output/release-1.1.0/otarchguard-1.1.0-py3-none-any.whl output/release-1.1.0/otarchguard-1.1.0.tar.gz --source-root . --output output/release-1.1.0/archive-audit.json
Get-FileHash output/release-1.1.0/otarchguard-1.1.0-py3-none-any.whl -Algorithm SHA256
Get-FileHash output/release-1.1.0/otarchguard-1.1.0.tar.gz -Algorithm SHA256
```

Record hashes of these exact final bytes and prepare a reviewed SHA256SUMS file.
Do not reuse hashes of earlier archives. Equal member contents do not establish
universal archive-byte reproducibility. Any owner-approved release-status wording
change also needs source review, applicable CI and rebuilt/audited packages.

## F. Separate tagging decision

After separate owner approval, assign the full verified release SHA to
`$acceptedReleaseSha`. Check it against clean HEAD and the approved source. The
owner's explicit annotated-tag procedure is:

```powershell
git rev-parse HEAD
git status --porcelain
git tag -a v1.1.0 $acceptedReleaseSha -m "OT-ArchGuard v1.1.0"
git cat-file -p refs/tags/v1.1.0
git rev-parse 'v1.1.0^{}'
```

The owner separately approves and performs `git push origin v1.1.0`. Never modify
v1.0.1: object `39c855ad6204953495fdca4a7058fd53a3ba8f8c` targets root
`8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`. No v1.1.0 tag is created here.
Never tag uncommitted source or assume a future tag identifies this candidate.

## G. Separate publication decision

The owner approves destination and exact files. In the GitHub interface for
`z4y-d3n/OT-ArchGuard`, select the verified v1.1.0 tag, review release notes,
attach only audited wheel/sdist and the reviewed checksum file, then approve
publication. Exclude local paths/logs/credentials. Use publication-state-neutral
source documentation and the actual release record for availability; do not invent
a release date or URL. PyPI publication needs an independent decision, registry
identity/credentials review and procedure; no index upload is assumed.

## H. Post-publication verification

The owner checks public tag target, release description and actual downloaded
asset hashes. Install the actual downloaded wheel and sdist in approved separate
environments; verify metadata, native 1.1.0 output, module hashes, schema-1
validation, finite trace and offline reports. Record commit/OS/Python/checksums.
These operations remain pending until a release exists; local builds cannot
establish them.

## Recovery and incident response

| State/failure | Owner action | Identity rule |
| --- | --- | --- |
| Before publication: install, metadata, unexpected member or hosted failure | Stop advancement; retain package/logs and minimal reproducer; classify, correct reviewed scope and reverify | No release/tag until required checks pass |
| Merged but not tagged | Correct through a reviewed follow-up PR/current CI; rebuild from corrected accepted commit | Do not tag defective merge |
| Tag created, release unpublished | Stop and determine whether tag escaped locally; unshared local correction needs explicit owner decision; shared tag requires documented exceptional recovery or corrective version | Never silently move public tags |
| Hash differs or unexpected package content | Quarantine local copies, stop distribution, compare source/build/channel evidence and investigate | No substitution of different bytes under published identity |
| Published compatibility/install/package defect | Preserve original evidence/assets; issue advisory and reviewed corrective version; withdrawal requires a documented owner incident decision | Prefer immutable tags/assets; no silent replacement |
| Documentation overstates support | Review correction and identify affected version/verification boundary | Do not fabricate past tests/certification |
| v1.0.1 user rollback | Invoke retained known-good executable in parallel stable environment; preserve schema-1 input copies and compare historical behavior | Keep original stable assets unchanged |

Record blocker identifier, severity, reproduction, impact, contract, remedy,
disposition and authorization. An analytical defect blocks release pending a
separate decision; this gate does not silently alter semantics. No destructive
recovery is executed here.
