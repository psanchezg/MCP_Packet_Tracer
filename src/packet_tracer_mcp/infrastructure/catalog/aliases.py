"""Alias de nombres de dispositivos."""

# Mapeo de nombres comunes que el LLM podría usar → pt_type
MODEL_ALIASES: dict[str, str] = {
    "router":    "2911",
    "switch":    "2960",
    "pc":        "PC",
    "computer":  "PC",
    "server":    "Server",
    "laptop":    "Laptop",
    "cloud":     "Cloud-PT",
    "wan":       "Cloud-PT",
    "ap":        "AccessPoint-PT",
    "wifi":      "AccessPoint-PT",
    "access_point": "AccessPoint-PT",
}
