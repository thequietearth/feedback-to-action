"""Every assumption the discovery analysis uses, in one place.

These are analysis choices, separate from the generator's config: the app must
be able to read a real export in the same schema, where generator settings
would not exist. Change a value here and the app follows; analysis and display
code never hard-code a number.
"""

# --- Data -------------------------------------------------------------------
DATA_PATH = "data/event_log.csv"   # relative to the repo root
DATASET_DEFAULT = "Default (detail effect on)"
DATASET_EFFECT_OFF = "Detail effect off"

# --- Working calendar (Singapore, no public holidays) -----------------------
UTC_OFFSET_HOURS = 8
WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 18
WEEKMASK = "Mon Tue Wed Thu Fri"

# --- Lifecycle vocabulary ---------------------------------------------------
START_ACTIVITY = "Feedback submitted"
END_ACTIVITIES = ["Merged as duplicate", "Resolved", "Won't do", "Closed as stale"]
INTAKE_END_ACTIVITIES = ["Routed to owner", "Merged as duplicate"]
CLARIFICATION_ACTIVITY = "Clarification requested"
# Sequence rules: each activity on the left needs one of the activity on the
# right earlier in the same case (counted, so a second reply needs a second request).
REQUIRES_EARLIER = {
    "Clarification received": "Clarification requested",
    "Owner acknowledged": "Routed to owner",
}

# --- Who a wait is on: decided by the activity *before* the wait -------------
WAITING_ON = {
    "Feedback submitted": "product ops",
    "Triaged": "product ops",
    "Clarification received": "product ops",
    "Clarification requested": "provider",
    "Routed to owner": "owner",
    "Reassigned": "owner",
    "Nudge sent": "owner",
    "Escalated": "owner",
    "Owner acknowledged": "owner",
    "In progress": "owner working",
}
UNATTRIBUTED = "unattributed"   # a wait after any activity not listed above
# Time labelled with these is someone actively working, not a stall: it is
# reported on its own and left out of stall rankings and party shares.
ACTIVE_WORK = ["owner working"]

# --- Cost of chasing --------------------------------------------------------
CURRENCY = "SGD"
HOURLY_RATE = 60                 # product ops, fully loaded
HOURLY_RATE_MIN = 20             # sidebar slider bounds
HOURLY_RATE_MAX = 150
CHASING_ACTIVITIES = ["Clarification requested", "Nudge sent", "Escalated"]
REWORK_ACTIVITIES = ["Reassigned"]
WEEKS_PER_YEAR = 52

# --- Detail-level verdict ---------------------------------------------------
DETAIL_LEVELS = ["low", "medium", "high"]
DETAIL_LOW = "low"
DETAIL_HIGH = "high"
P_THRESHOLD = 0.05               # "unlikely to be chance"
MIN_EFFECT_RATIO = 1.5           # low-detail median must be at least this x high-detail
N_PERMUTATIONS = 5_000
PERMUTATION_SEED = 0

# --- Process map and tables -------------------------------------------------
MAP_MIN_EDGE_COUNT = 20          # default; adjustable in the sidebar
MAP_MIN_EDGE_COUNT_MAX = 500     # sidebar slider upper bound
EDGE_PENWIDTH_MIN = 1.0          # line thickness for the rarest and busiest shown edges
EDGE_PENWIDTH_MAX = 6.0
TOP_VARIANTS = 10
TOP_TRANSITIONS = 10
AGEING_BUCKETS_DAYS = [1, 5, 10, 20]   # open-item age bands, in working days
