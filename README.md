# OT-ArchGuard

**Offline OT Architecture & Historical Network Evidence Analysis**

Validate declared IT/OT architectures, correlate supported passive capture
evidence, compare historical records, and trace findings to their supporting
evidence. Use it to review segmentation proposals and investigate differences
between declarations and finite observations.

**Offline · Passive · Evidence-driven · Python 3.12+**

Analysis reads local files; it does not scan devices or capture live traffic.
Reports open locally without a server, JavaScript or remote rendering service.

**Published stable: [v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0).**
This branch prepares the **unpublished v1.4.0 candidate** described below.
Distribution/CLI: `1.4.0`; frozen native engine: `1.3.0`; native YAML schema: `1`.
Python 3.12 and 3.14 form the Windows, Ubuntu and macOS CI matrix; metadata admits
Python >=3.12 without claiming every interpreter version has been tested.

[See it in action](#see-it-in-action) · [Quick Start](#quick-start--5-minutes) ·
[Capabilities and limits](#what-it-does--what-it-does-not-do) ·
[Documentation & verification](#documentation--verification)

## See it in action

**Historical Evidence & Drift Explorer — fictional historical comparison**

![Historical Explorer v1.4 domain navigation table showing canonical record counts for fictional communications, industrial metadata, declared architecture, native assessments, interpretation and coverage, with explicit limits on what each comparison establishes](docs/images/historical-explorer-v14.png)

This owner-provided **v1.4 browser screenshot** shows domain navigation and
canonical record counts from a fictional historical evidence comparison.
The visible interpretation notes qualify the results: historical differences
do not prove an operational incident or a physical network change.
[Historical Explorer guide](docs/v14-historical-explorer.md) ·
[Screenshot provenance and preserved legacy previews](docs/images/README.md).

For **v1.4**, the [Historical Evidence & Drift Explorer walkthrough](docs/v14-historical-explorer.md#fictional-walkthrough-and-owner-review)
generates real offline reports for changed declarations, finite capture
differences, incomplete coverage, decoder reinterpretation and revoked approval.
Its tables link findings, comparability and retained evidence. A historical
difference alone establishes neither an industrial incident nor a physical
network change.

### From declared architecture to historical evidence

Each stage has its own inputs and commands. Identity associations and baseline
decisions require explicit review; this is not an automatic approval pipeline.

1. **Declared architecture:** validate the model and evaluate finite paths,
   requirements and prohibitions. Start with the [fictional architectures](examples/README.md).
2. **Passive capture:** read a supported local PCAP/PCAPNG and retain observations,
   coverage and bounded protocol metadata. Follow [PCAP Evidence Studio](docs/pcap-evidence-studio.md).
3. **Identity review:** inspect proposed address-to-asset/interface associations
   and explicitly record decisions. These are human assertions, not authenticated
   device identities. See the [capture example](examples/capture-studio/README.md).
4. **Historical evidence:** retain immutable observations and validated optional
   attachments; create a separately identified **analytical revision** for each
   selected interpretation. Follow the [historical lifecycle](docs/v14-history.md).
5. **Baseline review:** propose a scoped selection, inspect its evidence, then
   explicitly approve it if justified. A reviewed baseline does not authenticate
   the capture; a changed revision receives no inherited approval.
6. **Drift comparison:** select exact reference/candidate revisions and explicit
   alignment. Compare finite observations, declarations and supported native
   assessments, retaining incomparable and unsupported states. See [drift](docs/v14-drift.md).
7. **Visual evidence report:** open the [Historical Explorer](docs/v14-historical-explorer.md)
   and follow findings to retained source context. Portable integrity verification
   and source-dependent analytical reproduction are separate checks.

The existing fictional walkthroughs exercise these transitions, including
explicitly labelled fixture reviews. They confer no approval on real evidence.

## Quick Start — 5 minutes

Try a fictional declared remote-support architecture and open its **Architecture
Explorer**. This first report needs no capture, account or baseline decisions.
Five minutes is an approximate onboarding label, not a measured guarantee.

**Choose the installation source first:**

- **Stable v1.3.0:** obtain its wheel and source archive from the
  [published release](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0).
  Use the [stable first-run instructions](docs/installation.md#stable-v130-first-run).
- **Local v1.4.0 candidate:** obtain the four local audited assets from the owner,
  put them in `artifacts/` inside a fresh folder, and
  [verify the complete checksum list](docs/installation.md#obtain-and-verify-assets).
  Repository reviewers can use the source-bound assets identified in the latest
  [documentation handoff](docs/development/v14-06-public-documentation-es.md).
- **Future stable v1.4.0:** use its actual release assets only after publication
  and acceptance of the integrated source. There is no published v1.4 download
  destination to use yet.

With **Python >=3.12** available as `python`, run this candidate sequence in
**Windows PowerShell**, from the fresh folder containing `artifacts/`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install artifacts/otarchguard-1.4.0-py3-none-any.whl
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\otarchguard.exe --version
tar -xf artifacts/otarchguard-1.4.0.tar.gz
.\.venv\Scripts\otarchguard.exe explore otarchguard-1.4.0/examples/remote-support/proposed.yaml --output report
Invoke-Item .\report\index.html
```

The wheel supplies the installed application; the source archive supplies the
fictional example. No Git checkout, development installation or GitHub CLI is
required. Expected `--version` output: `1.4.0`; analysis exits **0** and
creates `report/index.html` with local navigation. The diagram shows declarations,
including a firewall placed in three zones; it does not prove physical
connectivity or permitted traffic. `explore` generates a model browser and does
not assert that all declared communication intents pass.

Installation may download dependencies. For disconnected installation use a
[prepared wheelhouse](docs/installation.md#optional-completely-offline-setup).
Analysis and report navigation need no network service. Choose a new report
directory on a repeat run. Linux/macOS use the same inputs and CLI arguments
with `.venv/bin/`; see [platform instructions](docs/installation.md#candidate-first-report-on-linuxmacos).

## What it does / What it does not do

### What it does

| Capability | Practical use | Guide |
| --- | --- | --- |
| Declared architecture analysis | Validate bounded YAML declarations, placements and explicit transitions | [Native schema](docs/yaml-schema-v1.md) |
| Native reachability and trace | Explain exact declared IPv4 TCP/UDP initiation paths, port intervals and replayable witnesses | [Trace](docs/trace.md), [algorithms](docs/algorithms.md) |
| Requirements, prohibitions and exposure | Check independent communication intents and compare finite exposure without hiding broken requirements | [Examples](examples/README.md), [quality and comparison](examples/quality-comparison/README.md) |
| Import Studio | Reconcile supported inventory, diagram and restricted document sources through explicit review | [Import guide](docs/import-studio.md), [multi-source example](examples/import-studio/projects/README.md) |
| Architecture Explorer | Browse zones, assets, interfaces, provenance and explicit analytical queries offline | [Explorer example](examples/explorer/README.md) |
| PCAP Evidence Studio | Inspect supported passive captures, review address associations and reconcile eligible observations with the declared model | [Capture guide](docs/pcap-evidence-studio.md) |
| Industrial metadata | Inspect seven bounded header/metadata subsets with separate hints, structural evidence and abstentions | [Coverage and limits](docs/v14-foundation.md) |
| Immutable historical evidence | Retain metadata collections and validated attachments with exact identities | [Lifecycle](docs/v14-history.md) |
| Analytical revisions | Preserve separate interpretations of the same collection, bound to exact producer semantics | [Revision contract](docs/development/v14-analysis-revisions-adr.md) |
| Scoped baseline review | Propose, inspect, approve, supersede or revoke an exact selection through explicit local decisions | [Review workflow](docs/v14-history.md#propose-inspect-and-explicitly-decide) |
| Historical drift | Compare selected observations, declarations and supported native assessments with coverage and alignment limits | [Drift workflow](docs/v14-drift.md) |
| Historical Evidence & Drift Explorer | Navigate differences, unchanged support, abstentions and retained source evidence | [Explorer guide](docs/v14-historical-explorer.md) |
| Traceable offline publication and verification | Publish static local bundles; check portable integrity and separately reproduce analytical meaning against the source workspace | [Verification boundaries](docs/v14-historical-explorer.md#authority-and-verification) |

The seven subsets cover **Modbus TCP, PROFINET DCP, EtherNet/IP with limited CIP,
classic S7comm, IEC-104, OPC UA Binary outer framing and DNP3/TCP**. Port/EtherType
hints are separate from structurally validated headers. `STRUCTURALLY_VALID`
describes only the supported frame subset, never successful industrial execution.

### What it does not do

- **Active operation:** it does not scan devices, interact with controllers or
  capture live traffic.
- **Deployment proof:** declared reachability and compatible observations do not
  prove actual firewall enforcement, authorization or physical configuration.
- **Session or process proof:** packet observations do not establish successful
  sessions, command execution, compromise or process consequences.
- **Complete visibility:** unobserved traffic does not establish absence,
  blocking or an offline device. Unsupported or incomparable evidence remains
  qualified, rather than becoming a confirmed negative.
- **Unrestricted decoding:** arbitrary PCAP linktypes, arbitrary TCP stream
  reassembly and full industrial application payload interpretation are unsupported.
  DLT_NULL and Linux SLL are outside the supported linktypes.
- **Authenticated review or forensic provenance:** reviewer names are local
  unauthenticated assertions. SHA-256 establishes byte identity, not capture
  authenticity, authorship, collection time or reviewer authority.
- **Certification:** it does not independently certify a network's security
  posture, guarantee compliance or establish industrial process safety.

Workspaces assume a single writer. Reports and review text may contain sensitive
information; inspect a complete bundle before sharing it. External positive
validation remains incomplete for Modbus TCP, PROFINET DCP and IEC-104.
Read the [comprehensive limitations](docs/limitations.md),
[capture subset](docs/pcap-evidence-studio.md) and
[industrial protocol coverage](docs/v14-foundation.md).

## Documentation & verification

### Using the tool

| Start here | Continue with |
| --- | --- |
| [Installation and offline operation](docs/installation.md) | [Upgrade and recovery](docs/installation.md#historical-workspaces-and-upgrade) |
| [First-run fictional architectures](examples/README.md) | [Native model](docs/yaml-schema-v1.md), [trace](docs/trace.md), [requirements](docs/requirements.md) |
| [Import Studio](docs/import-studio.md) | [Multi-source reconciliation](examples/import-studio/projects/README.md), [restricted documents](examples/import-studio/documents/README.md) |
| [Architecture Explorer](examples/explorer/README.md) | [Reporting options](docs/reporting.md) |
| [PCAP Evidence Studio](docs/pcap-evidence-studio.md) | [Fictional capture tutorial](examples/capture-studio/README.md) |
| [Industrial metadata](docs/v14-foundation.md) | [Historical lifecycle and review](docs/v14-history.md) |
| [Historical drift](docs/v14-drift.md) | [Historical Evidence & Drift Explorer](docs/v14-historical-explorer.md) |

### Engineering and auditing

| Evidence or contract | Resource |
| --- | --- |
| Data schemas and analytical contracts | [Domain model](docs/domain-model.md), [algorithms](docs/algorithms.md), [versioned contract map](docs/development/v14-06-contracts.md) |
| Protocol subsets | [Enrichment contract](docs/development/v14-enrichment-contract.md), [ENIP/S7](docs/development/v14-enip-s7.md), [IEC/OPC/DNP](docs/development/v14-iec-opc-dnp.md) |
| Canonical evidence identities | [Frozen capture contract](docs/development/v13-18-evidence-contract-freeze.md), [historical evidence](docs/development/v14-evidence-contract.md), [review lifecycle](docs/development/v14-history-contract.md), [drift](docs/development/v14-drift-contract.md) |
| Historical compatibility | [Native audit](docs/development/v14-06-native-audit.md), [version identities](docs/development/v14-version-identity-adr.md) |
| Testing and CI | [Testing strategy](docs/testing-strategy.md), [workflow](.github/workflows/ci.yml), [historical verification](docs/verification.md) |
| Independent corpus evidence | [Interoperability](docs/development/v14-05-interoperability.md), [coverage gaps](docs/development/v14-05-corpus-coverage.md) |
| Performance | [Matched measurements](docs/development/v14-05-performance.md), [candidate comparison](docs/development/v14-06-performance.md) |
| Source/package integrity | [Packaging audit](docs/development/v14-06-packaging-audit.md), [local source-bound handoff](docs/development/v14-06-handoff-es.md) |
| Release acceptance | [Release checklist](docs/release-checklist.md), [Spanish publication runbook](docs/development/v14-06-publication-runbook-es.md) |
| Security and trust assumptions | [Scope and limitations](docs/limitations.md), [bounded internal security review](docs/development/v14-06-security-audit.md) |
| Release details | [Unpublished v1.4.0 notes](docs/release-notes-1.4.0.md), [published v1.3.0 notes](docs/release-notes-1.3.0.md), [changelog](CHANGELOG.md) |
| Visual provenance | [Current and historical diagram previews](docs/images/README.md) |

The owner reports six successful Windows/Ubuntu/macOS × Python 3.12/3.14 hosted
jobs for V14-06 checkpoint `5c70ae09904687070ecce9374546aff8ae806588`
on [Draft PR #24](https://github.com/z4y-d3n/OT-ArchGuard/pull/24).
Those results apply to that SHA. A later documentation commit needs its own
hosted CI; final acceptance of integrated `main`, artifact reconstruction,
tagging and stable publication remain separate owner gates. See the
[documentation verification handoff](docs/development/v14-06-public-documentation-es.md)
for the preceding local checks; [visual provenance](docs/images/README.md)
records the subsequently supplied owner screenshot.

Project code and documentation use [Apache-2.0](LICENSE); dependencies retain
their [licenses and notices](THIRD_PARTY_NOTICES.md). This independent project
does not imply IEC 62443 certification, normative conformity or institutional
endorsement. Report defects through [GitHub issues](https://github.com/z4y-d3n/OT-ArchGuard/issues)
with minimal fictional reproductions, exact versions and exit statuses; never
attach operational captures or credentials.
