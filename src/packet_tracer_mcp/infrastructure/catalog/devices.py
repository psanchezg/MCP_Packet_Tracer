"""Packet Tracer device catalog for PT 8.2.2 / 9.x."""

from __future__ import annotations

from dataclasses import dataclass

from ...shared.enums import PortSpeed


@dataclass(frozen=True)
class PortSpec:
    speed: str
    slot: str
    full_name: str = ""

    def __post_init__(self) -> None:
        if not self.full_name:
            speed_str = self.speed.value if hasattr(self.speed, "value") else self.speed
            object.__setattr__(self, "full_name", f"{speed_str}{self.slot}")


@dataclass(frozen=True)
class DeviceModel:
    pt_type: str
    category: str
    ports: tuple[PortSpec, ...]
    display_name: str = ""


def _port(speed: str, slot: str, full_name: str) -> PortSpec:
    return PortSpec(speed, slot, full_name=full_name)


def _fast(slot: str) -> PortSpec:
    return PortSpec(PortSpeed.FAST_ETHERNET, slot)


def _gig(slot: str) -> PortSpec:
    return PortSpec(PortSpeed.GIGABIT_ETHERNET, slot)


def _serial(slot: str) -> PortSpec:
    return PortSpec(PortSpeed.SERIAL, slot)


def _coax(slot: str) -> PortSpec:
    return PortSpec(PortSpeed.COAXIAL, slot)


def _named_fast(name: str) -> PortSpec:
    return _port(PortSpeed.FAST_ETHERNET, name, name)


def _named_gig(name: str) -> PortSpec:
    return _port(PortSpeed.GIGABIT_ETHERNET, name, name)


def _named_serial(name: str) -> PortSpec:
    return _port(PortSpeed.SERIAL, name, name)


def _named_coax(name: str) -> PortSpec:
    return _port(PortSpeed.COAXIAL, name, name)


def _custom(name: str, speed: str = "Custom") -> PortSpec:
    return _port(speed, name, name)


def _range(factory, prefix: str, start: int, end: int) -> tuple[PortSpec, ...]:
    return tuple(factory(f"{prefix}{index}") for index in range(start, end + 1))


def _fe_switch(prefix: str, count: int) -> tuple[PortSpec, ...]:
    return _range(_fast, prefix, 1, count)


def _ge_switch(prefix: str, start: int, end: int) -> tuple[PortSpec, ...]:
    return _range(_gig, prefix, start, end)


def _ethernet_block(start: int, end: int) -> tuple[PortSpec, ...]:
    return tuple(_named_fast(f"Ethernet{index}") for index in range(start, end + 1))


ROUTER_MODELS: tuple[DeviceModel, ...] = (
    DeviceModel("819", "router", tuple(_gig(str(i)) for i in range(4)), "Cisco 819 ISR"),
    DeviceModel("829", "router", tuple(_gig(str(i)) for i in range(4)), "Cisco 829 ISR"),
    DeviceModel("Router-PT", "router", (_fast("0/0"), _fast("0/1")), "Generic Router PT"),
    DeviceModel("1841", "router", (_fast("0/0"), _fast("0/1")), "Cisco 1841"),
    DeviceModel("1941", "router", (_gig("0/0"), _gig("0/1")), "Cisco 1941"),
    DeviceModel("2620XM", "router", (_fast("0/0"),), "Cisco 2620XM"),
    DeviceModel("2621XM", "router", (_fast("0/0"), _fast("0/1")), "Cisco 2621XM"),
    DeviceModel("2811", "router", (_fast("0/0"), _fast("0/1")), "Cisco 2811"),
    DeviceModel("2901", "router", (_gig("0/0"), _gig("0/1")), "Cisco 2901"),
    DeviceModel("2911", "router", (_gig("0/0"), _gig("0/1"), _gig("0/2")), "Cisco 2911"),
    DeviceModel("CGR1240", "router", tuple(_gig(f"0/{i}") for i in range(4)), "Cisco CGR1240"),
    DeviceModel("ISR4321", "router", (_gig("0/0/0"), _gig("0/0/1")), "Cisco ISR 4321"),
    DeviceModel("ISR4331", "router", (_gig("0/0/0"), _gig("0/0/1"), _gig("0/0/2")), "Cisco ISR 4331"),
    DeviceModel("ISR4351", "router", (_gig("0/0/0"), _gig("0/0/1"), _gig("0/0/2")), "Cisco ISR 4351"),
)


