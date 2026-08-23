/** Fixtures shaped exactly like the backend responses.
 *
 * Every `source` block is a REAL row from data/raw/input_sample.csv, so the UI
 * is exercised against the actual mess it has to handle: distributor names in
 * the manufacturer column, "-- Unbranded --" placeholders, and part
 * descriptions written in trade shorthand.
 *
 * Delete this file once the backend is live; nothing imports it except api.ts.
 */

import type {
  Cell,
  EnrichedRow,
  PropagationResult,
  Provenance,
  ReviewQueueParams,
  RunStats,
  SearchComparison,
} from "./types";

const cell = (
  value: string | null,
  state: Provenance | null,
  confidence: number,
  extra: Partial<Cell> = {},
): Cell => ({ value, state, confidence, ...extra });

/** An honest gap. Not a failure — a first-class result. */
const gap = (reason: string): Cell => ({
  value: null,
  state: null,
  confidence: 0,
  reason,
});

export const rows: EnrichedRow[] = [
  {
    row_id: "801274",
    source: {
      Mfg_Part_Num: "801274",
      Part_Desc: '801274 10w LED 6" Retro 50k',
      E1_Brand: "-- Unbranded --",
      Unilog_Brand: "-- No Unilog Brand --",
      DIB_Brand: "Philips",
      Part_Manuf: "Phillips Lighting (5831)",
    },
    classpath: cell(
      "Lighting>Lamps>LED Retrofit Downlights",
      "LOOKUP",
      0.94,
      { evidence: { source: "classpath vocabulary" }, reason: "Router matched Part_Manuf + 'LED' signature" },
    ),
    fields: {
      MANUFACTURER_NAME: cell("Signify North America Corporation", "LOOKUP", 0.91, {
        evidence: { source: "approved manufacturer list" },
        reason: "Resolved from distributor code 5831; 'Phillips Lighting' is a misspelling of Philips",
      }),
      BRAND_NAME: cell("Philips®", "LOOKUP", 0.96, {
        evidence: { source: "DIB_Brand" },
        reason: "Canonical casing and ® restored from the approved brand list",
      }),
      MANUFACTURER_PART_NUMBER: cell("801274", "PARSED", 1.0, {
        evidence: { source: "Mfg_Part_Num" },
      }),
      "Product Name": cell("LED Retrofit Downlight", "INFERRED", 0.88, {
        evidence: { source: "consensus", contributing_skus: ["800938", "801266", "801282"] },
        reason: "37 of 111 Philips siblings share this item type",
      }),
      MOBILE_DESC: cell("Philips, LED Retrofit Downlight, 801274", "PARSED", 0.9, {
        evidence: { source: "composed" },
        reason: "Composed from the fact layer — not generated",
      }),
      INVOICE_DESC: cell("DOWNLIGHT LED 10W 6IN 5000K", "PARSED", 0.9, {
        evidence: { source: "composed" },
        reason: "27 chars, within the 40-char limit",
      }),
      UPC: gap("Out of scope for this run — see docs/00-brief.md"),
      "Country Of Origin": gap("No manufacturer document retrieved"),
    },
    attributes: [
      {
        label: "Wattage",
        cell: cell("10", "PARSED", 0.97, {
          uom: "W",
          evidence: { source: "Part_Desc", span: [7, 10] },
          reason: "Matched slot_2 <int>w of the Philips LED template",
        }),
      },
      {
        label: "Lamp Type",
        cell: cell("LED", "PARSED", 0.98, {
          evidence: { source: "Part_Desc", span: [11, 14] },
          reason: "Matched slot_3 of the Philips LED template",
        }),
      },
      {
        label: "Nominal Size",
        cell: cell("6", "PARSED", 0.95, {
          uom: "in",
          evidence: { source: "Part_Desc", span: [15, 17] },
          reason: 'Matched slot_4 <int>" of the Philips LED template',
        }),
      },
      {
        label: "Color Temperature",
        cell: cell("5000", "PARSED", 0.93, {
          uom: "K",
          evidence: { source: "Part_Desc", span: [24, 27] },
          reason: "Slot_6 <int>k expands ×100 — learned from 111 sibling rows, not a dictionary",
        }),
      },
      {
        label: "Base Type",
        cell: cell("Medium (E26)", "INFERRED", 0.79, {
          evidence: { source: "consensus", contributing_skus: ["800938", "801266", "801282", "800912"] },
          reason: "4 siblings agree, none disagree",
        }),
      },
      { label: "Lumens", cell: gap("No sibling agreement and no manufacturer document") },
      { label: "Rated Life", cell: gap("No sibling agreement and no manufacturer document") },
      {
        label: "Dimmable",
        cell: cell("Yes", "RETRIEVED", 0.86, {
          evidence: {
            source: "manufacturer document",
            url: "https://www.usa.lighting.philips.com/",
            snippet: "Dimmable to 10% with most standard incandescent dimmers.",
          },
          reason: "Extracted verbatim from the Philips spec sheet",
        }),
      },
    ],
    flags: ["low_confidence_attribute"],
  },
  {
    row_id: "PDSH4816AF",
    source: {
      Mfg_Part_Num: "PDSH4816AF",
      Part_Desc: "PDSH4816AF Dishwasher SS - Display Only",
      E1_Brand: "-- Unbranded --",
      Unilog_Brand: "-- No Unilog Brand --",
      DIB_Brand: "-- No DIB Brand --",
      Part_Manuf: "Appliance Dealers Cooperative (APPDE)",
    },
    classpath: cell(
      "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
      "LOOKUP",
      0.97,
    ),
    fields: {
      MANUFACTURER_NAME: cell("Electrolux Home Products, Inc.", "LOOKUP", 0.72, {
        evidence: { source: "approved manufacturer list" },
        reason:
          "Part_Manuf is a DISTRIBUTOR, not a manufacturer. Resolved via the FRIGIDAIRE brand. Ground truth says 'Rheem Manufacturing' — flagged for review, see docs/04-decisions.md Q3",
      }),
      BRAND_NAME: cell("FRIGIDAIRE®", "PARSED", 0.9, {
        evidence: { source: "Mfg_Part_Num" },
        reason: "PDSH prefix is a Frigidaire Professional series code",
      }),
      MANUFACTURER_PART_NUMBER: cell("PDSH4816AF", "PARSED", 1.0, {
        evidence: { source: "Mfg_Part_Num" },
      }),
      "Product Name": cell("Dishwasher", "PARSED", 0.99, {
        evidence: { source: "Part_Desc", span: [11, 21] },
      }),
      INVOICE_DESC: cell("DISHWASHER LEG 5 SST 120V 15A 50-1/4IN", "PARSED", 0.92, {
        evidence: { source: "composed" },
        reason: "38 chars — greedy token-drop kept it inside the 40-char limit",
      }),
    },
    attributes: [
      { label: "Series", cell: cell("Professional Series", "RETRIEVED", 0.89, {
        evidence: {
          source: "manufacturer document",
          url: "https://www.frigidaire.com/en/p/owner-center/product-support/PDSH4816AF",
        },
      }) },
      { label: "Model", cell: gap("Not stated in any retrieved document") },
      { label: "Number of Wash Cycles", cell: cell("5", "RETRIEVED", 0.94, {
        evidence: {
          source: "manufacturer document",
          url: "https://www.frigidaire.com/en/p/owner-center/product-support/PDSH4816AF",
          snippet: "5 wash cycles including Heavy, Normal, Light/China",
        },
      }) },
      { label: "Voltage Rating", cell: cell("120", "RETRIEVED", 0.95, { uom: "V" }) },
      { label: "Amperage Rating", cell: cell("15", "RETRIEVED", 0.93, { uom: "A" }) },
      { label: "Mounting Type", cell: cell("Leg", "RETRIEVED", 0.88) },
      { label: "Plug Type", cell: gap("Not stated in any retrieved document") },
      { label: "Sound Level", cell: cell("47", "RETRIEVED", 0.91, { uom: "dBA" }) },
      { label: "Material", cell: cell("Stainless Steel", "PARSED", 0.87, {
        evidence: { source: "Part_Desc", span: [22, 24] },
        reason: "'SS' expanded via the appliance abbreviation grammar",
      }) },
      { label: "Color", cell: gap("Not stated in any retrieved document") },
    ],
    flags: ["manufacturer_resolution_uncertain", "conflicts_with_ground_truth"],
  },
  {
    row_id: "DCGG581B",
    source: {
      Mfg_Part_Num: "DCGG581B",
      Part_Desc: "DCGG581B Dewalt 20V Grease Gun 2-Speed",
      E1_Brand: "-- Unbranded --",
      Unilog_Brand: "-- No Unilog Brand --",
      DIB_Brand: "-- No DIB Brand --",
      Part_Manuf: "Black & Decker/dewlt (2585)",
    },
    classpath: cell("Tools>Cordless Power Tools>Grease Guns", "LOOKUP", 0.93),
    fields: {
      MANUFACTURER_NAME: cell("Black & Decker/dewlt", "PARSED", 0.41, {
        evidence: { source: "Part_Manuf" },
        reason:
          "Distributor string copied through — this is the failure mode the correction rule fixes. Should resolve to Stanley Black & Decker, Inc.",
      }),
      BRAND_NAME: cell("DEWALT®", "PARSED", 0.92, {
        evidence: { source: "Part_Desc", span: [9, 15] },
      }),
      MANUFACTURER_PART_NUMBER: cell("DCGG581B", "PARSED", 1.0, {
        evidence: { source: "Mfg_Part_Num" },
      }),
      "Product Name": cell("Cordless Grease Gun", "PARSED", 0.95, {
        evidence: { source: "Part_Desc", span: [20, 30] },
      }),
    },
    attributes: [
      { label: "Voltage Rating", cell: cell("20", "PARSED", 0.96, {
        uom: "V",
        evidence: { source: "Part_Desc", span: [16, 19] },
      }) },
      { label: "Number of Speeds", cell: cell("2", "PARSED", 0.9, {
        evidence: { source: "Part_Desc", span: [31, 38] },
      }) },
      { label: "Battery Included", cell: cell("No", "INFERRED", 0.83, {
        evidence: { source: "consensus", contributing_skus: ["DCGG571B", "DCF887B", "DCD791B"] },
        reason: "Trailing 'B' means bare tool across 41 DeWalt siblings",
      }) },
      { label: "Maximum Pressure", cell: gap("No sibling agreement and no manufacturer document") },
    ],
    flags: ["distributor_in_manufacturer_field", "low_confidence_attribute"],
  },
  {
    row_id: "49-94-0013",
    source: {
      Mfg_Part_Num: "49-94-0013",
      Part_Desc: '49-94-0013 Milw 5"x.045"x7/8" Metal Cut Off Disc',
      E1_Brand: "-- Unbranded --",
      Unilog_Brand: "-- No Unilog Brand --",
      DIB_Brand: "-- No DIB Brand --",
      Part_Manuf: "Milwaukee Accessory (4031)",
    },
    classpath: cell("Tools>Power Tool Accessories>Cut-Off Wheels", "LOOKUP", 0.96),
    fields: {
      MANUFACTURER_NAME: cell("Milwaukee Electric Tool Corporation", "LOOKUP", 0.94),
      BRAND_NAME: cell("Milwaukee®", "PARSED", 0.93, {
        evidence: { source: "Part_Desc", span: [11, 15] },
        reason: "'Milw' expanded via the abbreviation grammar mined from 108 siblings",
      }),
      MANUFACTURER_PART_NUMBER: cell("49-94-0013", "PARSED", 1.0, {
        evidence: { source: "Mfg_Part_Num" },
      }),
      "Product Name": cell("Metal Cut-Off Wheel", "PARSED", 0.97, {
        evidence: { source: "Part_Desc", span: [29, 47] },
      }),
    },
    attributes: [
      { label: "Wheel Diameter", cell: cell("5", "PARSED", 0.98, {
        uom: "in",
        evidence: { source: "Part_Desc", span: [16, 18] },
      }) },
      { label: "Wheel Thickness", cell: cell("3/64", "PARSED", 0.86, {
        uom: "in",
        evidence: { source: "Part_Desc", span: [19, 24] },
        reason: "0.045 in normalised to the nearest 64th — tradespeople search in fractions",
      }) },
      { label: "Arbor Size", cell: cell("7/8", "PARSED", 0.97, {
        uom: "in",
        evidence: { source: "Part_Desc", span: [25, 28] },
      }) },
      { label: "Maximum RPM", cell: gap("No sibling agreement and no manufacturer document") },
    ],
    flags: [],
  },
  {
    row_id: "543300256",
    source: {
      Mfg_Part_Num: "543300256",
      Part_Desc: "6' Black Select Classic Horiz - Rail w/Rnd Black Alum Baluster",
      E1_Brand: "TREX",
      Unilog_Brand: "-- No Unilog Brand --",
      DIB_Brand: "-- No DIB Brand --",
      Part_Manuf: "Boise Cascade Building Materials (BOICA)",
    },
    classpath: cell("Building Materials>Decking & Railing>Railing Kits", "LOOKUP", 0.92),
    fields: {
      MANUFACTURER_NAME: cell("Trex Company, Inc.", "LOOKUP", 0.95, {
        evidence: { source: "approved manufacturer list" },
        reason: "Decking is the one category where E1_Brand is actually populated",
      }),
      BRAND_NAME: cell("Trex®", "LOOKUP", 0.95, { evidence: { source: "E1_Brand" } }),
      MANUFACTURER_PART_NUMBER: cell("543300256", "PARSED", 1.0, {
        evidence: { source: "Mfg_Part_Num" },
      }),
      "Product Name": cell("Horizontal Rail Kit", "PARSED", 0.89, {
        evidence: { source: "Part_Desc", span: [30, 34] },
      }),
    },
    attributes: [
      { label: "Length", cell: cell("6", "PARSED", 0.97, {
        uom: "ft",
        evidence: { source: "Part_Desc", span: [0, 2] },
      }) },
      { label: "Color", cell: cell("Black", "PARSED", 0.94, {
        evidence: { source: "Part_Desc", span: [3, 8] },
      }) },
      { label: "Series", cell: cell("Select Classic", "PARSED", 0.88, {
        evidence: { source: "Part_Desc", span: [9, 23] },
      }) },
      { label: "Baluster Material", cell: cell("Aluminum", "PARSED", 0.91, {
        evidence: { source: "Part_Desc", span: [47, 51] },
        reason: "'Alum' expanded via the decking abbreviation grammar",
      }) },
      { label: "Baluster Profile", cell: cell("Round", "PARSED", 0.85, {
        evidence: { source: "Part_Desc", span: [38, 41] },
      }) },
      { label: "Load Rating", cell: gap("No manufacturer document retrieved") },
    ],
    flags: [],
  },
];

