"""Independent original wire fixtures for EtherNet/IP and classic S7comm.

Builders specify wire layouts and never call product code to construct an oracle.
"""

import json
import random
import struct
from dataclasses import asdict, replace

import pytest

from otarchguard.capture.protocols.contract import ENRICHMENT_LIMITS, ProtocolView, Status
from otarchguard.capture.protocols.enip import decode_enip
from otarchguard.capture.protocols.s7comm import decode_s7comm


def encapsulation(command: int, body: bytes = b"", *, status: int = 0, options: int = 0) -> bytes:
    return struct.pack("<HHII8sI", command, len(body), 1234, status, b"PRIVATE!", options) + body


def cpf(items: list[tuple[int, bytes]]) -> bytes:
    return struct.pack("<H", len(items)) + b"".join(
        struct.pack("<HH", kind, len(value)) + value for kind, value in items
    )


def unconnected(cip: bytes = bytes.fromhex("0e03200124013001")) -> bytes:
    return encapsulation(0x6F, b"\x00" * 6 + cpf([(0, b""), (0xB2, cip)]))


def s7(
    parameter: bytes = bytes.fromhex("f0000001000101e0"),
    data: bytes = b"",
    *,
    rosctr: int = 1,
    error: bytes = b"\x00\x00",
    cotp: bytes = b"\x02\xf0\x80",
) -> bytes:
    pdu = struct.pack("!BBHHHH", 0x32, rosctr, 0, 1, len(parameter), len(data))
    if rosctr in {2, 3}:
        pdu += error
    body = cotp + pdu + parameter + data
    return b"\x03\x00" + struct.pack("!H", len(body) + 4) + body


# S7ANY variable specification: marker, size, syntax, then private identifiers.
ANY = bytes.fromhex("120a10020001000184000000")
READ = s7(b"\x04\x01" + ANY)
WRITE = s7(b"\x05\x01" + ANY, bytes.fromhex("00040008aa"))


def enip_decode(data: bytes, *, reverse: bool = False) -> tuple[object, ...]:
    source, destination = (44818, 42000) if reverse else (42000, 44818)
    return decode_enip(ProtocolView(data, "tcp", source, destination), ENRICHMENT_LIMITS)


@pytest.mark.parametrize(
    ("command", "body", "category"),
    [
        (0, b"", "nop"),
        (4, b"", "list_services"),
        (0x63, b"", "list_identity"),
        (0x64, b"", "list_interfaces"),
        (0x65, b"\x01\x00\x00\x00", "register_session"),
        (0x66, b"", "unregister_session"),
        (4, cpf([(0x100, b"\x01\x00\x20\x00" + b"Communications!!")]), "list_services"),
        (0x63, cpf([(0x0C, b"\x01\x00\x00\x02" + b"\x00" * 28 + b"\x03ABC\x00")]), "list_identity"),
        (0x64, cpf([]), "list_interfaces"),
    ],
)
def test_enip_command_specific_envelopes(command: int, body: bytes, category: str) -> None:
    for source, destination in [(42000, 44818), (44818, 42000)]:
        (result,) = decode_enip(
            ProtocolView(encapsulation(command, body), "tcp", source, destination),
            ENRICHMENT_LIMITS,
        )
        assert result.status == Status.STRUCTURALLY_VALID
        assert result.message_category == category
        assert dict(result.fields)["encapsulation_command"] == command
        assert dict(result.fields)["encapsulation_length"] == len(body)


@pytest.mark.parametrize("service", [1, 2, 5, 14, 16])
@pytest.mark.parametrize("response", [False, True])
def test_enip_explicit_cip_supported_services(service: int, response: bool) -> None:
    cip = (
        bytes([service | 0x80, 0, 1, 1, 0x34, 0x12])
        if response
        else bytes([service, 2, 0x20, 1, 0x24, 1])
    )
    (result,) = decode_enip(ProtocolView(unconnected(cip), "tcp", 44818, 42000), ENRICHMENT_LIMITS)
    assert result.status == Status.STRUCTURALLY_VALID
    fields = dict(result.fields)
    assert fields["cip_metadata"] == "recognized"
    assert fields["cip_service"] == cip[0]
    assert fields["cip_response"] is response
    assert fields["cip_operation"] in {"read_type", "write_type", "reset_type"}
    assert "execution" in " ".join(result.limitations)


