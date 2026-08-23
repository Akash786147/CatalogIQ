"""
Classpath taxonomy for the categories actually present in the 1,000-row sample
(profiled from Part_Manuf distribution - see docs/00-brief.md). This is deliberately
NOT built around Faucets & Fittings, which the Solution Guide's example points at
but which barely appears in the real sample.

router_keywords match against Part_Manuf (case-insensitive substring). This is
Stage A of classification - the ~70% of rows that resolve with zero model calls.
desc_keywords are used to disambiguate when one Part_Manuf covers multiple
sub-categories (e.g. "Appliance Dealers Cooperative" ships dishwashers, ranges,
and refrigerators alike - the distributor code is not the classpath).

Attribute lists for Dishwashers are reverse-engineered directly from the two
ground-truth rows in delivery_format.csv (real ATTRIBUTE_LABEL values), not
invented. Other classpaths are seeded from the abbreviation grammar visible in
Part_Desc and are intentionally extensible - see docs/04-decisions.md.
"""
from __future__ import annotations

from app.core.schema import AttributeDef, ClasspathSchema

CLASSPATHS: dict[str, ClasspathSchema] = {}


def _register(schema: ClasspathSchema) -> None:
    CLASSPATHS[schema.name] = schema


# ---------------------------------------------------------------------------
# Lighting > Lamps (Philips, Satco) - 111 + 41 rows, largest single family
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Lighting>Lamps>LED Lamps",
    dept="Lighting", klass="Lamps", fine="LED Lamps",
    item_type="LED Lamp",
    router_keywords=["phillips lighting", "philips lighting", "satco"],
    desc_keywords=["led", "watt", "lumen", "cct"],
    attributes=[
        AttributeDef(label="Wattage", uom="W", numeric=True, priority=1),
        AttributeDef(label="Lamp Type", lov=["LED", "CFL", "Halogen", "Incandescent"], priority=1),
        AttributeDef(label="Bulb Shape", lov=["A19", "A21", "BR30", "PAR20", "PAR30", "PAR38", "T9", "G25"], priority=3),
        AttributeDef(label="Base Type", lov=["Medium (E26)", "Candelabra (E12)", "Mogul (E39)", "GU24"], priority=2),
        AttributeDef(label="Color Temperature", uom="K", numeric=True, priority=2),
        AttributeDef(label="Package Quantity", numeric=True, priority=4),
        AttributeDef(label="Lumens", uom="lm", numeric=True, priority=5),
        AttributeDef(label="Voltage Rating", uom="V", numeric=True, priority=6),
    ],
))

# ---------------------------------------------------------------------------
# Lighting > Fixtures (Kichler, Hunter Fan) - 56 + 9 rows
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Lighting>Fixtures>Decorative Fixtures",
    dept="Lighting", klass="Fixtures", fine="Decorative Fixtures",
    item_type="Light Fixture",
    router_keywords=["kichler", "hunter fan"],
    desc_keywords=["lt", "fixture", "fan", "chandelier", "sconce"],
    attributes=[
        AttributeDef(label="Fixture Type", lov=["Pendant", "Sconce", "Chandelier", "Ceiling Fan", "Flush Mount"], priority=1),
        AttributeDef(label="Finish", priority=2),
        AttributeDef(label="Number of Lights", numeric=True, priority=3),
        AttributeDef(label="Voltage Rating", uom="V", numeric=True, priority=5),
        AttributeDef(label="Width", uom="in", numeric=True, priority=4),
        AttributeDef(label="Height", uom="in", numeric=True, priority=4),
    ],
))

