"""Every assumption the generator uses, in one place.

Nothing here is measured: these are plausible starting values for a mid-sized
B2B software company. Change a value and rerun the generator; simulation code
never hard-codes a number.

Delays are lognormal and stated as (median_hours, sigma) in *working* hours.
The median is the typical wait; sigma controls the long tail (0.5 = tight,
1.0+ = some waits run many times longer than typical).
"""

from datetime import date

# --- Reproducibility --------------------------------------------------------
SEED = 42

# --- Volume and observation window -----------------------------------------
N_CASES = 2_000
WINDOW_START = date(2026, 1, 5)  # a Monday
WINDOW_END = date(2026, 6, 30)   # events after 18:00 on this day are cut off

# --- Working hours (Singapore, no daylight saving) --------------------------
UTC_OFFSET_HOURS = 8
WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 18
WEEKMASK = "Mon Tue Wed Thu Fri"

# --- Case attribute mixes (each must sum to 1.0) ----------------------------
SOURCE_MIX = {"support_ticket": 0.45, "sales_call": 0.20, "survey": 0.15, "in_app": 0.20}
DETAIL_MIX = {"low": 0.35, "medium": 0.40, "high": 0.25}
TIER_MIX = {"enterprise": 0.20, "mid_market": 0.45, "smb": 0.35}
PRODUCT_AREA_MIX = {
    "billing": 0.18,
    "reporting": 0.20,
    "integrations": 0.20,
    "permissions": 0.12,
    "onboarding": 0.15,
    "mobile": 0.15,
}

# --- People (anonymised IDs only, never names) ------------------------------
# Who submits feedback depends on where it came from.
SUBMITTER_ROLE = {
    "support_ticket": "support_agent",
    "sales_call": "account_exec",
    "survey": "customer",
    "in_app": "customer",
}
ROLES = ["support_agent", "account_exec", "customer", "product_ops", "owner"]
# Pool size and ID prefix per role. Owners are split evenly across product areas.
RESOURCE_POOLS = {
    "support_agent": ("SUP", 12),
    "account_exec": ("AE", 8),
    "customer": ("CUS", 600),
    "product_ops": ("OPS", 4),
    "owner": ("OWN", 18),
}

# --- Channel: the medium each event happened through ------------------------
CHANNELS = ["tracker", "email", "chat", "call"]
SUBMISSION_CHANNEL = {
    "support_ticket": "tracker",
    "sales_call": "call",
    "survey": "tracker",
    "in_app": "tracker",
}
# Clarification requests: colleagues are asked on chat more often; customers by email.
CLARIFICATION_CHANNEL_MIX = {
    "internal": {"chat": 0.6, "email": 0.4},
    "customer": {"email": 1.0},
}
NUDGE_CHANNEL_MIX = {"chat": 0.7, "email": 0.3}
ESCALATION_CHANNEL_MIX = {"email": 0.5, "call": 0.5}
# Every other activity is recorded in the tracker.

# --- Intake: clarification loops ---------------------------------------------
# THE KEY ASSUMPTION: vague feedback needs clarifying far more often.
DETAIL_EFFECT_ON = True
P_NEEDS_CLARIFICATION = {"low": 0.70, "medium": 0.35, "high": 0.10}
# With the effect off, every detail level uses the DETAIL_MIX-weighted average
# of the values above, so total clarification workload stays about the same.
P_STILL_UNCLEAR = 0.25           # after a reply, another round is needed
MAX_CLARIFICATION_LOOPS = 3
P_PROVIDER_NEVER_REPLIES = {"internal": 0.05, "customer": 0.25}

# --- Duplicates and routing -------------------------------------------------
P_DUPLICATE = 0.12
P_MISROUTED = 0.10               # chance each routing goes to the wrong area
MAX_REASSIGNMENTS = 2

# --- Owner follow-through ---------------------------------------------------
NUDGE_INTERVAL_DAYS = 3          # product ops nudges every N working days of silence
STALE_AFTER_DAYS = 20            # no response within N working days -> closed as stale
ESCALATE_AFTER_NUDGES = 3        # escalation is considered once, at this many nudges
P_ESCALATE = 0.15                # chance product ops decides to escalate at that point
# What the owner does after acknowledging (must sum to 1.0).
OUTCOME_MIX = {"resolved": 0.70, "wont_do": 0.20, "no_progress": 0.10}

# --- Delays: (median working hours, lognormal sigma) ------------------------
DELAYS = {
    "submit_to_triage": (4, 0.8),
    "triage_to_request": (0.5, 0.5),
    "reply_internal": (8, 1.0),
    "reply_customer": (24, 1.0),
    "process_reply": (3, 0.7),
    "to_routing_or_merge": (2, 0.7),
    "misroute_noticed": (12, 0.8),
    "owner_acknowledge": (16, 1.1),
    "escalation_raised": (2, 0.5),
    "after_escalation": (8, 0.7),
    "decide_wont_do": (16, 0.9),
    "start_work": (40, 1.0),
    "resolve_work": (60, 1.0),
}

# --- Handle time: (min, max) minutes of effort per activity -----------------
HANDLE_TIME_MIN = {
    "Feedback submitted": (5, 15),
    "Triaged": (3, 10),
    "Clarification requested": (5, 15),
    "Clarification received": (2, 8),
    "Merged as duplicate": (2, 6),
    "Routed to owner": (2, 5),
    "Reassigned": (5, 12),
    "Owner acknowledged": (1, 3),
    "Nudge sent": (3, 8),
    "Escalated": (15, 30),
    "In progress": (5, 10),
    "Resolved": (10, 30),
    "Won't do": (5, 10),
    "Closed as stale": (1, 3),
}

# --- Noise applied after simulation -----------------------------------------
MISSING_EVENT_RATE = 0.015
DUPLICATE_EVENT_RATE = 0.005

# --- Output -----------------------------------------------------------------
OUTPUT_PATH = "data/event_log.csv"
CASE_ID_PREFIX = "FB-"
CASE_ID_DIGITS = 5
