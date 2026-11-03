# V15-02 — F06 diagnostic reliability

Pre-fix receipts: `output/v15-02/report-io/pre-fix.json` and
`pre-fix-matrix.json`. Deterministic replacement plus cleanup denial raised
`PermissionError`, masking `ModelError/REPORT_IO_ERROR`. CLI emitted
`INTERNAL_ERROR/execution_error` with exit 2. Old output bytes survived; a real
temporary file remained. This was a diagnostic defect, not ordinary data loss.

`write_report` retains temporary creation, atomic `os.replace`, input collision
protection and `finally` cleanup. It records only primary/cleanup `OSError`
failures and emits the controlled diagnostic after cleanup. A primary write
failure keeps the original message and code; secondary cleanup adds path-free
context that a temporary file may remain. It does not claim successful removal.

Cleanup-only denial after successful replacement reports that the report was
written but cleanup could not be confirmed. The new report is retained; failure
does not trigger rollback of an already completed atomic replacement. Unexpected
non-I/O primary exceptions propagate, even if cleanup also has an I/O failure.
There is no broad exception suppression. Non-I/O cleanup failures also propagate.

Regression matrix in `test_v15_report_reliability.py`: creation, replacement,
replacement denial with successful/failed cleanup, old byte preservation,
diagnostic code/category, CLI exit 2/empty stdout, residual temporary behavior,
input collision before temporary creation, unexpected primary exception,
temporary creation denial and failure during writing a real temporary file.

Fault injection records actual ordering and file state. After successful
replacement the temporary path normally no longer exists; denied synthetic
unlink does not prove residual bytes. Failed cleanup leaves recovery to the
owner/filesystem; this gate does not introduce background retries or deletion of
unrelated files. Other subsystem publication contracts remain unchanged.
