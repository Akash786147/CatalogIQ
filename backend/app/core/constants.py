"""Corpus facts that everything else keys off.

Anything statistical (value ranges, expected wattages, family sizes) is derived
from the corpus at runtime and does NOT belong here -- see docs/04-decisions.md
D4. This file holds only the fixed vocabulary of the *format*.
"""

from __future__ import annotations

# Placeholder strings that mean "no value". Treated as null everywhere.
# ~80% of E1_Brand and 100% of Unilog_Brand are one of these.
NULL_TOKENS: frozenset[str] = frozenset(
    {
        "-- Unbranded --",
        "-- No Unilog Brand --",
        "-- No DIB Brand --",
        "-",
        "",
        "N/A",
        "NA",
    }
)


def is_null(raw: str | None) -> bool:
    """Placeholder-aware emptiness check."""
    return raw is None or raw.strip() in NULL_TOKENS


# Approved abbreviations for INVOICE_DESC compression (<=40 chars, uppercase).
# Extend as new categories are added; every entry must be an abbreviation a
# distributor would actually recognise on an invoice line.
INVOICE_ABBREVIATIONS: dict[str, str] = {
    "STAINLESS STEEL": "SST",
    "BUILT-IN": "BLTLN",
    "INCH": "IN",
    "INCHES": "IN",
    "STAINLESS": "SST",
    "ALUMINUM": "ALUM",
    "GALVANIZED": "GALV",
    "PACKAGE": "PK",
    "MOUNTING": "MT",
}

# Delimiters observed in the ground-truth rows.
APPROVALS_DELIMITER = "|"  # Standard/Approvals, alphabetically sorted
ADDITIONAL_INFO_DELIMITER = ", "  # Additional Information, alphabetically sorted

# Sourcing rule: manufacturer documentation only. Marketplaces and distributor
# sites are blocked at the retrieval layer, by code, not by prompt.
BLOCKED_RETRIEVAL_DOMAINS: frozenset[str] = frozenset(
    {
        "amazon.com",
        "ebay.com",
        "walmart.com",
        "grainger.com",
        "homedepot.com",
        "lowes.com",
        "zoro.com",
        "alibaba.com",
        "aliexpress.com",
        "wayfair.com",
    }
)

# Document-type -> filename suffix, for deterministic asset naming.
# See docs/03-composition-rules.md.
DOCUMENT_SUFFIXES: dict[str, str] = {
    "Specification Sheet": "Specification_Sheet",
    "Instruction/Installation Manual": "Instruction_Installation_Manual",
    "Owners/User Manual": "Owners_User_Manual",
    "Service Manual": "Service_Manual",
    "Warranty Information": "Warranty_Information",
    "Line Drawing": "Line_Drawing",
    "Catalog": "Catalog",
    "SDS": "SDS",
}
