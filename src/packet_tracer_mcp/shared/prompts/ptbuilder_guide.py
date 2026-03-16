"""PTBuilder generation guide — comprehensive prompt for LLM-driven PT script generation."""

PTBUILDER_GUIDE = r"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL — PTBUILDER API CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The PTBuilder JavaScript environment exposes EXACTLY these functions.
NO OTHER FUNCTIONS EXIST. Do not invent, assume, or hallucinate any others.

ALLOWED — these 3 functions only:

  addDevice(name, model, x, y)
    name  : string — unique label shown on canvas, e.g. "R1", "SW-Core"
    model : string — exact model from the valid list below
    x, y  : integer — canvas coordinates (x: 100-1400, y: 50-950)

  addLink(device1, port1, device2, port2, linkType)
    device1/2  : string — must match a name used in addDevice()
    port1/2    : string — exact IOS interface name, e.g. "GigabitEthernet0/0"
    linkType   : "straight" | "crossover" | "serial" | "fiber"

  configureDevice(name, configLines)
    name        : string — must match a name used in addDevice()
    configLines : string[] — IOS CLI commands, one per array element
                  NO "enable", NO "configure terminal" — start directly
                  with the command (e.g. "hostname R1", "interface Gi0/0")

FORBIDDEN — these do NOT exist, never use them:
  configureIosDevice()   configurePcIp()        queryTopology()
  createNetwork()        buildTopology()         createSubnet()
  connectDevices()       setIPAddress()          addVlan()
  createRoute()          configureOSPF()         addFirewallRule()
  setInterface()         linkDevices()           createDHCP()
  addProtocol()          buildNetwork()          configureNAT()
  addModule()            any other function

VALID DEVICE MODELS:
  Do NOT rely on a short hardcoded list.
  Use the live catalog exposed by the server:
    - pt_list_devices()
    - pt://catalog/devices
    - pt://catalog/aliases
  Model strings are case-sensitive and must match the catalog exactly.

VALID LINK TYPES:
  "straight"   — router-switch, switch-PC, switch-switch (different layer)
  "crossover"  — switch-switch (same layer), router-router direct
  "serial"     — WAN point-to-point between routers
  "fiber"      — high-speed uplinks between distribution/core switches

VALID PORT NAMES:
  Use the exact port strings from the live catalog for the chosen model.
  Common examples:
    Router 2911       : "GigabitEthernet0/0" "GigabitEthernet0/1" "GigabitEthernet0/2"
    Router ISR4321    : "GigabitEthernet0/0/0" "GigabitEthernet0/0/1"
    L3 SW 3650/3850   : "GigabitEthernet1/0/1" through "GigabitEthernet1/0/24"
    L2 SW 2960        : "FastEthernet0/1" through "FastEthernet0/24", "GigabitEthernet0/1"
    ASA5506           : "GigabitEthernet0/0" through "GigabitEthernet0/7"
    PC / Server       : "FastEthernet0"

OUTPUT RULES — STRICT:
- Output ONE single JavaScript code block
- No imports, no require(), no module.exports
- No async/await, no fetch(), no external calls
- No try/catch blocks
- Variables are allowed (let, const, for loops, etc.)
- The code must run top-to-bottom with zero dependencies
- If a device needs more than 3 interfaces, do NOT invent new functions

SELF-CHECK before writing any line of code:
  [ ] I will only call addDevice(), addLink(), configureDevice()
  [ ] Every device name in addLink() matches an addDevice() name exactly
  [ ] Every device name in configureDevice() matches an addDevice() name exactly
  [ ] Every port name exists in the live catalog for that model
  [ ] Every model string is copied from the live catalog
  [ ] configureDevice() arrays contain ONLY plain IOS CLI strings
  [ ] No function calls inside configureDevice() arrays
  [ ] No undefined variables referenced anywhere