def test_enip_outer_recognition_does_not_assert_cip_recognition() -> None:
    for cip in [bytes.fromhex("4c012001"), bytes.fromhex("0e019102")]:
        (result,) = decode_enip(ProtocolView(unconnected(cip), "tcp", 1, 44818), ENRICHMENT_LIMITS)
        assert result.status == Status.STRUCTURALLY_VALID
        assert dict(result.fields)["cip_metadata"] == "unsupported"
        assert "cip_service" not in dict(result.fields)
    connected = encapsulation(
        0x70, b"\x00" * 6 + cpf([(0xA1, b"\x00" * 4), (0xB1, b"\x01\x00\x0e\x01\x20\x01")])
    )
    (result,) = decode_enip(ProtocolView(connected, "tcp", 1, 44818), ENRICHMENT_LIMITS)
    assert result.status == Status.STRUCTURALLY_VALID
    assert dict(result.fields)["cip_metadata"] == "opaque"
    assert "cip_service" not in dict(result.fields)


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        (b"", Status.PORT_HINT),
        (b"HTTP/1.1 200 OK\r\n\r\n", Status.TRUNCATED),
        (encapsulation(0xFFFF), Status.UNSUPPORTED_VARIANT),
        (encapsulation(0x65, b"\x01"), Status.MALFORMED),
        (encapsulation(0x65, b"\x02\x00\x00\x00"), Status.UNSUPPORTED_VARIANT),
        (encapsulation(0x66, b"x"), Status.MALFORMED),
        (encapsulation(0, options=1), Status.UNSUPPORTED_VARIANT),
        (encapsulation(0x6F, b"\x00" * 7), Status.MALFORMED),
        (encapsulation(0x6F, b"\x01" + b"\x00" * 7), Status.UNSUPPORTED_VARIANT),
        (encapsulation(0x6F, b"\x00" * 6 + b"\x02\x00"), Status.MALFORMED),
        (encapsulation(0x6F, b"\x00" * 6 + cpf([(0, b""), (0xB2, b"x")])), Status.MALFORMED),
        (unconnected(bytes.fromhex("0e042001")), Status.MALFORMED),
        (unconnected(bytes.fromhex("8e000002")), Status.MALFORMED),
        (unconnected(bytes.fromhex("8e010000")), Status.MALFORMED),
        (unconnected(bytes.fromhex("0e02210101ff")), Status.MALFORMED),
        (encapsulation(4, cpf([(0x100, b"\x01\x00")])), Status.MALFORMED),
        (encapsulation(0x63, cpf([(0x0C, b"\x00" * 34 + b"X")])), Status.MALFORMED),
        (encapsulation(0x64, cpf([(0xFFFF, b"")])), Status.UNSUPPORTED_VARIANT),
        (
            encapsulation(0x6F, b"\x00" * 6 + cpf([(0, b""), (0xB2, b"\x0e\x01\x20\x01")]) + b"x"),
            Status.MALFORMED,
        ),
        (encapsulation(0x6F, b"\x00" * 6 + b"\x01\x00\x00\x00\xff\xff"), Status.MALFORMED),
    ],
)
def test_enip_negative_envelopes(payload: bytes, status: Status) -> None:
    (result,) = decode_enip(ProtocolView(payload, "tcp", 1, 44818), ENRICHMENT_LIMITS)
    assert result.status == status
    assert not result.fields and result.message_category is None


def test_enip_nonzero_encapsulation_status_is_not_cip_success() -> None:
    (result,) = decode_enip(
        ProtocolView(encapsulation(0x6F, status=0x64), "tcp", 44818, 1), ENRICHMENT_LIMITS
    )
    assert result.status == Status.STRUCTURALLY_VALID
    assert dict(result.fields)["encapsulation_status"] == 0x64
    assert dict(result.fields)["cip_metadata"] == "not_present"


@pytest.mark.parametrize("cut", [1, 2, 3, 7, 23, 24, 25, 31, 39])
def test_enip_split_is_never_complete(cut: int) -> None:
    (result,) = decode_enip(ProtocolView(unconnected()[:cut], "tcp", 1, 44818), ENRICHMENT_LIMITS)
    assert result.status == Status.TRUNCATED
    assert not result.fields


