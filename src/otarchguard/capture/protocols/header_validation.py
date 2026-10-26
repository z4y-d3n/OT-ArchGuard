"""Strict metadata allowlists for decoder revision 2; no packet bytes consumed."""

from typing import Any


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("Invalid or unsupported protocol enrichment artifact.")


def _int(value: object, maximum: int = 65535) -> bool:
    return type(value) is int and 0 <= value <= maximum


def validate_header(protocol: str, fields: dict[str, Any], category: str) -> int:
    """Return complete frame size after validating every exported header field."""
    if protocol == "ethernet_ip":
        from otarchguard.capture.protocols.enip import CIP_OPERATIONS, COMMAND_CATEGORIES

        required = {
            "encapsulation_command",
            "encapsulation_status",
            "encapsulation_length",
            "cip_metadata",
        }
        extra = {"cip_service", "cip_response", "cip_operation"}
        recognized = fields.get("cip_metadata") == "recognized"
        _require(set(fields) == (required | extra if recognized else required))
        command = fields["encapsulation_command"]
        _require(_int(command) and command in COMMAND_CATEGORIES)
        _require(category == COMMAND_CATEGORIES[command])
        _require(_int(fields["encapsulation_status"], 2**32 - 1))
        length = fields["encapsulation_length"]
        _require(_int(length))
        metadata = fields["cip_metadata"]
        _require(metadata in {"not_present", "recognized", "unsupported", "opaque"})
        if recognized:
            service = fields["cip_service"]
            _require(_int(service, 255) and (service & 127) in CIP_OPERATIONS)
            _require(type(fields["cip_response"]) is bool)
            _require(fields["cip_response"] == bool(service & 128))
            _require(fields["cip_operation"] == CIP_OPERATIONS[service & 127])
            _require(command == 0x6F and length >= 20)
        if metadata == "opaque":
            _require(command == 0x70 and length >= 22)
        elif metadata == "unsupported":
            _require(command == 0x6F and length >= 18)
        elif metadata == "not_present":
            _require(
                command not in {0x6F, 0x70} or (fields["encapsulation_status"] != 0 and length == 0)
            )
        if fields["encapsulation_status"] == 0:
            if command in {0, 0x66}:
                _require(length == 0)
            elif command == 0x65:
                _require(length == 4)
        return 24 + int(length)
    if protocol == "s7comm":
        from otarchguard.capture.protocols.s7comm import FUNCTION_CATEGORIES, PDU_CATEGORIES

        required = {
            "protocol_id",
            "rosctr",
            "pdu_category",
            "parameter_length",
            "data_length",
            "tpkt_length",
        }
        _require(set(fields) in (required, required | {"function_code"}))
        _require(_int(fields["protocol_id"]) and fields["protocol_id"] == 0x32)
        rosctr = fields["rosctr"]
        _require(_int(rosctr, 255) and rosctr in {1, 2, 3})
        _require(fields["pdu_category"] == PDU_CATEGORIES[rosctr])
        _require(all(_int(fields[k]) for k in ("parameter_length", "data_length", "tpkt_length")))
        _require(
            fields["tpkt_length"]
            == 7
            + (12 if rosctr in {2, 3} else 10)
            + fields["parameter_length"]
            + fields["data_length"]
        )
        if "function_code" in fields:
            code = fields["function_code"]
            _require(_int(code, 255) and code in FUNCTION_CATEGORIES and rosctr in {1, 3})
            _require(category == FUNCTION_CATEGORIES[code])
            _require(fields["parameter_length"] >= 2)
            if code == 0xF0:
                _require(fields["parameter_length"] == 8 and fields["data_length"] == 0)
        else:
            _require(category == "pdu_header" and rosctr in {2, 3})
            _require(fields["parameter_length"] == fields["data_length"] == 0)
        return int(fields["tpkt_length"])
    if protocol == "iec104":
        from otarchguard.capture.protocols.iec104 import _ASDU_WIDTHS, _U_FUNCTIONS

        form = fields.get("frame_format")
        extra_fields = {"I": {"asdu_type"}, "S": set(), "U": {"u_function"}}
        _require(isinstance(form, str) and form in extra_fields)
        if not isinstance(form, str):
            raise ValueError("Invalid frame format")
        _require(set(fields) == {"frame_format", "apdu_length"} | extra_fields[form])
        size = fields["apdu_length"]
        _require(_int(size, 255) and size >= 6)
        _require(
            category
            == {"I": "information_transfer", "S": "supervisory", "U": "unnumbered_control"}[form]
        )
        if form == "I":
            _require(_int(fields["asdu_type"], 255) and fields["asdu_type"] in _ASDU_WIDTHS)
            _require(size >= 15 + _ASDU_WIDTHS[fields["asdu_type"]])
        else:
            _require(size == 6)
            if form == "U":
                _require(fields["u_function"] in _U_FUNCTIONS.values())
        return int(size)
    if protocol == "opcua_binary":
        _require(set(fields) == {"message_type", "chunk_type", "message_size"})
        kind, chunk, size = fields["message_type"], fields["chunk_type"], fields["message_size"]
        minimum = {"HEL": 32, "ACK": 28, "ERR": 16, "RHE": 16, "OPN": 33, "MSG": 25, "CLO": 25}
        _require(isinstance(kind, str) and kind in minimum)
        _require(_int(size, 16384) and size >= minimum[kind])
        if kind in {"HEL", "ACK", "ERR", "RHE"}:
            _require(chunk == "F")
            _require(category == ("connection_error" if kind == "ERR" else "connection_handshake"))
            if kind == "ACK":
                _require(size == 28)
        else:
            _require(chunk in {"F", "C"} and category == "secure_channel_opaque")
            _require(kind == "MSG" or chunk == "F")
        return int(size)
    _require(protocol == "dnp3")
    from otarchguard.capture.protocols.dnp3 import _APPLICATION, _PRIMARY, _SECONDARY

    required = {
        "link_status",
        "protocol_source",
        "protocol_destination",
        "link_function",
        "link_primary",
        "frame_length",
    }
    user = category == "user_data"
    _require(category in {"link_management", "user_data"})
    _require(
        set(fields)
        == (required | {"application_function", "application_category"} if user else required)
    )
    _require(fields["link_status"] == "crc_valid" and type(fields["link_primary"]) is bool)
    _require(all(_int(fields[k]) for k in ("protocol_source", "protocol_destination")))
    function = fields["link_function"]
    _require(
        _int(function, 15) and function in (_PRIMARY if fields["link_primary"] else _SECONDARY)
    )
    _require(user == (fields["link_primary"] and function in {3, 4}))
    size = fields["frame_length"]
    _require(_int(size, 292))
    if user:
        _require(size in {10 + n + 2 * ((n + 15) // 16) for n in range(3, 251)})
        code = fields["application_function"]
        _require(_int(code, 255) and code in _APPLICATION)
        _require(fields["application_category"] == _APPLICATION[code])
    else:
        _require(size == 10)
    return int(size)
