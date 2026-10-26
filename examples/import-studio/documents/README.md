# Fictional document evidence tutorial

These fixtures contain no customer data. DOCX/PPTX are generated from explicit
transitional OPC structures by `tools.synthetic_documents`; they exercise
structural extraction rather than Office rendering. The DOCX table deliberately
contradicts the existing mixed inventory's zone. Presentation arrows and text
claiming `TCP 502 allowed` establish no native edge or rule.

After a regular noneditable v1.3.0 installation using the
[installation guide](../../../docs/installation.md), from the verified source
distribution or matching checkout:

```console
otarchguard import inspect examples/import-studio/documents/inventory.docx
otarchguard import preview examples/import-studio/documents/inventory.docx --profile examples/import-studio/documents/docx-profile.json
otarchguard import map examples/import-studio/documents/inventory.docx --profile examples/import-studio/documents/docx-profile.json --output document-draft.json
python -m tools.document_walkthrough --output NEW_DEMONSTRATION_DIRECTORY
```

The walkthrough executes the installed console for all four formats, registers
them alongside the existing XLSX/JSON/CSV/draw.io fixture, inspects/previews/maps the
project, creates unresolved decisions, applies the known fictional owner's explicit
choices, emits through native validation, rejects a source edited after review and
generates a compact Explorer after parking the raw documents. It writes command
receipts in `walkthrough.json`. Those fixture choices are not a production accept-all
workflow. Real owner review uses the existing project commands:

```console
otarchguard import project map project.json --output project-draft.json
otarchguard import project review project-draft.json --decisions unresolved.json
otarchguard import project acknowledge project-draft.json --decisions unresolved.json --source document-docx --reviewer "Named owner" --rationale "Retain selected text as context only" --output acknowledged.json
```

Acknowledgment retains documentary observations and confirms no candidates or
model. Resolve candidate partitions, contradictory fields and conflicts separately,
then supply final model confirmation using the documented project review contract.
Do not reuse a decision file after changing any source, profile or context.

Profiles explicitly choose `select: ["*"]` or exact collections, such as
`word/document.xml/table:1`, `slide:257` or `slide:257/table:4`. DOCX maps exact
headers `/id`, `/name`, `/zone`. Other shipped profiles retain evidence only.
TXT may explicitly map `key-values`; Markdown simple tables use `table:1`.
Only asset/zone/interface candidates are supported; each remains unconfirmed.

Open the original Explorer folder's `index.html` and retain its local CSS and all
relative files when moving it. A fragment identifies one record but its grouped
page contains other evidence. The site is sensitive local documentation, without
automatic public-safe redaction. See the
[restricted format and security reference](../../../docs/development/v12-06-document-evidence-and-explorer.md).
