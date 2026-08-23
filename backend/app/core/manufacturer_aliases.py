"""
Distributor code -> canonical manufacturer/brand resolution.

This is NOT a simple lookup table, because Part_Manuf is a distributor, not a
manufacturer - the ground truth proves it: "Appliance Dealers Cooperative
(APPDE)" resolves to Rheem Manufacturing / FRIGIDAIRE(R) on one row and to
Whirlpool Corporation / Whirlpool(R) on another. Two distributor codes
(APPDE, and the bare "-") are genuinely ambiguous from Part_Manuf alone and
MUST be resolved from the brand token actually present in Part_Desc, or left
BLANK+FLAGGED - never guessed from the distributor code.

BRAND_ALIASES: a token found in Part_Desc (case-insensitive) -> (manufacturer_name, brand_name).
This covers the rows where the description itself names the brand, which is
the majority of non-appliance rows in the sample (Diablo, Milwaukee, Dewalt,
Makita, Trex, Azek, TimberTech, etc. all appear directly in Part_Desc).

DISTRIBUTOR_MANUFACTURER: distributor code -> (manufacturer_name, brand_name),
used ONLY when the distributor code is unambiguous in the observed data (i.e.
every row for that code plausibly shares one manufacturer). APPDE is
deliberately absent - it must go through brand-token resolution instead.
"""
from __future__ import annotations

# token (matched case-insensitively as a whole word/prefix in Part_Desc) -> (MANUFACTURER_NAME, BRAND_NAME)
BRAND_ALIASES: dict[str, tuple[str, str]] = {
    "diablo": ("Freud Inc.", "Diablo\u00ae"),
    "freud": ("Freud Inc.", "Freud\u00ae"),
    "milw": ("Milwaukee Tool", "Milwaukee\u00ae"),
    "milwaukee": ("Milwaukee Tool", "Milwaukee\u00ae"),
    "dewalt": ("Stanley Black & Decker, Inc.", "DEWALT\u00ae"),
    "dcf": ("Stanley Black & Decker, Inc.", "DEWALT\u00ae"),   # DEWALT model-number prefix
    "dcb": ("Stanley Black & Decker, Inc.", "DEWALT\u00ae"),
    "makita": ("Makita U.S.A., Inc.", "Makita\u00ae"),
    "3m": ("3M Company", "3M\u2122"),
    "trex": ("Trex Company, Inc.", "Trex\u00ae"),
    "azek": ("AZEK Building Products", "AZEK\u00ae"),
    "timbertech": ("AZEK Building Products", "TimberTech\u00ae"),
    "huber": ("Huber Engineered Woods", "Huber\u00ae"),
    "kreg": ("Kreg Tool Company", "Kreg\u00ae"),
    "festool": ("Festool USA, LLC", "Festool\u00ae"),
    "feit": ("Feit Electric Company, Inc.", "Feit Electric\u00ae"),
    "kichler": ("Kichler Lighting LLC", "Kichler\u00ae"),
    "hunter": ("Hunter Fan Company", "Hunter\u00ae"),
    "southwire": ("Southwire Company, LLC", "Southwire\u00ae"),
    "leviton": ("Leviton Manufacturing Co., Inc.", "Leviton\u00ae"),
    "mirka": ("Mirka Abrasives, Inc.", "Mirka\u00ae"),
    "vessel": ("Vessel Tools USA Inc.", "Vessel\u00ae"),
    "paslode": ("Paslode", "Paslode\u00ae"),
    "philips": ("Signify (Philips Lighting)", "Philips\u00ae"),
    "satco": ("Satco Products, Inc.", "Satco\u00ae"),
}

# distributor code substring (lowercased) -> (MANUFACTURER_NAME, BRAND_NAME).
# Only used as a fallback when no brand token was found in Part_Desc.
# APPDE intentionally omitted - see module docstring.
DISTRIBUTOR_MANUFACTURER: dict[str, tuple[str, str]] = {
    "phillips lighting": ("Signify (Philips Lighting)", "Philips\u00ae"),
    "milwaukee accessory": ("Milwaukee Tool", "Milwaukee\u00ae"),
    "kichler lighting": ("Kichler Lighting LLC", "Kichler\u00ae"),
    "freud inc": ("Freud Inc.", "Freud\u00ae"),
    "satco prod inc": ("Satco Products, Inc.", "Satco\u00ae"),
    "makita usa inc": ("Makita U.S.A., Inc.", "Makita\u00ae"),
    "black & decker/dewlt": ("Stanley Black & Decker, Inc.", "DEWALT\u00ae"),
    "southwire/g turner": ("Southwire Company, LLC", "Southwire\u00ae"),
    "leviton mfg co": ("Leviton Manufacturing Co., Inc.", "Leviton\u00ae"),
    "festool usa": ("Festool USA, LLC", "Festool\u00ae"),
    "kreg tool company": ("Kreg Tool Company", "Kreg\u00ae"),
    "mirka abrasives inc": ("Mirka Abrasives, Inc.", "Mirka\u00ae"),
    "hunter fan co": ("Hunter Fan Company", "Hunter\u00ae"),
}


def resolve_brand_from_description(part_desc: str) -> tuple[str, str] | None:
    desc_lower = (part_desc or "").lower()
    for token, resolution in BRAND_ALIASES.items():
        if token in desc_lower:
            return resolution
    return None


def resolve_brand_from_distributor(part_manuf: str) -> tuple[str, str] | None:
    pm_lower = (part_manuf or "").lower()
    for code, resolution in DISTRIBUTOR_MANUFACTURER.items():
        if code in pm_lower:
            return resolution
    return None
