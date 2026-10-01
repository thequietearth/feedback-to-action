"""Generate a synthetic event log of customer feedback items.

Run:  python generator/generate.py [--seed N] [--out PATH] [--no-detail-effect]

All assumptions live in config.py. This file holds logic only.
"""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config

COLUMNS = [
    "case_id", "activity", "timestamp", "channel", "role", "resource",
    "handle_time_min", "source", "product_area", "detail_level", "customer_tier",
]
TERMINAL_ACTIVITIES = {"Merged as duplicate", "Resolved", "Won't do", "Closed as stale"}

# --- Working-time clock -------------------------------------------------------
# The simulation measures time in "working minutes" counted from 09:00 on
# WINDOW_START. Delays are added as plain integers, so nights and weekends can
# never leak in. Conversion to calendar time happens in one place: to_calendar().

TZ = timezone(timedelta(hours=config.UTC_OFFSET_HOURS))
MINUTES_PER_DAY = (config.WORKDAY_END_HOUR - config.WORKDAY_START_HOUR) * 60
WINDOW_START_NP = np.datetime64(config.WINDOW_START, "D")


def to_calendar(offset: int) -> datetime:
    """Convert a working-minute offset into a calendar timestamp (UTC+08:00)."""
    day_index, minute = divmod(int(offset), MINUTES_PER_DAY)
    day = np.busday_offset(WINDOW_START_NP, day_index, roll="forward", weekmask=config.WEEKMASK)
    start = datetime.fromisoformat(str(day)).replace(hour=config.WORKDAY_START_HOUR, tzinfo=TZ)
    return start + timedelta(minutes=minute)


def to_offset(ts: datetime) -> int:
    """Convert a calendar timestamp into a working-minute offset.

    Times outside working hours snap forward to the next working minute:
    before 09:00 -> 09:00 that day; after 18:00 or at a weekend -> 09:00 on the
    next working day.
    """
    ts = ts.astimezone(TZ)
    day = np.datetime64(ts.date(), "D")
    minute = (ts.hour - config.WORKDAY_START_HOUR) * 60 + ts.minute
    if not np.is_busday(day, weekmask=config.WEEKMASK) or minute >= MINUTES_PER_DAY:
        day = np.busday_offset(day, 1 if np.is_busday(day, weekmask=config.WEEKMASK) else 0,
                               roll="forward", weekmask=config.WEEKMASK)
        minute = 0
    minute = max(minute, 0)
    day_index = int(np.busday_count(WINDOW_START_NP, day, weekmask=config.WEEKMASK))
    return day_index * MINUTES_PER_DAY + minute


def add_working_minutes(ts: datetime, minutes: int) -> datetime:
    """Add working minutes to a timestamp, skipping nights and weekends."""
    return to_calendar(to_offset(ts) + minutes)


def observation_end_offset() -> int:
    """First working minute *after* the observation window (18:00 on WINDOW_END)."""
    days = int(np.busday_count(WINDOW_START_NP, np.datetime64(config.WINDOW_END, "D"),
                               weekmask=config.WEEKMASK))
    return (days + 1) * MINUTES_PER_DAY


def sample_submission_offsets(rng: np.random.Generator, n: int) -> np.ndarray:
    """Spread n submissions uniformly over every working minute in the window, sorted."""
    return np.sort(rng.integers(0, observation_end_offset(), size=n))


# --- Sampling helpers -----------------------------------------------------------

def choose(rng: np.random.Generator, mix: dict[str, float]) -> str:
    """Pick one key from a {value: probability} mix."""
    keys = list(mix)
    return keys[rng.choice(len(keys), p=list(mix.values()))]


def delay(rng: np.random.Generator, key: str) -> int:
    """Sample a lognormal wait from config.DELAYS, in whole working minutes (at least 1)."""
    median_hours, sigma = config.DELAYS[key]
    return max(1, round(median_hours * 60 * rng.lognormal(0.0, sigma)))