export const runStats: RunStats = {
  run_id: "run_20260823_2241",
  input_file: "input_sample.csv",
  completed_at: "2026-08-23T22:41:08Z",
  rows_total: 1000,
  rows_clean: 918,
  rows_needing_review: 82,
  cells_total: 252000,
  cells_populated: 96420,
  provenance_counts: {
    PARSED: 41230,
    LOOKUP: 24870,
    INFERRED: 19640,
    RETRIEVED: 10680,
    GAP: 155580,
  },
  confidence_histogram: [0, 0, 140, 620, 1840, 4210, 9870, 21400, 33210, 25130],
  lov_conformance: 0.973,
  char_limit_compliance: 1.0,
  cost_usd: 4.18,
  llm_calls: 212,
  analyst_hours_saved: 41,
};

export function filterRows(params: ReviewQueueParams): EnrichedRow[] {
  const term = params.search?.toLowerCase().trim();
  return rows.filter((row) => {
    if (params.manufacturer && row.source.Part_Manuf !== params.manufacturer) return false;
    if (params.flag && !row.flags.includes(params.flag)) return false;
    if (params.maxConfidence != null) {
      const lowest = Math.min(
        ...row.attributes.filter((a) => a.cell.value).map((a) => a.cell.confidence),
        1,
      );
      if (lowest > params.maxConfidence) return false;
    }
    if (term) {
      const haystack = [row.row_id, ...Object.values(row.source)].join(" ").toLowerCase();
      if (!haystack.includes(term)) return false;
    }
    return true;
  });
}

