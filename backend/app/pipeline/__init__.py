"""The seven-stage enrichment pipeline. See docs/01-architecture.md.

Each stage is a separate module with a narrow contract so the four of us can
work in parallel without stepping on each other:

    stage                module                 owner
    1 CLASSIFY           classify.py            (unassigned)
    2 PARSE              parse.py               (unassigned)
      template induction template_induction.py  (unassigned)
    3 ENRICH  3a         consensus.py           (unassigned)
              3b         retrieve.py            (unassigned)
    4 VALIDATE           validate.py            (unassigned)
    5 COMPOSE            compose.py             (unassigned)
    7 PROPAGATE          rules.py               (unassigned)

Put your name in that table when you pick one up.
"""

from app.pipeline.runner import run_pipeline

__all__ = ["run_pipeline"]