def resource_id(role: str, index: int) -> str:
    """Anonymised ID such as OPS-03: a role prefix and a number, never a name."""
    prefix, size = config.RESOURCE_POOLS[role]
    width = max(2, len(str(size)))
    return f"{prefix}-{index + 1:0{width}d}"


def pick_resource(rng: np.random.Generator, role: str) -> str:
    return resource_id(role, int(rng.integers(config.RESOURCE_POOLS[role][1])))


AREAS = list(config.PRODUCT_AREA_MIX)


def pick_owner(rng: np.random.Generator, area: str, wrong_area: bool = False) -> str:
    """Pick an owner for an area (owner i covers area i mod number of areas).

    With wrong_area=True, pick an owner from any *other* area (a misrouting).
    """
    n_owners = config.RESOURCE_POOLS["owner"][1]
    target = AREAS.index(area)
    pool = [i for i in range(n_owners) if (i % len(AREAS) == target) != wrong_area]
    return resource_id("owner", int(rng.choice(pool)))


def p_needs_clarification(detail: str, detail_effect: bool) -> float:
    """Chance a case needs clarifying. With the effect off, every level gets the
    DETAIL_MIX-weighted average, so total workload stays the same and only the
    pattern disappears."""
    if detail_effect:
        return config.P_NEEDS_CLARIFICATION[detail]
    return sum(config.DETAIL_MIX[d] * p for d, p in config.P_NEEDS_CLARIFICATION.items())


# --- Case simulation ------------------------------------------------------------