CORRECT EXAMPLE:
  addDevice("R1", "2911", 400, 300);
  addDevice("SW1", "2960-24TT", 400, 500);
  addDevice("PC1", "PC-PT", 300, 700);
  addLink("R1", "GigabitEthernet0/0", "SW1", "GigabitEthernet0/1", "straight");
  addLink("SW1", "FastEthernet0/1", "PC1", "FastEthernet0", "straight");
  configureDevice("R1", [
    "hostname R1",
    "interface GigabitEthernet0/0",
    "ip address 192.168.1.1 255.255.255.0",
    "no shutdown"
  ]);
  configureDevice("PC1", [
    "ip address 192.168.1.2 255.255.255.0",
    "ip default-gateway 192.168.1.1"
  ]);

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — UNIVERSAL INPUT PARSING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Input can be ANY of these formats — handle all of them:

FORMAT A: Formal project brief (corporate/academic)
  → Tables with IP addressing, VLANs, device lists
  → Parse every table row as a network element

FORMAT B: Conversational / informal
  → "Necesito una red con 3 PCs, un switch y un router con salida a internet"
  → Infer all missing details using best practices

FORMAT C: Topology description only
  → "Red en estrella con switch central y 5 hosts"
  → Design IP scheme, pick device models, generate full config

FORMAT D: Lab/exam scenario
  → "Configure OSPF between R1 and R2, R1 has 192.168.1.0/24 LAN"
  → Extract requirements and build accordingly

FORMAT E: Partial spec (some info missing)
  → Fill gaps with sensible defaults, document your assumptions
    in code comments at the top of the output

For ANY format, your first step is always:
  1. List every DEVICE mentioned or implied
  2. List every LINK between devices
  3. List every SUBNET / IP mentioned or that needs to be created
  4. List every SERVICE required (DHCP, NAT, routing protocol, VLANs, etc.)
  Then generate the code.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — DEVICE MODEL SELECTION LOGIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Choose models based on the role described:

ROUTERS
  Basic/home/SOHO          → 2901
  Standard enterprise      → 2911  (default for most labs)
  High-performance/WAN     → ISR4321
  ISR modern               → ISR4331

SWITCHES
  Access layer / basic     → 2960-24TT
  Access with PoE          → 2960-48TT
  Distribution / L3        → 3650-24PS
  Core / advanced L3       → 3850-24T

END DEVICES
  Workstation / PC         → PC-PT
  Laptop / mobile          → Laptop-PT
  Web/file/DNS server      → Server-PT
  Wireless client          → Tablet-PT

SECURITY / WAN
  Firewall / perimeter     → ASA5506
  ISP / internet cloud     → Cloud-PT
  DSL/modem                → DSL-Modem-PT
  Wireless AP              → AccessPoint-PT
  Home router/AP           → WRT300N

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — IP ADDRESSING LOGIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IF the description provides an IP table → use it EXACTLY, no changes.

IF IPs are partially provided → fill gaps following the same scheme.

IF no IPs are given → create a clean plan:
  LAN segments:     192.168.N.0/24   (N = 1,2,3... per subnet)
  P2P router links: 10.0.N.0/30      (N = 0,1,2... per link)
  Loopbacks:        172.16.N.N/32
  DMZ / servers:    10.10.N.0/24
  WAN / ISP links:  200.0.0.N/30

Gateway always = first usable IP (.1 for /24, .X+1 for /30)
DHCP range always starts after static reservations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — SERVICE CONFIGURATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DHCP (configure on router or L3 switch owning the gateway):
  ip dhcp excluded-address [gateway] [last-static-ip]
  ip dhcp pool [NAME]
   network [subnet] [mask]
   default-router [gateway]
   dns-server 8.8.8.8

VLANs (on L3 switches):
  vlan [ID]
   name [descriptive-name]
  interface vlan [ID]
   ip address [gateway] [mask]
   no shutdown
  ip routing   ← always required on L3 switch

NAT/PAT (when internet access required):
  access-list 1 permit 192.168.0.0 0.0.255.255
  ip nat inside source list 1 interface [WAN_iface] overload
  Mark inside interfaces: ip nat inside
  Mark outside interface: ip nat outside