SWITCH_MODELS: tuple[DeviceModel, ...] = (
    DeviceModel(
        "Switch-PT",
        "switch",
        tuple(_port(PortSpeed.FAST_ETHERNET, str(index), f"FastEthernet{index}") for index in range(1, 9)),
        "Generic Switch PT",
    ),
    DeviceModel("2950-24", "switch", _fe_switch("0/", 24), "Cisco 2950-24"),
    DeviceModel("2950T-24", "switch", _fe_switch("0/", 24) + _ge_switch("0/", 1, 2), "Cisco 2950T-24"),
    DeviceModel("2960-24TT", "switch", _fe_switch("0/", 24) + _ge_switch("0/", 1, 2), "Cisco 2960-24TT"),
    DeviceModel("2960-48TT", "switch", _fe_switch("0/", 48) + _ge_switch("0/", 1, 2), "Cisco 2960-48TT"),
    DeviceModel("3560-24PS", "switch", _fe_switch("0/", 24) + _ge_switch("0/", 1, 2), "Cisco 3560-24PS"),
    DeviceModel("3650-24PS", "switch", _ge_switch("1/0/", 1, 24), "Cisco 3650-24PS"),
    DeviceModel("3850-24T", "switch", _ge_switch("1/0/", 1, 24), "Cisco 3850-24T"),
    DeviceModel(
        "IE2000",
        "switch",
        _fe_switch("0/", 8) + _ge_switch("0/", 1, 2),
        "Cisco IE2000",
    ),
    DeviceModel("Bridge-PT", "bridge", (_named_fast("Port 0"), _named_fast("Port 1")), "Bridge PT"),
    DeviceModel("Hub-PT", "hub", tuple(_named_fast(f"Port {index}") for index in range(10)), "Hub PT"),
    DeviceModel("Repeater-PT", "repeater", (_named_fast("Port 0"), _named_fast("Port 1")), "Repeater PT"),
)


END_DEVICE_MODELS: tuple[DeviceModel, ...] = (
    DeviceModel("PC-PT", "pc", (_fast("0"),), "PC"),
    DeviceModel("Server-PT", "server", (_fast("0"),), "Server"),
    DeviceModel("Meraki-Server", "server", (_gig("0"),), "Meraki Server"),
    DeviceModel("Network Controller", "controller", (_gig("0"),), "Network Controller"),
    DeviceModel("Laptop-PT", "laptop", (_fast("0"),), "Laptop"),
    DeviceModel("Tablet-PT", "tablet", (), "Tablet"),
    DeviceModel("TabletPC-PT", "tablet", (), "Tablet PC"),
    DeviceModel("SMARTPHONE-PT", "phone", (), "Smartphone"),
    DeviceModel(
        "7960",
        "phone",
        (_named_fast("FastEthernet0"), _named_fast("FastEthernet1")),
        "Cisco IP Phone 7960",
    ),
    DeviceModel("Home-VoIP-PT", "phone", (_fast("0"),), "Home VoIP Phone"),
    DeviceModel("Analog-Phone-PT", "phone", (), "Analog Phone"),
    DeviceModel("TV-PT", "iot", (_fast("0"),), "TV"),
    DeviceModel("Printer-PT", "printer", (_fast("0"),), "Printer"),
    DeviceModel("WirelessEndDevice-PT", "wireless_client", (), "Generic Wireless Device"),
    DeviceModel("WiredDevice-PT", "iot", (_fast("0"),), "Generic Wired Device"),
    DeviceModel("Sniffer", "tool", (_fast("0"),), "Sniffer"),
)


