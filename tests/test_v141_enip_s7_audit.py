"""Independent review oracles for the other decoder team's wire boundaries.

These fixtures are intentionally separate from that team's test builders.
"""

import struct

import pytest

from otarchguard.capture.protocols.contract import ENRICHMENT_LIMITS, ProtocolView, Status
from otarchguard.capture.protocols.enip import decode_enip
from otarchguard.capture.protocols.s7comm import decode_s7comm


def _enip(command: int, payload: bytes) -> bytes:
    return struct.pack("<HHII8sI", command, len(payload), 0, 0, b"\0" * 8, 0) + payload


def _identity(value: bytes) -> bytes:
    return _enip(0x63, struct.pack("<HHH", 1, 12, len(value)) + value)


def _s7(pdu: bytes, cotp: bytes = b"\x02\xf0\x80") -> bytes:
    return b"\x03\0" + struct.pack("!H", 4 + len(cotp) + len(pdu)) + cotp + pdu


def test_enip_reviewed_list_identity_envelope() -> None:
    # Encapsulation version1; sockaddr AF_INET, port44818, documentation IP;
    # eight reserved zero octets; fixed identity fields; zero-length name+state.
    value = b"\1\0\0\2\xaf\x12\xc0\0\2\1" + b"\0" * 22 + b"\0\0"
    (record,) = decode_enip(ProtocolView(_identity(value), "tcp", 44818, 1), ENRICHMENT_LIMITS)
    assert record.status == Status.STRUCTURALLY_VALID
    assert "protocol_source" not in dict(record.fields)


@pytest.mark.parametrize("offset,new", [(0, b"\xff\xff"), (2, b"\xff\xff"), (10, b"\xff\x00")])
def test_enip_identity_unknown_wire_variant_does_not_acquire_positive(
    offset: int, new: bytes
) -> None:
    value = bytearray(b"\1\0\0\2\xaf\x12\xc0\0\2\1" + b"\0" * 24)
    value[offset : offset + 2] = new
    (record,) = decode_enip(
        ProtocolView(_identity(bytes(value)), "tcp", 44818, 1), ENRICHMENT_LIMITS
    )
    assert record.status != Status.STRUCTURALLY_VALID
    assert record.fields == ()


@pytest.mark.parametrize("body", [b"\1\0\xb2\0\xff\xff", b"\2\0\0\0\0\0\xb2\0\x04\0\x0e\1\x20"])
def test_enip_cpf_nested_lengths_cannot_be_repaired_by_outer_validity(body: bytes) -> None:
    message = _enip(0x6F, b"\0" * 6 + body)
    (record,) = decode_enip(ProtocolView(message, "tcp", 1, 44818), ENRICHMENT_LIMITS)
    assert record.status == Status.MALFORMED and not record.fields


@pytest.mark.parametrize("rosctr", [2, 3])
def test_s7_ack_requires_complete_extended_header(rosctr: int) -> None:
    pdu = bytes([0x32, rosctr]) + b"\0" * 8
    (record,) = decode_s7comm(ProtocolView(_s7(pdu), "tcp", 1, 102), ENRICHMENT_LIMITS)
    assert record.status == Status.MALFORMED and not record.fields


@pytest.mark.parametrize("cotp", [b"\0\xf0\x80", b"\xff\xf0\x80", b"\x02\xf0\x00", b"\x02\xf0\x81"])
def test_s7_cotp_length_and_segment_boundary(cotp: bytes) -> None:
    pdu = bytes.fromhex("32010000000100080000f0000001000101e0")
    (record,) = decode_s7comm(ProtocolView(_s7(pdu, cotp), "tcp", 1, 102), ENRICHMENT_LIMITS)
    assert record.status in {Status.MALFORMED, Status.UNSUPPORTED_VARIANT}
    assert not record.fields


def test_s7_error_response_does_not_inherit_embedded_function() -> None:
    pdu = bytes.fromhex("320300000001000000008104")
    (record,) = decode_s7comm(ProtocolView(_s7(pdu), "tcp", 102, 1), ENRICHMENT_LIMITS)
    assert record.status == Status.STRUCTURALLY_VALID
    assert record.message_category == "pdu_header" and "function_code" not in dict(record.fields)


@pytest.mark.parametrize("identifier", [0x72, 0x00, 0xFF])
def test_s7_plus_and_unknown_identifier_abstain(identifier: int) -> None:
    pdu = bytes([identifier]) + bytes.fromhex("010000000100080000f0000001000101e0")
    (record,) = decode_s7comm(ProtocolView(_s7(pdu), "tcp", 1, 102), ENRICHMENT_LIMITS)
    assert record.status == Status.UNSUPPORTED_VARIANT and not record.fields
