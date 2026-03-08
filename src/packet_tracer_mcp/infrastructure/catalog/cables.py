"""Catálogo de cables y reglas de cableado."""

from __future__ import annotations

# Tipos de cable en Packet Tracer
CABLE_TYPES: dict[str, str] = {
    "straight": "Copper Straight-Through",
    "cross":    "Copper Cross-Over",
    "serial":   "Serial DCE",
    "fiber":    "Fiber",
    "console":  "Console",
}

# Reglas: (categoría_a, categoría_b) → tipo de cable
CABLE_RULES: dict[tuple[str, str], str] = {
    ("router", "switch"):      "straight",
    ("switch", "router"):      "straight",
    ("switch", "pc"):          "straight",
    ("pc", "switch"):          "straight",
    ("switch", "server"):      "straight",
    ("server", "switch"):      "straight",
    ("switch", "laptop"):      "straight",
    ("laptop", "switch"):      "straight",
    ("switch", "accesspoint"): "straight",
    ("accesspoint", "switch"): "straight",
    ("router", "router"):      "cross",
    ("switch", "switch"):      "cross",
    ("router", "cloud"):       "straight",
    ("cloud", "router"):       "straight",
    ("router", "pc"):          "cross",
    ("pc", "router"):          "cross",
    ("router", "server"):      "cross",
    ("server", "router"):      "cross",
}


def infer_cable(cat_a: str, cat_b: str) -> str:
    """Infiere el tipo de cable correcto entre dos categorías de dispositivo."""
    return CABLE_RULES.get((cat_a, cat_b), "straight")