# ---------------------------------------------------------------------------
# Power Tools > Accessories > Abrasives/Blades (Milwaukee, Freud/Diablo, Mirka) - 108+46+9
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Tools>Power Tool Accessories>Cutting & Abrasive Accessories",
    dept="Tools", klass="Power Tool Accessories", fine="Cutting & Abrasive Accessories",
    item_type="Accessory",
    router_keywords=["milwaukee accessory", "freud inc", "mirka abrasives"],
    desc_keywords=["disc", "blade", "belt", "grit", "tooth", "abrasive"],
    attributes=[
        AttributeDef(label="Accessory Type", lov=["Cut Off Disc", "Sanding Belt", "Sanding Disc", "Saw Blade", "Router Bit"], priority=1),
        AttributeDef(label="Diameter", uom="in", numeric=True, priority=2),
        AttributeDef(label="Grit / Tooth Count", priority=2),
        AttributeDef(label="Arbor Size", uom="in", numeric=True, priority=4),
        AttributeDef(label="Material", lov=["Masonry", "Metal", "Wood", "Plywood"], priority=3),
        AttributeDef(label="Package Quantity", numeric=True, priority=5),
    ],
))

# ---------------------------------------------------------------------------
# Power Tools (Black & Decker/DeWalt, Makita, Festool, Kreg) - 55+23+16+11
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Tools>Power Tools>Cordless Power Tools",
    dept="Tools", klass="Power Tools", fine="Cordless Power Tools",
    item_type="Power Tool",
    router_keywords=["black & decker/dewlt", "makita usa", "festool usa", "kreg tool"],
    desc_keywords=["drill", "driver", "nailer", "kit", "battery", "charger", "20v", "18v", "m18", "m12"],
    attributes=[
        AttributeDef(label="Tool Type", lov=["Drill", "Impact Driver", "Nailer", "Charger", "Battery"], priority=1),
        AttributeDef(label="Voltage System", lov=["12V", "18V", "20V MAX"], priority=2),
        AttributeDef(label="Battery Included", lov=["Yes", "No", "Bare Tool"], priority=4),
        AttributeDef(label="Package Quantity", numeric=True, priority=5),
    ],
))

# ---------------------------------------------------------------------------
# Building Materials > Composite Decking (Parksite -> Trex/AZEK/TimberTech) - 55 rows,
# and Boise Cascade panels/OSB - 85 rows. Two distinct sub-families under one dept.
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Building Materials>Decking & Railing>Composite Decking",
    dept="Building Materials", klass="Decking & Railing", fine="Composite Decking",
    item_type="Composite Decking",
    router_keywords=["parksite"],
    desc_keywords=["decking", "fascia", "trex", "azek", "timbertech", "trim", "groove"],
    attributes=[
        AttributeDef(label="Profile", lov=["Decking", "Fascia", "Trim", "Riser"], priority=1),
        AttributeDef(label="Length", uom="ft", numeric=True, priority=2),
        AttributeDef(label="Width", uom="in", numeric=True, priority=3),
        AttributeDef(label="Color", priority=2),
        AttributeDef(label="Product Line", priority=3),
        AttributeDef(label="Edge Type", lov=["Grooved", "Square"], priority=6),
    ],
))

_register(ClasspathSchema(
    name="Building Materials>Panels & Sheathing>OSB & Subfloor Panels",
    dept="Building Materials", klass="Panels & Sheathing", fine="OSB & Subfloor Panels",
    item_type="Panel",
    router_keywords=["boise cascade", "u s lumber"],
    desc_keywords=["osb", "sub floor", "t&g", "plywood", "sheathing"],
    attributes=[
        AttributeDef(label="Thickness", uom="in", numeric=True, priority=1),
        AttributeDef(label="Length", uom="ft", numeric=True, priority=2),
        AttributeDef(label="Width", uom="ft", numeric=True, priority=2),
        AttributeDef(label="Edge Profile", lov=["Tongue & Groove", "Square Edge"], priority=4),
        AttributeDef(label="Application", lov=["Sub Floor", "Wall Sheathing", "Roof Sheathing"], priority=3),
    ],
))

