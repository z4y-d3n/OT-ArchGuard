"""Opt-in development acquisition of exact reviewed public test captures.

The runtime never imports or invokes this module. Capture bytes stay outside
source/package paths. No redirects, archives, first-use trust or overwrites.
Acquisition approval permits local analysis, not third-party redistribution.
"""

import argparse
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from tools.protocol_corpus import MAX_FILE_BYTES, _local, load_manifest, verify_file

MAX_FILES = 8
# Filled from separately quarantined, hashed and reviewed bytes. A manifest edit
# alone cannot authorize a different URL, byte identity, or download size.
REVIEWED: dict[str, tuple[str, str, int]] = {
    "cisa-enip-multiple": (
        "https://raw.githubusercontent.com/cisagov/icsnpp-enip/3fbd32e3d2838d5e2bcd6c9ed79f036d23a0642e/testing/traces/multiple_service_packet_cip.pcapng",
        "4eed29d01d6fe3c827e3c947694526e7669d937ff8973d5c420979565597087c",
        344,
    ),
    "cisa-enip-set-attribute": (
        "https://raw.githubusercontent.com/cisagov/icsnpp-enip/3fbd32e3d2838d5e2bcd6c9ed79f036d23a0642e/testing/traces/set_attribute_single_service_cip.pcapng",
        "9b24d02e6f15a40f2109c2476bb117e2273bc9485077a50044269d3738cea8dc",
        500,
    ),
    "cisa-snap7": (
        "https://raw.githubusercontent.com/cisagov/icsnpp-s7comm/102a35c8f967f20640bd2427bb28a7c609b37493/testing/traces/snap7.pcap",
        "2b91f6a8a203ec83e4f2dbb69d5e61602845f23da0baa31d95d029fb24cbd427",
        8260,
    ),
    "cisa-s7-plus-mixed": (
        "https://raw.githubusercontent.com/cisagov/icsnpp-s7comm/102a35c8f967f20640bd2427bb28a7c609b37493/testing/traces/s7comm_plus.pcap",
        "2f9befe0667443fb86b7184b6ff7fcc4eb61fae67d3ce30793ce7b2937067b0c",
        33464,
    ),
    "cisa-open62541": (
        "https://raw.githubusercontent.com/cisagov/icsnpp-opcua-binary/d7fd8894d23baabcaf59989abc3cbab6b469c074/testing/traces/open62541_client-server_mainloop.pcap",
        "07dd69db7de730928601e4f66d94382d94257a344ae3a5f9147b7dec108bcefd",
        22412,
    ),
    "cisa-open62541-nonstandard": (
        "https://raw.githubusercontent.com/cisagov/icsnpp-opcua-binary/d7fd8894d23baabcaf59989abc3cbab6b469c074/testing/traces/open62541_client-server_mainloop-no-handshake-12345.pcap",
        "da507c9d8798e978ef452efa761da3ab8a3b28c5ad9cb68c150edfb27c7619a9",
        17159,
    ),
    "cisa-dnp3": (
        "https://raw.githubusercontent.com/cisagov/icsnpp-dnp3/b31dbadeceb1cbcda16aef89c650559cd177dd7e/testing/traces/dnp3_example.pcap",
        "d9b22ee7b5ece4a78d8f9995aff20d55bfb315752ce136f97c77eb5ce73511bf",
        115403,
    ),
    "cisa-opcua-gap": (
        "https://raw.githubusercontent.com/cisagov/icsnpp-opcua-binary/d7fd8894d23baabcaf59989abc3cbab6b469c074/testing/traces/opcua_with-gap_with-handshake.pcap",
        "030950345b2c79eaf3bedf8a04c2325cfe4a5d8b40225d250ed693daf350b6b6",
        83524,
    ),
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise ValueError("Capture download redirects are not approved")


def _fetch(url: str, size: int) -> bytes:
    opener = urllib.request.build_opener(_NoRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "OT-ArchGuard-corpus-review/1"})
    with opener.open(request, timeout=30) as response:
        if response.geturl() != url:
            raise ValueError("Unexpected capture download destination")
        length = response.headers.get("Content-Length")
        if length is not None and int(length) != size:
            raise ValueError("Capture download size does not match review")
        data: bytes = response.read(min(size, MAX_FILE_BYTES) + 1)
        if len(data) != size:
            raise ValueError("Capture download size does not match review")
        return data


def _entries(manifest: dict[str, Any], identities: list[str]) -> list[dict[str, Any]]:
    if not 1 <= len(identities) <= MAX_FILES or len(set(identities)) != len(identities):
        raise ValueError("Select one to eight distinct reviewed captures")
    entries = []
    for identity in identities:
        matches = [entry for entry in manifest["entries"] if entry["id"] == identity]
        if len(matches) != 1 or matches[0]["review_status"] != "approved_external":
            raise ValueError("Capture is not approved for local external analysis")
        entry = matches[0]
        if REVIEWED.get(identity) != (entry["source_url"], entry["sha256"], entry["size_bytes"]):
            raise ValueError("Capture is outside the fixed reviewed download allowlist")
        entries.append(entry)
    return entries


def acquire(
    manifest: dict[str, Any], identities: list[str], directory: Path, *, allow_network: bool = False
) -> list[dict[str, Any]]:
    """Acquire only explicitly opted-in, already hash-pinned allowlisted bytes.

    Files are published individually with atomic no-replace publication. If a later
    capture fails, earlier verified files remain and the operation raises; no
    successful complete-run receipt is returned. This is a single-writer tool.
    """
    if not allow_network:
        raise ValueError("Network acquisition requires explicit --allow-network")
    entries = _entries(manifest, identities)
    _local(directory)
    if not directory.is_dir():
        raise ValueError("Capture directory must already exist")
    destinations = [directory / Path(entry["original_filename"]).name for entry in entries]
    if len(set(destinations)) != len(destinations) or any(path.exists() for path in destinations):
        raise ValueError("Capture publication cannot overwrite existing paths")
    results = []
    for entry, destination in zip(entries, destinations, strict=True):
        data = _fetch(entry["source_url"], entry["size_bytes"])
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Capture download SHA-256 does not match review")
        descriptor, pending_name = tempfile.mkstemp(
            prefix=".capture-review-", suffix=".tmp", dir=directory
        )
        pending = Path(pending_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            result = verify_file(manifest, entry["id"], pending)
            _local(directory)
            if os.name == "nt":
                # Windows rename fails when the target already exists.
                os.rename(pending, destination)
            else:
                os.link(pending, destination)
            results.append(
                {**result, "filename": destination.name, "redistribution": entry["redistribution"]}
            )
        finally:
            pending.unlink(missing_ok=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--id", action="append", required=True, dest="identities")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    try:
        results = acquire(
            load_manifest(args.manifest),
            args.identities,
            args.directory,
            allow_network=args.allow_network,
        )
    except (OSError, ValueError, urllib.error.URLError) as error:
        parser.exit(2, str(error) + "\n")
    print(
        json.dumps(
            {"status": "verified_local_reference_bytes", "captures": results}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
