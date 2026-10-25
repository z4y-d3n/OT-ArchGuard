# Quality and before/after review, entirely offline

Use an installed 1.2.0 distribution. From the source/tutorial checkout run:

```powershell
python -m tools.quality_walkthrough --output NEW_LOCAL_FOLDER
```

Choose a fresh folder. The script uses only fictional data and the active
interpreter's installed `otarchguard` console. It creates two valid declarations:
the proposed model removes one declared asset, adds another, moves the engineering
station to a declared zone, changes its interface address/placement and removes
an allow rule. It separately revises a fictional documentary arrow while keeping
its owner-confirmed native model unchanged.

Run the resulting models yourself (replace `NEW_LOCAL_FOLDER`):

```powershell
otarchguard quality NEW_LOCAL_FOLDER/baseline.yaml
otarchguard quality NEW_LOCAL_FOLDER/baseline.yaml --profile NEW_LOCAL_FOLDER/profile.json --output NEW_QUALITY_REPORT
otarchguard compare-architecture NEW_LOCAL_FOLDER/baseline.yaml NEW_LOCAL_FOLDER/proposed.yaml --trace eng:svc_plc --output NEW_COMPARISON
```

Without `--output`, quality prints JSON. A report directory includes `index.html`,
`review.json`, CSS and a link-audited manifest. Open `index.html` directly from
the original folder; keep the complete folder together when relocating it.

The profile explicitly requests source support for every selected asset. No
source evidence was supplied for the first models, so the missing support stays
in the coverage denominator. This is an unmet documentation requirement, not
evidence that the network is vulnerable. The profile hash binds the exact model;
using it for the changed model requires a freshly bound owner profile.

In the comparison, follow Baseline, Proposed and Native changes. Inspect each
changed field and exact before/after declaration. “Removed” means removed from
the proposed model. Diagrams declare placement/edges; they do not prove deployed
connectivity. Follow Exact analysis for `eng:svc_plc`: both native engines actually
evaluate the TCP/502 listener and the reported lost permission is limited to that
query. Without `--trace`, analysis is NOT_EVALUATED, never denied.

Open `documentary-comparison/index.html` for the second example. Its native hashes
are equal. The arrow, source digest and owner acknowledgment changed, while no
native transport or analytical permission was invented. Original documents are
not embedded in the report. Selected content is still sensitive local engineering
information, not a public-safe export.

Optional comparison flags accept separately matching project provenance,
baseline/proposed quality profiles and an explicit ordered model-bound identity
mapping. See the [contract](../../docs/development/v12-07-quality-and-comparison.md)
for exact schemas, limits and unsupported split/merge cases. Invalid sidecars or
stale profiles stop with exit 2 and publish no successful partial report.