OSPF (2+ routers, dynamic routing):
  router ospf 1
   network [subnet] [wildcard] area 0
   ← include ALL directly connected subnets
   passive-interface [toward-end-devices]

STATIC ROUTES (simple topologies or toward firewall/ISP):
  ip route [dest] [mask] [next-hop]
  ip route 0.0.0.0 0.0.0.0 [ISP-gateway]   ← default route

FIREWALL ASA (when perimeter security required):
  interface GigabitEthernet0/0
   nameif inside / security-level 100
  interface GigabitEthernet0/1
   nameif outside / security-level 0
  route outside 0.0.0.0 0.0.0.0 [ISP-next-hop]
  route inside [internal-summary] [mask] [router-next-hop]

STP / TRUNK (between switches):
  interface [uplink]
   switchport mode trunk
  spanning-tree mode rapid-pvst
  spanning-tree vlan [ID] root primary   ← on distribution switch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — LAYOUT ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Automatically infer topology shape from the description:

STAR        → central device at (700,400), others around it
HIERARCHICAL→ ISP top → FW → Routers → L3SW → Access SW → PCs (bottom)
RING        → devices evenly spaced in a circle
DUAL-SITE   → left cluster (X:100-500) and right cluster (X:900-1300)
MESH        → routers distributed across the canvas

Y-axis layers (hierarchical, most common):
  Internet/ISP:        Y = 50
  Firewall/Perimeter:  Y = 200
  Core Routers:        Y = 380
  Distribution (L3SW): Y = 560
  Access Switches:     Y = 720
  End Devices:         Y = 880

Space devices at least 150px apart horizontally.
Max canvas: X=1400, Y=950.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6 — OUTPUT STRUCTURE (ALWAYS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Always produce output in this order:

// ============================================================
// ASSUMPTIONS (only if you had to infer missing details)
// ============================================================
// - [list any decision you made that wasn't explicit]

// ============================================================
// PHASE 1: DEVICES
// ============================================================
addDevice(...)

// ============================================================
// PHASE 2: LINKS
// ============================================================
addLink(...)

// ============================================================
// PHASE 3: CONFIGURATION
// ============================================================
configureDevice(...)

After the code block, add a SHORT summary table:
| Device | Interface | IP | Role |
(max 20 rows, just the key interfaces)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7 — INTERFACE PORT ASSIGNMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Assign ports in order, track usage per device:

Cisco 2911 (3 ports default):
  Gi0/0 → first link, Gi0/1 → second, Gi0/2 → third

Cisco ISR4321 (2 ports):
  Gi0/0/0 → first link, Gi0/0/1 → second

Cisco 3650-24PS / 3850-24T:
  Gi1/0/1 → routed uplink (no switchport)
  Gi1/0/2..24 → switchport access/trunk downlinks

Cisco 2960-24TT:
  Gi0/1 → uplink trunk to L3 switch
  Fa0/1..24 → access ports to end devices

ASA5506 (8 ports):
  Gi0/0 → inside, Gi0/1 → outside
  Gi0/2..7 → additional zones if needed

PC-PT / Server-PT:
  FastEthernet0 → only port available

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 8 — GRACEFUL HANDLING OF AMBIGUITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If something is unclear:
  → Do NOT ask for clarification.
  → Make the most reasonable professional choice.
  → Document it in the // ASSUMPTIONS comment block.
  → Continue generating the complete code.

Examples of reasonable defaults:
  - No routing protocol specified → OSPF if 2+ routers,
    static routes if only 1 router
  - No VLAN IDs specified → use 10, 20, 30...
  - No device count for a LAN → place 2 PCs per segment
  - No server type specified → use Server-PT with basic config
  - "Internet access" mentioned → add NAT overload + default route
  - Redundancy mentioned but not detailed → add dual uplinks + HSRP
""".strip()
