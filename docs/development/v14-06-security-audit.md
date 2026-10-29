# V14-06 — Internal security and adversarial assurance

## Scope and outcome

Independent internal Subagent C assessment of the verified V14-05 runtime:
`ac893bc3174f0a7ace67454d19ad6e61116425af`. The new audit tests and this report
were prepared on `codex/v14-06-final-release-readiness`; no production, CI,
compatibility-verifier or inventory files were edited by this agent.

**No reproducible P0 or P1 security defect was demonstrated in this assessment.**
This is finite internal assurance, not a professional external penetration test,
an industrial certification, forensic authentication or proof of defect absence.
Final candidate/package identity remains the integrator's separate freeze gate.

## Attack-surface matrix

| Surface and hypothesis | Observed defense and concrete checks | Result / boundary |
|---|---|---|
| Native YAML: constructors, aliases, nesting, malformed Unicode | Event parser rejects tags/anchors/aliases; byte/event/depth ceilings precede tree construction; existing `test_loading.py` adversaries | PASS; native schema remains unchanged |
| Import/evidence JSON: duplicate keys, nonfinite values, nested input | Strict loaders and explicit numeric/text/type restrictions; workspace/history/release tests reject rehashed structural lies | PASS for tested contracts; hashes do not establish origin |
| Draw.io/GraphML: DTD, entities, PI, compressed payloads | Expat handlers forbid active XML constructs; bounded decompression and cumulative XML budgets; graphical security suite | PASS; supported graphical subsets only |
| XLSX/DOCX/PPTX ZIP metadata and allocation order | No extraction; all members checked before XML parsing; new late-member sentinel covers traversal, symlink mode, nonempty directory, ratio and NUL ambiguity for all three adapters | 15 new PASS; no source modification or extracted files |
| OOXML active content and relationships | Unknown/macro/object parts and external relationships rejected; existing workbook/document adversaries cover even unselected content | PASS; structural import, no Office execution |
| PCAP/PCAPNG: lengths, growth, allocation, framing | Streaming bounds, regular-file identity checks, packet/block/file ceilings; independent resources/publication suites | PASS; unsupported framing is not positive protocol knowledge |
| Paths, links, junctions, reparse points | Historical/capture path policies reject unsupported local paths/ancestors; regular reads compare opened and named identities | PASS for executed cases; one real junction creation test environmentally skipped |
| Interrupted writes, destination conflicts, partial sites | Existing outputs preserved; staged capture publication or historical completion marker; rejection/interruption tests | PASS; incomplete historical directory is not a verified bundle |
| HTML/CSS/SVG, hostile labels and URI schemes | Escaping, fixed renderer filenames, restricted element/attribute/resource/link validators and CSP; generated bundle and documentary tests | PASS; parser checks are not human browser/zoom acceptance |
| Rehashed forged reports and invalid approval chains | Source-dependent replay and canonical regeneration reject invented authority; revocation/supersession preserve history while removing current approval | PASS; local reviewer names are unauthenticated assertions |
| Release archives and public source | Existing archive/source-integrity suites reject unsafe/unreviewed members, collisions and mismatched reviewed bytes | PASS of targeted tests; final built artifacts need integrator audit |
| Unexpected networking or code execution | Static runtime search found no socket/HTTP request/subprocess/eval/exec/pickle/archive-extraction call sites; targeted tests inherited offline network-denial hook | PASS for observed operations; not a physical air-gap measurement |
| Credentials and imported privacy | Bounded signature scan of 483 tracked parent files (454 strict UTF-8) found no private-key blocks, AWS access-key signatures or GitHub-token signatures; privacy disclosures reviewed | No signature hit; not a comprehensive secret detector or anonymization claim |

Import Studio's individual-file adapter promises refusal of leaf symlinks and
special files, whereas project/capture/history policies have stricter ancestor
checks. Documentation makes that distinction. Local single-writer publication
does not claim isolation from a malicious concurrent administrator, universal
crash durability, or distributed-filesystem atomicity. No new guarantee is inferred
from ordinary mutation checks. Finite byte/structure budgets are not a universal
bound on interpreter RSS; JSON parsing and library metadata have their own costs.

## Finding and disposition register

| ID | Capability / severity | Reproduction; expected versus actual | Source / disposition / verification | Residual limit |
|---|---|---|---|---|
| V146-SEC-001 | OOXML preallocation assurance, P2 | Append a hostile entry after valid XML members and replace `XmlBudget.parse` with a sentinel that fails on any call. Expected: controlled archive/budget failure before tree allocation. Actual: all three adapters fail before the sentinel, leave input bytes intact and create no other file. | `tests/test_v146_security_audit.py`; assurance gap closed with 15 finite tests; no runtime patch required | Covers five concrete metadata attacks, not arbitrary ZIP implementations or Office rendering |

There are no open substantiated P0/P1 findings from this agent. Missing external
protocol positives, no TCP reassembly, NULL/SLL limitations, unauthenticated human
review, original-capture provenance and the single-writer trust model remain
documented limitations. They were not relabeled as defensive detections.

## Reproduction and receipts

Interpreter: Windows Python 3.14.5 in `.venv`; installed parent runtime, whose
97 production hashes were recorded by the integrator before work began.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_v146_security_audit.py -q `
  --basetemp=output/v146/security-new-tmp --junitxml=output/v146/security-new.xml
.venv/Scripts/python.exe -m ruff check tests/test_v146_security_audit.py
.venv/Scripts/python.exe -m ruff format --check tests/test_v146_security_audit.py
$env:MYPYPATH = (Join-Path (Get-Location) 'src')
.venv/Scripts/python.exe -m mypy tests/test_v146_security_audit.py
```

Results: **15 PASS**, Ruff lint PASS, Ruff formatting PASS, strict mypy PASS.
The source path is required for this focused mypy invocation because this project
normally type-checks `src` and the complete test tree together; the installed
package does not carry a `py.typed` marker. No type-checking rule was suppressed.

The broader campaign used `OTARCHGUARD_OFFLINE_CHECK=1` and `PYTHONPATH` set to
the absolute `tools/offline` directory, then ran these 12 test files together:

```text
tests/test_v146_security_audit.py
tests/test_loading.py
tests/test_ingestion_graphical_security.py
tests/test_ingestion_xlsx_security.py
tests/test_ingestion_documents.py
tests/test_drift_security.py
tests/test_historical_explorer_bundle.py
tests/test_capture_independent_publication.py
tests/test_capture_independent_resources.py
tests/test_release_audit.py
tests/test_release_integrity.py
tests/test_source_checkout.py
```

Result: **430 PASS, one SKIP, zero FAIL/ERROR; 431 unique cases; 62.12 seconds**.
The 15 new tests are included in that count and are not additive. The skip is
`test_actual_windows_junction_is_rejected`: the operating system did not grant
junction creation. It is not a product pass. Raw evidence is retained locally in
`output/v146/security-suite.log` and `output/v146/security-suite.xml`.

No live plant, production network, uncontrolled PCAP, unbounded fuzzing, actual
resource exhaustion, external publication or remote mutation was used. Advisory
database/dependency/license review and final wheel/sdist identities belong to
the separate packaging assurance and integrator acceptance records.
