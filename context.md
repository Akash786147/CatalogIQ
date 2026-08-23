



Claude finished the response

Unihack_ Expected Output - Delivery Format.csv
csv


Unihack_ Sample Dataset - Input.csv
csv


[EXT] UniHack-Protoype Template .pptx
pptx


Your Company Home Blogs My Dashboard Open user menu Akash choudhary akash.choudhary.23cse@bmu.edu.in Logout support+unihack@hack2skill.com Event banner #unilog #unilogcorp #unihack UniHack Virtual Team Size: 1-4 Free Last Date to Register Sun 23 Au

pasted


Published using Google Docs Report abuseLearn more UniHack Solution Guide Updated automatically every 5 minutes 1. What you are actually building Unilog builds product content for industrial distributors - the manufacturer names, titles, descriptions, attributes and images that let a buyer find

pasted







Message collapsed

Ran 4 commands
Ran 4 commands
Claude’s response was interrupted.
No dont consider the deadline and all


Thought for 29s
Thought for 29s
Good — then let's talk about what to actually build.

First, what I found by profiling your two files, because it changes the answer:

The 1,000 input rows are not faucets or fittings. They're dominated by lighting (111 Philips + 41 Satco + 56 Kichler), power-tool accessories (108 Milwaukee, 46 Freud/Diablo, 55 DeWalt), composite decking (85 Boise Cascade + 55 Parksite — Trex/AZEK/TimberTech), and appliances (84 ADC). The Solution Guide tells everyone to go deep on Faucets/Fittings. Almost nobody will notice those categories barely exist in the sample. Depth on lighting + decking is depth on data the evaluators will actually test you against.
Unilog_Brand is a placeholder in 1000/1000 rows. E1_Brand in 799. So 80% of rows have literally no brand signal — the brand must be recovered from the description string and the Part_Manuf code.
Part_Manuf is a distributor, not a manufacturer. "Appliance Dealers Cooperative (APPDE)" → the ground truth says MANUFACTURER_NAME: Rheem Manufacturing. Naive systems will copy the distributor into the manufacturer field and fail every row.
The obvious project (don't build this)
Row → one big LLM prompt → 252 columns → CSV + a dashboard with a pie chart. 80% of submissions will be exactly this. It hallucinates amperage ratings, produces five descriptions that contradict each other, and has no answer when a judge asks "how do you know that's true?"

The project I'd build: an evidence-first enrichment engine with cell-level provenance
The reframe that makes it feel real: the bottleneck at a company like Unilog isn't generating content, it's reviewing it. A human content analyst can produce ~15 enriched SKUs a day. AI that produces 10,000 rows of unverifiable text creates more work, not less — someone still has to check all of it. So the product isn't "AI fills the sheet." It's "AI fills the sheet and tells you exactly which 8% of cells to look at."

Four design decisions that carry the whole project:

1. Split extraction from composition. Everyone will ask an LLM to write MOBILE_DESC, INVOICE_DESC, SHORT_DESC, LONG_DESC1, RETAIL_DESC separately — which is why theirs will disagree with each other and blow character limits. Instead: AI's only job is to produce a validated attribute layer (Series, Voltage, Mounting, Sound Level…). All five descriptions are then deterministically composed from that one layer using the guideline formulas. Consistency becomes structurally guaranteed, not prompted-for. INVOICE_DESC ≤40 chars becomes a compression problem with a greedy token-dropper, not a prayer.

2. Every populated cell carries provenance + confidence. Four tiers: PARSED (from the input string, with the exact character span), LOOKUP (matched a controlled vocabulary), INFERRED (cross-row consensus), RETRIEVED (manufacturer doc, with URL). Anything that would be GENERATED with no evidence gets left blank and flagged, not invented. The Solution Guide explicitly says a fluent description made of invented values scores zero — you'd be the only team whose system is architecturally incapable of that.

3. Learn the abbreviation grammar from the corpus, don't hardcode it. 573352 40W Led Med 27k 2pk → Wattage 40 W, Lamp Type LED, Base Medium (E26), Color Temp 2700 K, Pack 2. Mine these patterns statistically across the 111 sibling Philips rows rather than writing a dictionary. This is the direct answer to the brief's "must not be hardcoded, must handle unseen field combinations" warning — and you can prove it by holding out a manufacturer entirely and showing it still parses.

4. Cross-row consensus (the sleeper feature). Rows aren't independent. 108 Milwaukee accessories share a naming grammar; the 122 TREX rows share a decking attribute skeleton. Cluster by manufacturer + part-family, build a "golden record" per family, and let a sparse row inherit attributes verified across its siblings — with the inheritance recorded as provenance. This is real entity resolution, it visibly improves output on rows where a per-row LLM has nothing to work with, and essentially no one else will do it.

The demo moment that wins it
A reviewer opens the flagged queue, sees Part_Manuf: "Black & Decker/dewlt (2585)" mapped to the wrong manufacturer, and corrects it once. The system doesn't just patch that cell — it generalises the correction into a mapping rule and shows: "applied to 55 rows, 3 now need re-review." Then a counter: analyst-hours saved: 41.

That's the thing judges remember, because it's the only part of any submission that looks like software a company would deploy rather than a hackathon artifact.

Metrics to put on the slide
Field-level accuracy vs. ground truth is table stakes. Add: a coverage–accuracy curve (accuracy at 100% / 90% / 70% auto-approval thresholds), % of values found in LOV, character-limit compliance rate, calibration (does 0.9 confidence actually mean 90% correct?), and cost per 1,000 SKUs. The calibration chart is the one that signals you know what you're doing.

What to deliberately cut
Skip image sourcing, skip UPC/EAN/GTIN, skip country-of-origin, skip web scraping at scale. Leave them blank and say so on the slide with a reason — the Guide explicitly rewards flagging gaps. Spend that time on two categories done to full depth and on the review UI.

If you want, I can take this further in one of two directions: sketch the actual system architecture and module breakdown, or write the abbreviation-parser + attribute-extraction core and run it against the 1,000 rows so you can see real accuracy numbers before you commit.


Message collapsed

Thought for 12s
Thought for 12s
Your teammate has two good instincts buried in there, but the wrapper around them would sink you. Let me separate them.

The core problem with the proposal as stated
The input doesn't match what you'll be evaluated on. Read the brief again: "capable of processing the evaluation test dataset during assessment" and "generate a downloadable XLSX or CSV from the given input data, with all the required static headers populated."

On evaluation day someone hands your system a CSV that looks exactly like your 1,000-row file — Mfg_Part_Num, Part_Desc, E1_Brand, Unilog_Brand, DIB_Brand, Part_Manuf. Six columns of abbreviated junk. No company website. No catalog PDF. No technical docs.

A pipeline whose entry point is "input the company website" has nothing to eat. It scores zero not because it's bad but because it answers a question nobody asked.

Franchises, locations, employee datasets are out of scope. Unilog does product content for industrial distributors — titles, attributes, descriptions, images. An HR sheet and a franchise-location sheet have no connection to the challenge statement or to those 252 headers. That part is a generic "company knowledge base builder," which is exactly the pattern-matched idea we agreed to avoid. Ironically it's more obvious than the obvious one — every hackathon has three of these.

Notion/Sheets is plumbing, not product. Judges are Unilog's tech leaders. They already have a PIM. Adding a Notion sync tells them nothing about whether your extraction is correct — and it burns your build time on OAuth, API quotas, and a live integration that has a real chance of failing on stage. The deliverable is a file. Ship a file.

What's genuinely worth keeping
RAG — yes, but as an internal grounding layer, not a chatbot. The Solution Guide has a hard sourcing rule: data must come from the manufacturer's own site or documentation, marketplaces explicitly excluded. That is a retrieval problem. Index manufacturer spec sheets and use retrieval to ground attribute extraction, so every RETRIEVED cell carries the URL it came from. That's RAG doing real work — feeding the provenance system from the last message — rather than RAG as a résumé keyword.

Step-back prompting — yes, and it has an exact home. Before extracting anything, step back: what class of product is this, and what attribute set applies to that class? Classify → pull the attribute schema for that classpath → extract only within it. That's not decoration, that's the mechanism that keeps the model inside the controlled vocabulary instead of inventing free text. Same idea for the description formulas.

Nobody awards points for naming techniques. They award points when the technique visibly fixes a failure the judge can see.

The one merge worth making
Your teammate is right that a spreadsheet is a bad review surface. But the fix isn't Notion — it's the reviewer queue we already discussed. Same underlying want, scoped to the actual problem.

And if you want a chat interface, point it at the right question. Not "ask me about your company." Instead: a buyer-style search over the catalog, run twice — once on raw Part_Desc, once on enriched output. Search 2700K medium base LED 40W and watch it return nothing on the raw data and the correct Philips SKUs on the enriched data. That's a 30-second demo that proves why enrichment matters commercially, and it reuses the RAG stack your teammate wants to build.

How I'd put it to them
Don't frame it as "your idea is wrong." Frame it as scope:

The eval is a headless CSV-in, CSV-out test — so the pipeline core has to be file-based or we can't be scored at all. But your RAG layer is exactly how we ground attributes in manufacturer docs instead of hallucinating them, and step-back classification is how we stay inside the LOV. Let's put those in the engine, and make the review queue the shareable surface instead of Notion.

That keeps their contribution load-bearing, which matters more for a four-person team over the build than winning the argument does.

One thing worth deciding early, since it shapes everything: are you going to attempt live retrieval from manufacturer sites during evaluation, or pre-index a fixed corpus of spec sheets for the categories in the sample? Live retrieval is riskier and slower but demonstrates the sourcing rule properly. I'd lean pre-indexed with a live fallback — happy to argue either side if you want to think it through.

Walking through what actually happens to one product. Same example the whole way:

What goes in: 573352  40W Led Med 27k 2pk

Step 1 — Figure out what it even is
Before reading any detail, the system asks one question: what type of product is this?

It works out: this is a light bulb.

That matters because now it knows which questions to ask. Bulbs have wattage, brightness, colour temperature, base type. Dishwashers have wash cycles and noise levels.

So instead of staring at a blank form with 250 empty boxes, it's working through a short checklist for bulbs. It can't wander off and invent a "wash cycle" field for a light bulb — that question was never on the list.

Step 2 — Decode the shorthand
The messy text isn't random. It's trade shorthand — the same way a chef writes "2T btr" for two tablespoons of butter.

40W  →  40 watts
Led  →  LED
Med  →  Medium screw base
27k  →  2700 Kelvin (warm white)
2pk  →  pack of two
How does it learn the shorthand? Not from a dictionary we typed out. There are 111 Philips products in this catalogue, all written by the same person in the same style. The system reads them together and works out the pattern itself.

That's why it also works on a brand we've never seen — it learns the habit, not a fixed list.

Step 3 — Fill the gaps, in a strict order
The bulb still has empty boxes — dimensions, lifespan, certifications. Three places to look, in this order:

First, its siblings. Those other 110 Philips bulbs. If 40 of them share the same base type and packaging dimensions, we can reasonably carry that across — and we record which products it came from.

Second, the manufacturer's own documents. We search Philips' actual spec sheets and save the link.

Third, nowhere. If neither works, the box stays empty and gets flagged. This is the step everyone else skips — and it's exactly why their output can't be trusted.

One firm rule: it only fills empty boxes. It never overwrites something that was already there.

Step 4 — Check every answer before accepting it
Four checks, fast:

Is it written correctly? 24in becomes 24 in. 0.5 becomes 1/2, because tradespeople search in fractions.
Is it a permitted value? Colour temperature must come from the approved list. "Warmish white" gets rejected.
Is it normal for this family? We know from those 111 Philips bulbs what wattages actually exist. A 4000-watt bulb gets flagged as suspicious. The system learned what's normal by reading the catalogue — we didn't tell it.
Does it contradict itself? Claims waterproof, but the material listed isn't waterproof → flag.
Step 5 — Write the descriptions from the facts
Here's the part that stops the AI from drifting.

The catalogue needs the same product written five different ways — a 40-character receipt line, a mobile-app line, a search-results title, a full product page, and marketing copy.

Most teams ask the AI to write all five. Result: five descriptions that quietly disagree with each other, and a receipt line that's 58 characters and breaks the till system.

We don't let the AI write them at all.

The AI's only job is to establish the facts. Once the facts are locked, all five descriptions get assembled from those same facts by a fixed formula — like a mail merge.

Two things become impossible:

The five versions can't contradict each other. They're built from one shared set of facts.
The 40-character line can't overflow. It drops the least important word until it fits.
Step 6 — Hand back the work and the doubts
Two things come out:

The finished sheet — all 252 columns, ready to load.

The review list — "918 products are clean. 82 need you."

Open any product and every value shows its origin:

Wattage 40 W — read from the original text
Colour temp 2700 K — found in Philips' spec sheet 🔗
Lifespan — empty, nothing supported it

Step 7 — One correction fixes many
A reviewer notices the manufacturer is wrong on a flagged row and fixes it.

The system doesn't just patch that one row. It recognises the same error pattern across the catalogue and reports: "Applied to 55 products."

The reviewer gets faster as they go, instead of grinding through the same mistake 55 times.

Back to the three problems
Buyer can't find it → the shorthand is decoded into real searchable words, so "2700K medium base LED" now matches.

Buyer doesn't trust it → full specs, proper title, consistent everywhere, sourced from the manufacturer.

Too slow to fix by hand → the person reviews 82 products instead of writing 1,000, and each fix multiplies.

And the trust problem AI usually creates? Solved by the empty box. The system would rather leave a gap than fill it with a guess — so when it does fill something in, that means something.

now tech part how are we solving

Same seven steps, now with what's actually running underneath.

Step 1 — Classification
Job: row → classpath (Lighting > Lamps > LED Lamps)

Two-stage, cheap-first:

Stage A — deterministic router. Part_Manuf + keyword signature gets ~70% of rows to a category with no model call. "Philips Lighting (5831)" + Led in the description is not ambiguous. Cost: zero.
Stage B — LLM classifier for the rest. Instead of asking "pick from 400 classpaths," we retrieve the ~10 nearest classpaths by embedding similarity, then have the model pick one. Small candidate set, high accuracy, small prompt.
Output is the classpath plus its attribute schema — the list of permitted fields and permitted values for that category. Everything downstream is constrained by this object.

Stack: sentence-transformers for embeddings, FAISS for nearest-neighbour lookup, Claude for the pick.

Step 2 — Abbreviation grammar (the learned parser)
Job: 40W Led Med 27k 2pk → typed key–value pairs

This is the part that must not be hardcoded. Three passes:

Pass 1 — tokenise + type. Regex splits into number-unit pairs (40W, 2pk), alphanumeric codes (573352), and word tokens (Led, Med).

Pass 2 — mine the family. Group rows by Part_Manuf + classpath. Within the 111 Philips rows, compute positional and co-occurrence statistics: which token shapes appear at which position, which vary, which are constant. 27k varies across rows in a slot that always holds <digits>k → it's a variable field, not boilerplate. This gives us candidate slots without a dictionary.

Pass 3 — name the slots. One LLM call per family, not per row. Show the model 20 sample rows plus the mined slot structure plus the category's attribute schema, and ask it to map slot → attribute label. It returns a reusable parse template:

slot_2: <int>W        → Wattage (UOM: W)
slot_4: <int>k        → Color Temperature (UOM: K)
slot_5: <int>pk       → Package Quantity
That template then runs deterministically across all 111 rows. One model call amortised over a hundred rows — this is what makes cost per 1,000 SKUs low enough to put on a slide.

Generalisation test: hold out an entire manufacturer, run template induction fresh, measure. Proves nothing is baked in.

Step 3 — Enrichment, in source order
3a — Cross-row consensus.
Blocking on Part_Manuf + normalised part-number prefix, then similarity clustering to build part families. For each family, aggregate attribute values across members; where ≥N siblings agree and no member disagrees, the value propagates to sparse members. Provenance records the contributing SKUs. Pure computation — no model calls.

3b — Manufacturer document RAG.
Spec sheets chunked and embedded into a vector store, filtered by manufacturer + part number at query time. Retrieved chunks go to the model with a strict instruction: extract only what the chunk states, return the source URL, return null otherwise. Domain allowlist enforces the sourcing rule — marketplaces and distributor sites are blocked at the retrieval layer, not by prompt.

3c — Nothing. Null + flag.

Enrichment is gap-fill only. Input values are immutable.

Step 4 — Validation
Runs as a chain; each check can downgrade confidence or void a value.

Check	Implementation
UOM normalisation	Lookup against the approved abbreviation table. Enforce number-space-unit.
Decimal → fraction	Exact conversion table (1/64 to 63/64), plus mixed-number formatting: 50.25 in → 50-1/4 in.
Vocabulary conformance	Value must exist in the LOV for that classpath. Near-misses go through fuzzy match (RapidFuzz) with a threshold; below threshold → reject, don't snap.
Statistical outlier	Per family + attribute, fit the observed distribution from the corpus. Flag values outside it. Ranges are derived at runtime, never hardcoded.
Cross-field contradiction	Small rule set plus one LLM plausibility pass on assembled records only.
Entity resolution for manufacturer/brand sits here too: Part_Manuf is a distributor code, so resolving Appliance Dealers Cooperative (APPDE) → Rheem Manufacturing is a lookup + fuzzy match against the approved manufacturer list, with exact casing and ®/™ preserved from the canonical entry.

Step 5 — Deterministic composition
No LLM. Template functions over the validated fact layer.

python
short_desc = join(brand, series, mpn, item_type,
                  *key_attrs_in_schema_order)
Field order comes from the category schema, so it's data-driven rather than per-category code.

INVOICE_DESC (≤40 chars, uppercase) is a constrained compression: tokens carry priority weights from the schema, and a greedy loop drops lowest-priority tokens until the string fits, applying approved abbreviations first. Deterministic and always compliant — a length assertion in the test suite, not a hope.

Because all five descriptions read the same fact layer, mutual consistency is structural.

Step 6 — Provenance and confidence
Internally each cell is an object, not a string:

json
{
  "value": "2700",
  "uom": "K",
  "state": "PARSED",
  "confidence": 0.96,
  "evidence": {"span": [18, 21], "source": "Part_Desc"},
  "reason": "Matched slot_4 of Philips LED template"
}
Confidence is composed from parse-template fit, vocabulary match strength, consensus agreement ratio, and retrieval score — then calibrated on the labelled ground-truth rows (isotonic regression) so 0.9 actually means 90%. That calibration curve is a slide.

Two writers serialise the same objects: the 252-column CSV/XLSX (values only, headers untouched) and a parallel provenance file of identical shape.

Step 7 — Correction propagation
A reviewer edit is stored as a rule, not a cell patch: {scope: Part_Manuf == "Black & Decker/dewlt (2585)", field: MANUFACTURER_NAME, value: ...}. Re-run the rule set over the batch, report affected rows, mark any downstream composed fields dirty and recompose them. That's why one fix reports "applied to 55 rows."

Execution
Async worker pool over rows, batched model calls, checkpointed to SQLite so a failed row doesn't kill a run and a batch can resume. Aggressive caching: parse templates cached per family, retrieval results cached per part number, classification cached per manufacturer+signature. Most rows complete with zero model calls after the first few in their family.

Stack: Python, FastAPI, Claude API, sentence-transformers + FAISS, pandas/openpyxl, RapidFuzz, SQLite, React for the reviewer queue.

What we can prove
Field-level accuracy vs. the labelled rows, per field and per category
Coverage–accuracy curve at 100/90/70% auto-approval
Calibration plot
LOV conformance %
Character-limit compliance (asserted, so it's 100% or the build fails)
Held-out-manufacturer accuracy — the no-hardcoding proof
Cost and latency per 1,000 SKUs
The honest summary: the LLM is used sparingly and always inside a constraint. It classifies, it induces a template once per family, it reads a retrieved document. It never freely writes a value, and it never writes the descriptions. That's why the output can be checked — and why it's cheap.







Capsule Hub
Claude is AI and can make mistakes. Please double-check responses.







