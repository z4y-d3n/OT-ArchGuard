# Independent fictional capture corpus (V13-14)

These original Apache-2.0 fixtures contain documentation-only IP addresses and
locally administered MAC addresses. They contain no operational capture, personal
data, credentials, or redistributed Wireshark code. The `.data` extension is
intentional: format recognition must use actual container headers.

Two independent origins are represented:

- `spec-*.data`: separately authored PCAP/PCAPNG byte specimens. The builder does
  not import the product parser, decoder, tests, or `capture_workloads` generator.
- `text2pcap-*.data`: unmodified output from installed Wireshark `text2pcap` 4.6.7
  (`v4.6.7-0-gb439fb7b47a9`), using the original hand-authored frame hexdump
  `fictional-frames.txt`. Timestamps are explicit UTC dates, not generation time.

`manifest.json` records the origin, exact SHA-256, size, expected packet count or
failure category, and compatibility features of each specimen.
`reference-decoder.json` records actual offline TShark 4.6.7 results, including
packet counts, interface references, exact timestamp strings, frame lengths,
addresses, transport ports, VLAN, and ARP fields. No name resolution is enabled.
Tests use these committed receipts; users and hosted test runners do not need
Wireshark, capture drivers, administrator privileges, or external Python packages.

Rebuild only when intentionally updating provenance and all dependent hashes:

```powershell
.venv\Scripts\python.exe -m tools.independent_capture_corpus --output tests/fixtures/capture-interoperability --wireshark-bin 'C:\Program Files\Wireshark'
```

On other systems omit `--wireshark-bin` when the tools are on PATH. Different
Wireshark versions or operating systems may add different container metadata;
byte-for-byte equivalence across generators is not promised. Rebuilding into a
separate directory permits reviewing the differences before updating fixtures.

Reference specifications:

- [PCAP format, draft-ietf-opsawg-pcap-09](https://www.ietf.org/archive/id/draft-ietf-opsawg-pcap-09.html)
- [PCAPNG format, draft-ietf-opsawg-pcapng-06](https://www.ietf.org/archive/id/draft-ietf-opsawg-pcapng-06.html)
- [Wireshark text2pcap manual](https://www.wireshark.org/docs/man-pages/text2pcap.html)
- [ARP, RFC 826](https://www.rfc-editor.org/rfc/rfc826)
- [IPv4, RFC 791](https://www.rfc-editor.org/rfc/rfc791)
- [IPv6, RFC 8200](https://www.rfc-editor.org/rfc/rfc8200)

Scope: interoperability with these independently produced synthetic specimens,
not broad operational or real-world capture validation. Header checksums are not
an oracle: the product deliberately does not validate them because offload can
leave incomplete checksums. Fragmented and incomplete transport metadata is
deliberately more conservative than Wireshark's display.
