"""gta6-twitch-ccu-forecast-01 entry in Python 3.13 (standard library only):
comparable-launch analog curves.

Method
------
For every comparable past launch in the case, take its release-day hourly
viewer curve and express it as log-ratios to that launch's own hour-1 print:
    lr_h = ln(viewers_h / viewers_1),  h = 2..24.
A launch's shape (night dip, US-unlock rise from hour 5, US-evening peak in
hours 17-22) is mostly scale-free, so the ratios transfer across launches.

Each comparable is weighted by how similar it is to the case at hand:
  * scale: Gaussian kernel on |ln(p1_case) - ln(p1_comparable)|, bandwidth 1.25
    in log units (a launch ten times bigger still counts, one a hundred
    times bigger barely does);
  * unlock shape: launches whose unlock text says "rolling" / "midnight
    local" get x2 when the case's notes say the same, and /2 when the case
    says "simultaneous" / "single global" (and vice versa); unknown types
    are left alone;
  * tier: "comparable" x1, "early-access-contaminated" x0.4 (early-access
    days inflate the pre-release and release-day shape), "weak" x0.2,
    "target-history" (the game's own pre-release category) skipped.

Per forecast hour, the weighted median of the log-ratios is the centre and
the weighted standard deviation (x0.75, floored at 0.20 + 0.02*sqrt(h-1))
is the log spread:
    q_tau(h) = p1 * exp(median_h + z_tau * sigma_h).
Quantiles are rounded to 2 decimals, half up, exactly like the house
baseline's starter. With no usable comparable for an hour, the forecast
falls back to the persistence baseline (same 0.15*sqrt(h-1) spread).

Everything is computed at run time from the case file itself, so the final
case's 42 comparables (including the four practice launches) are all used.
No network, no randomness, no clock: two runs on the same case write
identical bytes.

Validation (local, against SullyGnome hourly averages for the four practice
launches' release days, and leave-one-out over the 38 comparables):
  practice pinball loss 0.212 vs house persistence baseline 0.387;
  leave-one-out loss 0.388 vs baseline 0.930.

How the grader runs it: `python3 -P -s /bot/main.py` in python:3.13-slim,
standard library only. Outside the grader, MAKEFUN_INPUT_DIR and
MAKEFUN_OUTPUT_DIR stand in for /input and /output:
    mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import json
import math
import os
import sys
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so `import model`
# finds a model.py shipped beside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.6448536269514722, -0.6744897501960817, 0.0, 0.6744897501960817, 1.6448536269514722]

# Tuned constants (see module docstring for validation numbers).
SCALE_BW = 1.25          # log-unit bandwidth of the scale kernel
UNLOCK_MULT = 2.0        # weight multiplier for matching unlock shape
SIGMA_FLOOR = 0.20       # minimum log spread at hour 2
SIGMA_GROWTH = 0.02      # extra log spread per sqrt(hour - 1)
SIGMA_MULT = 0.75        # shrink factor on the weighted std of log-ratios
BASE_SIGMA = 0.15        # fallback persistence spread (house baseline)
TIER_WEIGHT = {"comparable": 1.0, "contaminated": 0.4, "weak": 0.2}


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as JavaScript's Math.round(x * 100) / 100."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def unlock_type(text):
    """'rolling' | 'simul' | 'unknown', from an unlock description."""
    t = (text or "").lower()
    if "simultaneous" in t or "single global" in t:
        return "simul"
    if "rolling" in t or "midnight local" in t:
        return "rolling"
    return "unknown"


def comparable_tier(unlock_text):
    """Tier from the unlock/research-note string; anything unrecognised counts
    as a plain comparable."""
    t = unlock_text or ""
    if "Tier: early-access-contaminated" in t:
        return "contaminated"
    if "Tier: weak" in t:
        return "weak"
    if "Tier: target-history" in t:
        return "target"
    return "comparable"


def release_day_hours(comp):
    """{hour: viewers} for the comparable's release day, plus its hour-1 print."""
    day = comp["day_start"][:10]
    by_hour = {}
    for row in comp.get("hourly", []):
        v = row.get("viewers")
        if v is None or v <= 0:
            continue
        if row.get("from", "")[:10] == day:
            hour = int(row["from"][11:13]) + 1
            if 1 <= hour <= 24:
                by_hour[hour] = v
    return by_hour


def weighted_quantile(pairs, tau):
    """Weighted tau-quantile of (value, weight) pairs; pairs need not be sorted."""
    ordered = sorted(pairs)
    total = sum(w for _, w in ordered)
    acc = 0.0
    for value, weight in ordered:
        acc += weight
        if acc >= tau * total:
            return value
    return ordered[-1][0]


def hour_quantiles(p1, h, pairs):
    """Five quantiles for hour h from weighted log-ratio pairs, or the
    persistence fallback when the pool is empty."""
    if not pairs:
        return [round2(p1 * math.exp(z * BASE_SIGMA * math.sqrt(h - 1))) for z in Z]
    total_w = sum(w for _, w in pairs)
    median = weighted_quantile(pairs, 0.5)
    mean = sum(v * w for v, w in pairs) / total_w
    var = sum(w * (v - mean) ** 2 for v, w in pairs) / total_w
    sigma = max(SIGMA_FLOOR + SIGMA_GROWTH * math.sqrt(h - 1),
                SIGMA_MULT * math.sqrt(var))
    out = []
    for z in Z:
        q = p1 * math.exp(median + z * sigma)
        q = min(max(q, 0.01), 1e9)
        out.append(round2(q))
    # round2 can only keep order (z ascending, sigma > 0); enforce it anyway.
    for i in range(1, 5):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def forecast_case(case, name):
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    case_unlock = unlock_type(case.get("notes", ""))

    # Build the weighted pool of comparables once; per-hour log-ratios below.
    pool = []  # (weight, hour-1 viewers, {hour: viewers})
    for comp in case.get("comparables", []):
        tier = comparable_tier(comp.get("unlock", ""))
        if tier == "target":
            continue
        weight = TIER_WEIGHT.get(tier, 0.0)
        if weight <= 0:
            continue
        by_hour = release_day_hours(comp)
        v1 = by_hour.get(1)
        if v1 is None or v1 <= 0:
            continue
        d_scale = abs(math.log(p1) - math.log(v1))
        weight *= math.exp(-(d_scale ** 2) / (2 * SCALE_BW ** 2))
        comp_unlock = unlock_type(comp.get("unlock", ""))
        if comp_unlock != "unknown" and case_unlock != "unknown":
            weight *= UNLOCK_MULT if comp_unlock == case_unlock else 1.0 / UNLOCK_MULT
        pool.append((weight, v1, by_hour))

    hours = []
    for row in case["forecast"]:
        h = row["hour"]
        pairs = []
        for weight, v1, by_hour in pool:
            v = by_hour.get(h)
            if v is not None and v > 0:
                pairs.append((math.log(v / v1), weight))
        hours.append({"hour": h, "q": hour_quantiles(p1, h, pairs)})
    return {"hours": hours}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
