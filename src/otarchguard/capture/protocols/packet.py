"""Read-only bridge from existing transient packets to independent enrichment.

The frozen observation decoder gates IP/TCP structure. The additional locator
only slices validated boundaries. Supported subset: Ethernet (up to two VLANs),
raw IP, IPv4 TCP, direct IPv6 TCP and PROFINET DCP. IPv6 extensions abstain here.
"""

from dataclasses import dataclass

from otarchguard.capture.contract import CaptureLimits, Packet
from otarchguard.capture.observations import _decode
from otarchguard.capture.protocols.contract import ProtocolView
from otarchguard.capture.protocols.dcp import DCP_FRAME_IDS


@dataclass(frozen=True, slots=True)
class PacketView:
    view: ProtocolView | None
    reason: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    vlans: tuple[int, ...] = ()


def packet_view(packet: Packet, limits: CaptureLimits) -> PacketView:
    data = packet.data
    if packet.link_errors:
        return PacketView(None, "CAPTURE_LINK_ERRORS_REPORTED")
    if packet.offloaded:
        return PacketView(None, "CAPTURE_SEGMENTATION_OFFLOAD_UNSUPPORTED")
    if packet.captured_length != packet.original_length:
        return PacketView(None, "CAPTURE_RECORD_TRUNCATED")
    offset, ethertype = 0, None
    tags: list[int] = []
    if packet.linktype == 1:
        if len(data) < 14:
            return PacketView(None, "ETHERNET_HEADER_TRUNCATED")
        offset, ethertype = 14, int.from_bytes(data[12:14], "big")
        while ethertype in {0x8100, 0x88A8}:
            if len(tags) == 2:
                return PacketView(None, "VLAN_DEPTH_UNSUPPORTED")
            if offset + 4 > len(data):
                return PacketView(None, "VLAN_HEADER_TRUNCATED")
            tags.append(int.from_bytes(data[offset : offset + 2], "big") & 4095)
            ethertype = int.from_bytes(data[offset + 2 : offset + 4], "big")
            offset += 4
        if ethertype == 0x8892:
            if len(data) - offset < 2:
                return PacketView(None, "PROFINET_FRAME_ID_MISSING")
            if int.from_bytes(data[offset : offset + 2], "big") not in DCP_FRAME_IDS:
                return PacketView(None, "NON_DCP_PROFINET_FRAME_ID")
            return PacketView(
                ProtocolView(data[offset:], "ethernet", ethertype=ethertype), vlans=tuple(tags)
            )
    elif packet.linktype == 101 and data:
        ethertype = {4: 0x0800, 6: 0x86DD}.get(data[0] >> 4)
    else:
        return PacketView(None, "LINKTYPE_UNSUPPORTED")
    outer = _decode(packet, limits)
    if outer.status != "decoded":
        return PacketView(None, outer.reason or "NETWORK_FRAME_UNASSESSED")
    if outer.transport != "tcp":
        return PacketView(None, "TRANSPORT_OUTSIDE_ENRICHMENT_SUBSET")
    if ethertype == 0x0800:
        end = offset + int.from_bytes(data[offset + 2 : offset + 4], "big")
        offset += (data[offset] & 15) * 4
    elif ethertype == 0x86DD:
        if data[offset + 6] != 6:
            return PacketView(None, "IPV6_EXTENSIONS_OUTSIDE_ENRICHMENT_SUBSET")
        end = offset + 40 + int.from_bytes(data[offset + 4 : offset + 6], "big")
        offset += 40
    else:
        return PacketView(None, "NETWORK_OUTSIDE_ENRICHMENT_SUBSET")
    offset += (data[offset + 12] >> 4) * 4
    return PacketView(
        ProtocolView(data[offset:end], "tcp", outer.source_port, outer.destination_port),
        source_ip=outer.source_ip,
        destination_ip=outer.destination_ip,
        vlans=outer.vlans,
    )