@pytest.mark.parametrize(
    ("payload", "category", "rosctr", "function"),
    [
        (s7(), "setup_communication", 1, 0xF0),
        (s7(rosctr=3), "setup_communication", 3, 0xF0),
        (READ, "read_type", 1, 4),
        (WRITE, "write_type", 1, 5),
        (s7(b"\x04\x01", bytes.fromhex("ff040008aa"), rosctr=3), "read_type", 3, 4),
        (s7(b"\x05\x01", b"\xff", rosctr=3), "write_type", 3, 5),
        (s7(b"", rosctr=2, error=b"\x81\x04"), "pdu_header", 2, None),
        (s7(b"", rosctr=3, error=b"\x81\x04"), "pdu_header", 3, None),
    ],
)
def test_s7_requests_responses_and_error_headers(
    payload: bytes, category: str, rosctr: int, function: int | None
) -> None:
    for source, destination in [(42000, 102), (102, 42000)]:
        (result,) = decode_s7comm(
            ProtocolView(payload, "tcp", source, destination), ENRICHMENT_LIMITS
        )
        assert result.status == Status.STRUCTURALLY_VALID
        assert result.message_category == category
        fields = dict(result.fields)
        assert fields["rosctr"] == rosctr
        assert fields["tpkt_length"] == len(payload)
        assert fields.get("function_code") == function


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        (b"", Status.PORT_HINT),
        (b"HTTP/1.1 200 OK", Status.PORT_HINT),
        (b"\x03\x01\x00\x07\x02\xf0\x80", Status.MALFORMED),
        (b"\x03\x00\x00\x06\x02\xf0", Status.MALFORMED),
        (s7(cotp=b"\xff\xf0\x80"), Status.MALFORMED),
        (s7(cotp=b"\x02\xe0\x80"), Status.UNSUPPORTED_VARIANT),
        (s7(cotp=b"\x02\xf0\x00"), Status.UNSUPPORTED_VARIANT),
        (s7(cotp=b"\x03\xf0\x80\x00"), Status.UNSUPPORTED_VARIANT),
        (s7(rosctr=9), Status.UNSUPPORTED_VARIANT),
        (s7(b"\x00\x01\x12\x04" + b"\x00" * 4, rosctr=7), Status.UNSUPPORTED_VARIANT),
        (s7(b"\xff"), Status.UNSUPPORTED_VARIANT),
        (s7(b"\xf0"), Status.MALFORMED),
        (s7(b"\x04\x00"), Status.MALFORMED),
        (s7(b"\x04\x02" + ANY), Status.MALFORMED),
        (s7(b"\x04\x01" + b"\x13" + ANY[1:]), Status.UNSUPPORTED_VARIANT),
        (s7(b"\x05\x01" + ANY), Status.MALFORMED),
        (s7(b"\x04\x01", b"\xff", rosctr=3), Status.MALFORMED),
        (s7(b"\x05\x01", b"\xff\xff", rosctr=3), Status.MALFORMED),
        (s7(b"\x04\x01", bytes.fromhex("ff040010aa"), rosctr=3), Status.MALFORMED),
        (s7(b"\x04\x01", bytes.fromhex("fffe0000"), rosctr=3), Status.MALFORMED),
        (s7(b"\x04\x01", bytes.fromhex("ff000001aa"), rosctr=3), Status.MALFORMED),
        (s7(b"\x04\x01", rosctr=2), Status.UNSUPPORTED_VARIANT),
    ],
)
def test_s7_negative_envelopes(payload: bytes, status: Status) -> None:
    (result,) = decode_s7comm(ProtocolView(payload, "tcp", 1, 102), ENRICHMENT_LIMITS)
    assert result.status == status
    assert not result.fields and result.message_category is None


def test_s7comm_plus_is_never_classic() -> None:
    payload = bytearray(s7())
    payload[7] = 0x72
    (result,) = decode_s7comm(ProtocolView(bytes(payload), "tcp", 1, 102), ENRICHMENT_LIMITS)
    assert result.status == Status.UNSUPPORTED_VARIANT
    assert not result.fields


@pytest.mark.parametrize("index", [1, 9, 10, 13, 14, 15, 16])
def test_s7_contradictory_reserved_and_lengths(index: int) -> None:
    payload = bytearray(s7())
    payload[index] ^= 1
    (result,) = decode_s7comm(ProtocolView(bytes(payload), "tcp", 1, 102), ENRICHMENT_LIMITS)
    assert result.status != Status.STRUCTURALLY_VALID
    assert not result.fields


@pytest.mark.parametrize("cut", [1, 2, 3, 4, 6, 7, 10, 20, 24])
def test_s7_split_is_never_complete(cut: int) -> None:
    (result,) = decode_s7comm(ProtocolView(s7()[:cut], "tcp", 1, 102), ENRICHMENT_LIMITS)
    assert result.status == Status.TRUNCATED
    assert not result.fields