class Case:
    """One feedback item walking through its lifecycle.

    `t` is the case's current time in working minutes. Each stage advances `t`
    and records events; a stage returns False when the case has ended.
    """

    def __init__(self, rng: np.random.Generator, case_id: str, submitted_at: int, detail_effect: bool):
        self.rng = rng
        self.t = int(submitted_at)
        self.detail_effect = detail_effect
        self.events: list[dict] = []
        self.nudges = 0
        self.attrs = {
            "case_id": case_id,
            "source": choose(rng, config.SOURCE_MIX),
            "product_area": choose(rng, config.PRODUCT_AREA_MIX),
            "detail_level": choose(rng, config.DETAIL_MIX),
            "customer_tier": choose(rng, config.TIER_MIX),
        }
        self.submitter_role = config.SUBMITTER_ROLE[self.attrs["source"]]
        self.submitter = pick_resource(rng, self.submitter_role)
        self.provider_kind = "customer" if self.submitter_role == "customer" else "internal"
        self.ops = pick_resource(rng, "product_ops")  # one product ops handler per case

    def emit(self, activity: str, t: int, role: str, resource: str, channel: str = "tracker") -> None:
        lo, hi = config.HANDLE_TIME_MIN[activity]
        self.events.append({
            **self.attrs,
            "activity": activity,
            "offset": int(t),
            "channel": channel,
            "role": role,
            "resource": resource,
            "handle_time_min": int(self.rng.integers(lo, hi + 1)),
        })

    def close_stale(self, t: int) -> bool:
        self.t = t
        self.emit("Closed as stale", t, "product_ops", self.ops)
        return False

    # Stage 1: submission, triage and clarification loops.
    def intake(self) -> bool:
        rng = self.rng
        self.emit("Feedback submitted", self.t, self.submitter_role, self.submitter,
                  config.SUBMISSION_CHANNEL[self.attrs["source"]])
        self.t += delay(rng, "submit_to_triage")
        self.emit("Triaged", self.t, "product_ops", self.ops)

        needs = rng.random() < p_needs_clarification(self.attrs["detail_level"], self.detail_effect)
        loops = 0
        while needs and loops < config.MAX_CLARIFICATION_LOOPS:
            self.t += delay(rng, "triage_to_request" if loops == 0 else "process_reply")
            channel = choose(rng, config.CLARIFICATION_CHANNEL_MIX[self.provider_kind])
            self.emit("Clarification requested", self.t, "product_ops", self.ops, channel)
            if rng.random() < config.P_PROVIDER_NEVER_REPLIES[self.provider_kind]:
                return self.close_stale(self.t + config.STALE_AFTER_DAYS * MINUTES_PER_DAY)
            self.t += delay(rng, f"reply_{self.provider_kind}")
            self.emit("Clarification received", self.t, self.submitter_role, self.submitter, channel)
            loops += 1
            needs = rng.random() < config.P_STILL_UNCLEAR
        return True

    # Stage 2: merge as duplicate, or route (possibly to the wrong owner first).
    def merge_or_route(self) -> bool:
        rng = self.rng
        self.t += delay(rng, "to_routing_or_merge")
        if rng.random() < config.P_DUPLICATE:
            self.emit("Merged as duplicate", self.t, "product_ops", self.ops)
            return False
        self.emit("Routed to owner", self.t, "product_ops", self.ops)
        area = self.attrs["product_area"]
        reassignments = 0
        while reassignments < config.MAX_REASSIGNMENTS and rng.random() < config.P_MISROUTED:
            wrong_owner = pick_owner(rng, area, wrong_area=True)
            self.t += delay(rng, "misroute_noticed")
            self.emit("Reassigned", self.t, "owner", wrong_owner)
            reassignments += 1
        self.owner = pick_owner(rng, area)
        return True

    # Owner timer: code decides when nudges happen, not chance.
    def wait_for_owner(self, response_delay: int | None) -> bool:
        """Wait for the owner while product ops nudges every NUDGE_INTERVAL_DAYS.

        response_delay is how long the owner would take unprompted (never shown
        in the log); None means they would never act. Escalation is rare, only
        considered after ESCALATE_AFTER_NUDGES nudges, and shortens the wait.
        Returns True if the owner responded (self.t = response time), False if
        the case was closed as stale.
        """
        rng = self.rng
        start = self.t
        respond_at = None if response_delay is None else start + response_delay
        stale_at = start + config.STALE_AFTER_DAYS * MINUTES_PER_DAY
        interval = config.NUDGE_INTERVAL_DAYS * MINUTES_PER_DAY
        next_nudge = start + interval
        while True:
            if respond_at is not None and respond_at <= min(next_nudge, stale_at):
                self.t = respond_at
                return True
            if stale_at <= next_nudge:
                return self.close_stale(stale_at)
            self.emit("Nudge sent", next_nudge, "product_ops", self.ops, choose(rng, config.NUDGE_CHANNEL_MIX))
            self.nudges += 1
            # One human decision, taken once, when the nudge count reaches the threshold.
            if self.nudges == config.ESCALATE_AFTER_NUDGES and rng.random() < config.P_ESCALATE:
                escalated_at = next_nudge + delay(rng, "escalation_raised")
                self.emit("Escalated", escalated_at, "product_ops", self.ops,
                          choose(rng, config.ESCALATION_CHANNEL_MIX))
                respond_at = escalated_at + delay(rng, "after_escalation")
            next_nudge += interval

    # Stage 3: acknowledgement, then resolution, won't do, or going stale.
    def owner_phase(self) -> None:
        rng = self.rng
        if not self.wait_for_owner(delay(rng, "owner_acknowledge")):
            return
        self.emit("Owner acknowledged", self.t, "owner", self.owner)
        outcome = choose(rng, config.OUTCOME_MIX)
        if outcome == "wont_do":
            self.t += delay(rng, "decide_wont_do")
            self.emit("Won't do", self.t, "owner", self.owner)
            return
        start_delay = delay(rng, "start_work") if outcome == "resolved" else None
        if not self.wait_for_owner(start_delay):
            return
        self.emit("In progress", self.t, "owner", self.owner)
        self.t += delay(rng, "resolve_work")
        self.emit("Resolved", self.t, "owner", self.owner)

    def run(self) -> list[dict]:
        if self.intake() and self.merge_or_route():
            self.owner_phase()
        return self.events


