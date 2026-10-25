# Offline Architecture Explorer walkthrough

All files in this tutorial are fictional. Install the locally built development
wheel into an environment containing the approved dependencies:

```text
python -m pip install --no-index --no-deps /path/to/otarchguard-1.2.0-py3-none-any.whl
otarchguard --version
```

Copy `examples/import-studio/projects/mixed/` from the development source archive
into a new working directory **outside the checkout**. It contains an XLSX asset/
zone inventory, JSON interfaces, CSV metadata, a draw.io drawing, profiles, explicit
native context and `tutorial-decisions.json`. Those owner choices apply only to
these exact fictional files. They equate known aliases, select inventory evidence
over a contradictory CSV zone and retain drawing connectors as documentary evidence.
Never use these decisions to accept a real customer project.

Run the installed console from that directory:

```text
otarchguard import project map project.json --output draft.json
otarchguard import project emit draft.json --project project.json --decisions tutorial-decisions.json --output accepted
otarchguard explore accepted/architecture.yaml --provenance accepted/architecture.provenance.json --output architecture-explorer
```

The two accepted artifacts are sufficient for Explorer generation. Keep their
matching names together; original workbook/XML/JSON sources need not be reopened.
An explicitly supplied mismatched or malformed sidecar fails closed.

Open `architecture-explorer/index.html` in your local browser. The six declared
devices are an engineering workstation, PLC, HMI, historian, firewall and switch.

1. Select **Zones**, then **control**. Confirm its native purpose and membership.
2. Select **eng** and an owned interface. Administrative ownership and placement
   are separately identified. Matching prefixes do not imply routing.
3. Follow a supporting source-qualified candidate to its **Source observation**.
   XLSX cells, JSON pointers and drawn node IDs retain their original locations.
4. Open the metadata candidate that proposed `alternate` for the engineering
   workstation. Its documentary value remains visible; the native zone is `control`.
5. Follow its reconciliation group and owner partition. Inspect selected field
   sources and rationale, then return to the authoritative native entity.
6. Follow the topology source → node → documentary connector. Its dashed line and
   graph direction describe the drawing; they do not authorize communication.
7. Open **Analytical results**. This inventory has no performed query and declares
   no transport/policy. **Not evaluated** is not a negative reachability result.

For genuine positive and negative query results, copy the source archive's
`tests/fixtures/boundary-device.yaml` into the working directory as `native.yaml`:

```text
otarchguard explore native.yaml --output analytical-explorer --trace it:svc_jump --trace it:svc_plc --check --scenario support_scope
```

Open its analytical index. `it → svc_jump` evaluates TCP/3389 with a permitted
witness; `it → svc_plc` evaluates TCP/502 with a negative engine explanation.
Inspect exact direction, destination binding, model hash, ports and limitations.
Other pairs remain unassessed. Without `--provenance`, the site explicitly identifies
itself as model-only and does not fabricate origins. Existing single-source
sidecars are not supported by Explorer version 1; omit them for model-only output.

Each site has `index.html`, entity/source/candidate/group/decision/node/connector/
analysis detail pages with hash-derived filenames, paginated indexes, `assets.css`
and `manifest.json`. All links are relative; no server, JavaScript, Python process
or Internet service is needed after generation. Existing destinations are refused.
Exit 0 means a complete site, including completed negative queries or failed intent
results. Exit 2 means no new complete site was published.

Before sharing a folder, review it as sensitive architecture documentation. Default
output includes asset names, addresses and selected documentary values/rationales.
Original documents/unmapped metadata and local source paths are excluded, but there
is no universal secret filter or public-safe/redacted mode. A digest is not proof
of safe content or authorship. Browser/assistive-technology validation limits are
listed in the [Explorer contract](../../docs/development/v12-05-architecture-explorer.md).
