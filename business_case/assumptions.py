"""Every assumption the business case uses, in one place.

Uncertain inputs are (low, most likely, high) ranges: the simulation draws each
from a triangular distribution. None of these are quotes or measurements; they
are starting estimates to be replaced with real numbers in a live engagement.
The product ops hourly rate is NOT here: it comes from app/settings.py so the
readout and the business case can never disagree.
"""

# --- Simulation -------------------------------------------------------------
SEED = 0
N_RUNS = 10_000
HORIZON_YEARS = 3
MONTHS_PER_YEAR = 12
PAYBACK_TARGET_MONTHS = 12        # "pays back within a year"
PERCENTILES = (10, 50, 90)

# --- Shared costs -----------------------------------------------------------
ENGINEER_WEEKLY_COST = (2_800, 3_300, 4_000)   # SGD per engineer-week, fully loaded

# --- Recommendation rules (used by the brief and the app page) --------------
P_ROI_POSITIVE_MIN = 0.5          # below this, an option "does not pay back on hours alone"

# --- Value x feasibility chart ----------------------------------------------
VALUE_AXIS = (-50_000, 100_000)   # SGD, median 3-year net benefit; fixed, not rescaled

# --- App sliders --------------------------------------------------------------
SHARE_SLIDER_STEP = 0.05
COST_SLIDER_STEP = 100

# --- Feasibility (1 = hard, 5 = easy) ----------------------------------------
FEASIBILITY_WEIGHTS = {
    "complexity": 0.25,
    "data": 0.25,
    "adoption": 0.25,
    "risk": 0.15,
    "time_to_value": 0.10,
}
CRITERIA_LABELS = {
    "complexity": "Technical complexity",
    "data": "Data and integration",
    "adoption": "Adoption",
    "risk": "Risk",
    "time_to_value": "Time to value",
}

# --- Uncertain inputs every option has (zero where it doesn't apply) ---------
INPUT_LABELS = {
    "share_saved": "share of targeted effort saved",
    "build_weeks": "build effort (engineer-weeks)",
    "engineer_weekly_cost": "engineer weekly cost",
    "maintenance_share": "annual maintenance (share of build)",
    "run_cost": "annual run cost",
    "review_share": "share of items needing human review",
    "review_minutes": "minutes per review",
    "rescue_share": "share of lost items rescued",
}

# --- The options ----------------------------------------------------------------
OPTIONS = {
    "ai_intake": {
        "name": "AI intake clarity check",
        "pool": ["Clarification requested"],
        "pool_label": "clarification requests",
        "share_saved": (0.40, 0.60, 0.80),
        "build_weeks": (4, 6, 10),
        "maintenance_share": (0.15, 0.20, 0.30),
        "run_cost": (500, 1_500, 3_000),
        "review_share": (0.15, 0.25, 0.40),    # medium-confidence items product ops confirms
        "review_minutes": (1, 2, 4),
        "rescue_share": (0.30, 0.50, 0.70),
        "rests_on": "rescuing items now lost to unanswered questions and getting feedback to owners faster",
        "feasibility": {
            "complexity": (2, "classifier, LLM and confidence gating to build and tune"),
            "data": (3, "needs the feedback text at the moment of submission"),
            "adoption": (3, "providers answer while still engaged, but some will ignore questions"),
            "risk": (3, "wrong or annoying questions could put providers off"),
            "time_to_value": (2, "weeks to build, then tuning on real feedback"),
        },
    },
    "intake_form": {
        "name": "Structured intake form",
        "pool": ["Clarification requested"],
        "pool_label": "clarification requests",
        "share_saved": (0.15, 0.30, 0.45),
        "build_weeks": (1, 1.5, 3),
        "maintenance_share": (0.05, 0.10, 0.15),
        "run_cost": (0, 0, 0),
        "review_share": (0, 0, 0),
        "review_minutes": (0, 0, 0),
        "rescue_share": (0.10, 0.20, 0.35),
        "rests_on": "providers filling in mandatory fields properly rather than with filler",
        "feasibility": {
            "complexity": (5, "a few required fields on existing forms"),
            "data": (5, "no new data or integrations needed"),
            "adoption": (2, "rigid forms attract junk answers and can deter submissions"),
            "risk": (4, "low; easy to roll back"),
            "time_to_value": (5, "days"),
        },
    },
    "follow_through": {
        "name": "Owner follow-through",
        "pool": ["Nudge sent", "Escalated"],
        "pool_label": "nudges and escalations",
        "share_saved": (0.30, 0.50, 0.70),
        "build_weeks": (3, 5, 8),
        "maintenance_share": (0.10, 0.15, 0.25),
        "run_cost": (300, 1_000, 2_000),
        "review_share": (0, 0, 0),
        "review_minutes": (0, 0, 0),
        "rescue_share": (0, 0, 0),
        "rests_on": "owners acting on digests and an ageing view instead of waiting for one-off nudges",
        "feasibility": {
            "complexity": (3, "scheduling, digests and an ageing view"),
            "data": (4, "uses owner and timestamp fields the tracker already has"),
            "adoption": (3, "owners may ignore digests as they ignore nudges"),
            "risk": (4, "soft levers only; escalation stays human"),
            "time_to_value": (4, "a few weeks"),
        },
    },
}