export function propagate(input: {
  rowId: string;
  field: string;
  value: string;
  scopeField: string;
  scopeValue: string;
}): PropagationResult {
  // In the real backend this counts rows actually matched by the rule scope.
  // The 55 DeWalt rows are the headline case from docs/05-evaluation.md.
  const affected = input.scopeValue === "Black & Decker/dewlt (2585)" ? 55 : 12;
  return {
    rule: {
      id: `rule_${Date.now()}`,
      scope_field: input.scopeField,
      scope_value: input.scopeValue,
      field: input.field,
      value: input.value,
      author: "reviewer",
      created_at: new Date().toISOString(),
      rows_affected: affected,
      rows_needing_rereview: 3,
    },
    rows_affected: affected,
    rows_needing_rereview: 3,
    sample_row_ids: ["DCGG581B", "DCGG581GD1", "DCL183"],
  };
}

export function compareSearch(query: string): SearchComparison {
  const q = query.toLowerCase();
  const isLedQuery = q.includes("led") || q.includes("5000") || q.includes("50k");
  return {
    query,
    // Raw Part_Desc is trade shorthand, so a buyer-style query matches nothing.
    raw: [],
    enriched: isLedQuery
      ? [
          {
            row_id: "801274",
            title: 'Philips® LED Retrofit Downlight, 10 W, 6 in, 5000 K',
            manufacturer: "Signify North America Corporation",
            matched_on: ["Lamp Type", "Color Temperature", "Wattage"],
          },
        ]
      : [],
  };
}