def case_id(i: int) -> str:
    return f"{config.CASE_ID_PREFIX}{i + 1:0{config.CASE_ID_DIGITS}d}"


def offsets_to_timestamps(offsets: pd.Series) -> pd.Series:
    """Vectorised to_calendar(): working-minute offsets -> tz-aware timestamps."""
    values = offsets.to_numpy()
    days = np.busday_offset(WINDOW_START_NP, values // MINUTES_PER_DAY,
                            roll="forward", weekmask=config.WEEKMASK)
    minutes = config.WORKDAY_START_HOUR * 60 + values % MINUTES_PER_DAY
    local = days.astype("datetime64[m]") + minutes.astype("timedelta64[m]")
    return pd.Series(pd.to_datetime(local), index=offsets.index).dt.tz_localize(TZ)


def simulate(rng: np.random.Generator, n_cases: int = config.N_CASES,
             detail_effect: bool = config.DETAIL_EFFECT_ON) -> pd.DataFrame:
    """Simulate every case and return the clean (noise-free) event log.

    Events after the observation window are cut off (right-censoring), so
    late cases stay open, as in a real export.
    """
    submissions = sample_submission_offsets(rng, n_cases)
    events = []
    for i, submitted_at in enumerate(submissions):
        events.extend(Case(rng, case_id(i), submitted_at, detail_effect).run())
    log = pd.DataFrame(events)
    log = log[log["offset"] < observation_end_offset()]
    log = log.sort_values(["case_id", "offset"], kind="stable")
    log["timestamp"] = offsets_to_timestamps(log["offset"])
    return log[COLUMNS].reset_index(drop=True)


# --- Noise ----------------------------------------------------------------------

def add_noise(log: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Return a copy with events randomly dropped, then some rows duplicated.

    Applied after simulation so tests can tell "the simulation is wrong" apart
    from "noise removed the event".
    """
    kept = log[rng.random(len(log)) >= config.MISSING_EVENT_RATE]
    duplicates = kept[rng.random(len(kept)) < config.DUPLICATE_EVENT_RATE]
    noisy = pd.concat([kept, duplicates])
    return noisy.sort_values(["case_id", "timestamp"], kind="stable").reset_index(drop=True)


def build_log(seed: int = config.SEED, n_cases: int = config.N_CASES,
              detail_effect: bool = config.DETAIL_EFFECT_ON) -> pd.DataFrame:
    """Simulate, then add noise, from a single seeded random generator."""
    rng = np.random.default_rng(seed)
    return add_noise(simulate(rng, n_cases, detail_effect), rng)


# --- Output ---------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent


def write_csv(log: pd.DataFrame, path: Path) -> None:
    """Write the log with ISO 8601 timestamps (e.g. 2026-01-05T09:00:00+08:00).

    A fixed line ending keeps the file byte-identical on Windows and Linux.
    """
    out = log.copy()
    out["timestamp"] = out["timestamp"].map(lambda ts: ts.isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, lineterminator="\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic feedback event log.")
    parser.add_argument("--seed", type=int, default=config.SEED, help="random seed (default from config)")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / config.OUTPUT_PATH, help="output CSV path")
    parser.add_argument("--no-detail-effect", action="store_true",
                        help="turn off the detail-level/clarification link (for the 'no pattern' check)")
    args = parser.parse_args(argv)

    detail_effect = config.DETAIL_EFFECT_ON and not args.no_detail_effect
    log = build_log(seed=args.seed, detail_effect=detail_effect)
    write_csv(log, args.out)
    print(f"Wrote {len(log):,} events for {log['case_id'].nunique():,} cases to {args.out} "
          f"(seed={args.seed}, detail effect {'on' if detail_effect else 'off'})")


if __name__ == "__main__":
    main()