WAN_AND_SPECIAL_MODELS: tuple[DeviceModel, ...] = (
    DeviceModel(
        "Cloud-PT",
        "cloud",
        (
            _named_fast("Ethernet6"),
            _named_fast("Ethernet7"),
            _named_serial("Serial0"),
            _named_serial("Serial1"),
            _named_coax("Coaxial0"),
            _custom("DSL", "DSL"),
        ),
        "Cloud / ISP",
    ),
    DeviceModel("DSL-Modem-PT", "wan", (_fast("0"), _fast("1")), "DSL Modem"),
    DeviceModel("Cable Modem-PT", "wan", (_named_coax("Coaxial0"), _named_fast("FastEthernet1")), "Cable Modem"),
    DeviceModel(
        "CoAxialSplitter-PT",
        "wan",
        (_named_coax("Coaxial0"), _named_coax("Coaxial1"), _named_coax("Coaxial2")),
        "Coaxial Splitter",
    ),
    DeviceModel(
        "Central Office Server",
        "wan",
        (_fast("0"),) + tuple(_named_coax(f"Coaxial{index}") for index in range(6)),
        "Central Office Server",
    ),
    DeviceModel("Cell Tower", "cellular", (), "Cell Tower"),
    DeviceModel("Power Distribution Device", "power", (), "Power Distribution Device"),
)


SECURITY_AND_WIRELESS_MODELS: tuple[DeviceModel, ...] = (
    DeviceModel("ASA5505", "firewall", _fe_switch("0/", 8), "Cisco ASA 5505"),
    DeviceModel("ASA5506", "firewall", _ge_switch("0/", 0, 7), "Cisco ASA 5506-X"),
    DeviceModel(
        "WRT300N",
        "home_router",
        (_custom("Internet", "Internet"),) + _ethernet_block(1, 4),
        "Linksys WRT300N",
    ),
    DeviceModel(
        "Meraki-MX65W",
        "firewall",
        (_custom("Internet", "Internet"),) + _ethernet_block(1, 4),
        "Meraki MX65W",
    ),
    DeviceModel(
        "Home Router",
        "home_router",
        (_custom("Internet", "Internet"),) + _ethernet_block(1, 4),
        "Home Router",
    ),
    DeviceModel(
        "Home Gateway",
        "home_gateway",
        (_custom("Internet", "Internet"),) + _ethernet_block(1, 4),
        "Home Gateway",
    ),
    DeviceModel("AccessPoint-PT", "accesspoint", (_named_fast("Port 0"),), "Access Point"),
    DeviceModel("AccessPoint-PT-A", "accesspoint", (_named_fast("Port 0"),), "Access Point A"),
    DeviceModel("AccessPoint-PT-AC", "accesspoint", (_named_fast("Port 0"),), "Access Point AC"),
    DeviceModel("AccessPoint-PT-N", "accesspoint", (_named_fast("Port 0"),), "Access Point N"),
    DeviceModel("LAP-PT", "accesspoint", (_named_fast("Port 0"),), "Lightweight AP"),
    DeviceModel("3702i", "accesspoint", (_gig("0"),), "Cisco Aironet 3702i"),
    DeviceModel("WLC-PT", "wireless_controller", (_gig("0"), _gig("1")), "Wireless LAN Controller"),
    DeviceModel("WLC-2504", "wireless_controller", (_gig("0"), _gig("1")), "Cisco WLC 2504"),
    DeviceModel("WLC-3504", "wireless_controller", (_gig("0"), _gig("1")), "Cisco WLC 3504"),
)


ALL_MODELS: dict[str, DeviceModel] = {
    model.pt_type: model
    for model in (
        ROUTER_MODELS
        + SWITCH_MODELS
        + END_DEVICE_MODELS
        + WAN_AND_SPECIAL_MODELS
        + SECURITY_AND_WIRELESS_MODELS
    )
}


def resolve_model(name: str) -> DeviceModel | None:
    """Resolve a model name or alias to a DeviceModel."""
    from .aliases import MODEL_ALIASES

    key = MODEL_ALIASES.get(name.lower(), name)
    return ALL_MODELS.get(key)


def get_ports_by_speed(model: DeviceModel, speed: str) -> list[PortSpec]:
    """Return model ports filtered by speed."""
    return [port for port in model.ports if port.speed == speed]


def get_valid_ports(model_name: str) -> set[str]:
    """Return the valid port names for a model."""
    model = resolve_model(model_name)
    if not model:
        return set()
    return {port.full_name for port in model.ports}