# ---------------------------------------------------------------------------
# Appliances (Appliance Dealers Cooperative) - 84 rows. Attributes below are
# taken VERBATIM from the two ground-truth dishwasher rows in delivery_format.csv.
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
    dept="Appliances", klass="Large Appliances", fine="Dishwashers",
    item_type="Dishwasher",
    router_keywords=["appliance dealers cooperative"],
    desc_keywords=["dishwasher"],
    attributes=[
        AttributeDef(label="Series", priority=2),
        AttributeDef(label="Model", priority=6),
        AttributeDef(label="Number of Wash Cycles", numeric=True, priority=3),
        AttributeDef(label="Voltage Rating", uom="V", numeric=True, priority=4),
        AttributeDef(label="Amperage Rating", uom="A", numeric=True, priority=4),
        AttributeDef(label="Mounting Type", lov=["Leg", "Built-in"], priority=2),
        AttributeDef(label="Plug Type", priority=8),
        AttributeDef(label="Size", priority=3),
        AttributeDef(label="Depth With Door Open", uom="in", numeric=True, priority=7),
        AttributeDef(label="Minimum Height", uom="in", priority=8),
        AttributeDef(label="Maximum Height", uom="in", priority=8),
        AttributeDef(label="Sound Level", uom="dBA", numeric=True, priority=2),
        AttributeDef(label="Material", priority=3),
        AttributeDef(label="Color", priority=5),
        AttributeDef(label="Additional Information", priority=9),
    ],
))

# ---------------------------------------------------------------------------
# Electrical (Southwire, Leviton) - 19 + 17 rows
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Electrical>Wire, Cable & Devices>Wire & Devices",
    dept="Electrical", klass="Wire, Cable & Devices", fine="Wire & Devices",
    item_type="Electrical Component",
    router_keywords=["southwire", "leviton"],
    desc_keywords=["wire", "cable", "gauge", "awg", "outlet", "switch", "receptacle"],
    attributes=[
        AttributeDef(label="Product Type", lov=["Wire", "Cable", "Switch", "Outlet", "Receptacle"], priority=1),
        AttributeDef(label="Gauge", priority=2),
        AttributeDef(label="Voltage Rating", uom="V", numeric=True, priority=3),
        AttributeDef(label="Amperage Rating", uom="A", numeric=True, priority=4),
        AttributeDef(label="Color", priority=6),
    ],
))

# ---------------------------------------------------------------------------
# Safety / PPE (Edge Eyewear) - 10 rows
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Safety>Personal Protective Equipment>Eyewear",
    dept="Safety", klass="Personal Protective Equipment", fine="Eyewear",
    item_type="Safety Eyewear",
    router_keywords=["edge eyewear"],
    desc_keywords=["glasses", "safety", "lens"],
    attributes=[
        AttributeDef(label="Lens Color", priority=2),
        AttributeDef(label="Frame Color", priority=3),
        AttributeDef(label="Standard/Approvals", lov=["ANSI Z87.1"], priority=1),
    ],
))

# ---------------------------------------------------------------------------
# Generic fallback - used only when neither router nor LLM classification lands.
# Everything here is BLANK+FLAGGED by construction: an unknown classpath has no
# attribute schema to extract into, so nothing gets invented.
# ---------------------------------------------------------------------------
_register(ClasspathSchema(
    name="Unclassified",
    dept="", klass="", fine="",
    item_type="Product",
    router_keywords=[],
    desc_keywords=[],
    attributes=[],
))


def get_classpath(name: str) -> ClasspathSchema:
    return CLASSPATHS.get(name, CLASSPATHS["Unclassified"])


def all_classpaths(exclude_unclassified: bool = True) -> list[ClasspathSchema]:
    return [c for c in CLASSPATHS.values() if not (exclude_unclassified and c.name == "Unclassified")]


def route_by_manufacturer(part_manuf: str) -> str | None:
    """Stage A: deterministic router. Returns a classpath name or None."""
    pm = (part_manuf or "").lower()
    for schema in CLASSPATHS.values():
        for kw in schema.router_keywords:
            if kw in pm:
                return schema.name
    return None