@pytest.mark.parametrize("protocol", ["enip", "s7"])
def test_nonstandard_ports_transport_and_no_speculative_offset(protocol: str) -> None:
    decoder, payload, port = (
        (decode_enip, unconnected(), 44818) if protocol == "enip" else (decode_s7comm, READ, 102)
    )
    assert decoder(ProtocolView(payload, "tcp", 1, 2), ENRICHMENT_LIMITS) == ()
    assert decoder(ProtocolView(payload, "ethernet", 1, port), ENRICHMENT_LIMITS) == ()
    (result,) = decoder(ProtocolView(b"junk" + payload, "tcp", 1, port), ENRICHMENT_LIMITS)
    assert result.status != Status.STRUCTURALLY_VALID


@pytest.mark.parametrize("protocol", ["enip", "s7"])
def test_coalescing_limits_and_determinism(protocol: str) -> None:
    decoder, payload, port = (
        (decode_enip, unconnected(), 44818) if protocol == "enip" else (decode_s7comm, READ, 102)
    )
    view = ProtocolView(payload * 2, "tcp", 1, port)
    records = decoder(view, ENRICHMENT_LIMITS)
    assert len(records) == 2 and all(r.status == Status.STRUCTURALLY_VALID for r in records)
    assert [r.record_offset for r in records] == [0, len(payload)]
    assert records == decoder(view, ENRICHMENT_LIMITS)
    (bounded,) = decoder(view, replace(ENRICHMENT_LIMITS, records_per_packet=1))
    assert (
        bounded.status == Status.UNSUPPORTED_VARIANT and bounded.reason == "RECORD_ITERATION_LIMIT"
    )
    (bounded,) = decoder(view, replace(ENRICHMENT_LIMITS, view_bytes=1))
    assert bounded.status == Status.UNSUPPORTED_VARIANT and bounded.reason == "VIEW_BYTE_LIMIT"


def test_enip_cpf_count_is_bounded() -> None:
    (result,) = decode_enip(
        ProtocolView(unconnected(), "tcp", 1, 44818), replace(ENRICHMENT_LIMITS, dcp_blocks=1)
    )
    assert (
        result.status == Status.UNSUPPORTED_VARIANT and result.reason == "CPF_ITEM_ITERATION_LIMIT"
    )


def test_s7_multiple_variable_data_alignment() -> None:
    payload = s7(b"\x04\x02", bytes.fromhex("ff040008aa00ff040008bb"), rosctr=3)
    (result,) = decode_s7comm(ProtocolView(payload, "tcp", 1, 102), ENRICHMENT_LIMITS)
    assert result.status == Status.STRUCTURALLY_VALID
    for data in [bytes.fromhex("ff040008aa01ff040008bb"), bytes.fromhex("ff040008aaff040008bb")]:
        (result,) = decode_s7comm(
            ProtocolView(s7(b"\x04\x02", data, rosctr=3), "tcp", 1, 102), ENRICHMENT_LIMITS
        )
        assert result.status == Status.MALFORMED


@pytest.mark.parametrize("protocol", ["enip", "s7"])
def test_privacy_random_bytes_and_mutation_terminate(protocol: str) -> None:
    decoder, payload, port = (
        (decode_enip, unconnected(), 44818) if protocol == "enip" else (decode_s7comm, WRITE, 102)
    )
    serialized = json.dumps(
        [asdict(r) for r in decoder(ProtocolView(payload, "tcp", 1, port), ENRICHMENT_LIMITS)]
    )
    assert "PRIVATE!" not in serialized
    assert "\\u00aa" not in serialized
    assert all(
        "address" not in name
        for result in decoder(ProtocolView(payload, "tcp", 1, port), ENRICHMENT_LIMITS)
        for name, _ in result.fields
    )
    rng = random.Random(14)
    candidates = [rng.randbytes(size) for size in range(256)]
    for index in range(len(payload)):
        mutated = bytearray(payload)
        mutated[index] ^= 0xFF
        candidates.append(bytes(mutated))
    for data in candidates:
        records = decoder(ProtocolView(data, "tcp", 1, port), ENRICHMENT_LIMITS)
        assert len(records) <= ENRICHMENT_LIMITS.records_per_packet
        assert all(not r.fields for r in records if r.status != Status.STRUCTURALLY_VALID)
        json.dumps([asdict(r) for r in records])
