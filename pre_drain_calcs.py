"""
Pre-drain calculations helper.

Purpose: Given a 6-character Murata battery code and two dates (pod manufacturing
and pre-drain dates), compute aging narrative and pre-drain discharge minutes,
plus intermediate capacity contributions.

Usage:
  python pre_drain_calcs.py 1YD082 04/12/2025 05/10/2025

Output: JSON with fields such as `narrative`, `c_total_mAh`, and `discharge_minutes`.

Notes:
- The battery code format is assumed to be: [digit][A–Z][A–L][digit][digit][digit]
  Example: 1YD082 (year=Y, month=D, day=08 -> 2025-04-08)
- All calculations use days, mAh, mA, and minutes as units where appropriate.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
import argparse
import json
import re


# Domain constants (units in names)
SELF_DISCHARGE_RATE_PER_YEAR = 0.05            # fraction per year
BATTERY_CAPACITY_MAH = 133.73                  # mAh
EXPECTED_LIFETIME_DAYS = 1186.38               # days
POD_SHELF_LIFE_DAYS = 730.08                   # days
POD_QUIESCENT_CURRENT_MA = 0.000124            # mA (124 nA)
PRE_DRAIN_CURRENT_MA = 2.0                     # mA


@dataclass
class PreDrainResult:
    narrative: str
    t_time_remaining_days: float
    c_battery_self_discharge_mAh: float
    c_storage_pod_quiescent_current_mAh: float
    c_sterilization_mAh: float
    c_shipping_mAh: float
    c_total_mAh: float
    discharge_minutes: int
    battery_manufacture_date: date


def parse_battery_code(code: str) -> date:
    """Parse a 6-character Murata battery code into a manufacture date.

    Format: [digit][A–Z][A–L][digit][digit][digit]
    - Year letter: A=2001, B=2002, ..., Z=2026
    - Month letter: A=1 (Jan), ..., L=12 (Dec)
    - Day: two digits
    """
    if not isinstance(code, str):
        raise TypeError("Battery code must be a string")

    code = code.strip().upper()
    if not re.fullmatch(r"[0-9][A-Z][A-L][0-9]{3}", code):
        raise ValueError(
            "Battery code must look like 1YD082 (6 chars, month A–L)."
        )

    year_letter = code[1]
    month_letter = code[2]
    day_digits = code[3:5]

    year = 2001 + (ord(year_letter) - ord("A"))
    month = (ord(month_letter) - ord("A")) + 1
    day = int(day_digits)

    # datetime will validate calendar correctness (e.g., 02/30 is invalid)
    return date(year, month, day)


def days_between_mmddyyyy(d1: str, d2: str) -> int:
    """Absolute number of days between two MM/DD/YYYY strings."""
    fmt = "%m/%d/%Y"
    try:
        left = datetime.strptime(d1, fmt).date()
        right = datetime.strptime(d2, fmt).date()
    except ValueError as exc:
        raise ValueError("Dates must be in MM/DD/YYYY format and valid calendar dates") from exc
    return abs((right - left).days)


def compute_pre_drain(battery_code: str, pod_manu_mmddyyyy: str, pre_drain_mmddyyyy: str) -> PreDrainResult:
    """Compute narrative, capacity contributions, and discharge minutes.

    Returns a PreDrainResult with structured numeric fields.
    """
    battery_date = parse_battery_code(battery_code)
    bat_mmddyyyy = battery_date.strftime("%m/%d/%Y")

    days_bat_to_pod = days_between_mmddyyyy(bat_mmddyyyy, pod_manu_mmddyyyy)
    days_pod_to_pre = days_between_mmddyyyy(pod_manu_mmddyyyy, pre_drain_mmddyyyy)

    months_bat_to_pod = round(days_bat_to_pod / 30)
    months_pod_to_pre = round(days_pod_to_pre / 30)
    total_days = days_bat_to_pod + days_pod_to_pre
    total_months = months_bat_to_pod + months_pod_to_pre

    narrative = (
        f"Batteries are installed in Pods {months_bat_to_pod} months after manufacturing ("\
        f"{days_bat_to_pod} days) and the Pods have aged {months_pod_to_pre} months since Pod "\
        f"Manufacturing ({days_pod_to_pre} days) for a total Battery age of {total_months} "\
        f"months ({total_days} days total)."
    )

    # Battery self-discharge
    t_remaining_days = max(EXPECTED_LIFETIME_DAYS - total_days, 0.0)
    c_self_discharge_mAh = (
        SELF_DISCHARGE_RATE_PER_YEAR * (t_remaining_days / 365.24) * BATTERY_CAPACITY_MAH
    )

    # Pod storage quiescent current
    t_shelf_remaining_days = max(POD_SHELF_LIFE_DAYS - days_pod_to_pre, 0.0)
    c_quiescent_mAh = POD_QUIESCENT_CURRENT_MA * 24 * t_shelf_remaining_days

    # Sterilization and shipping constants (mAh)
    c_ster_mAh = 1.8502
    c_ship_mAh = 1.037

    c_total_mAh = c_self_discharge_mAh + c_quiescent_mAh + c_ster_mAh + c_ship_mAh

    # Convert to minutes at pre-drain current
    discharge_minutes = round((c_total_mAh / PRE_DRAIN_CURRENT_MA) * 60)

    return PreDrainResult(
        narrative=narrative,
        t_time_remaining_days=round(t_remaining_days, 2),
        c_battery_self_discharge_mAh=round(c_self_discharge_mAh, 4),
        c_storage_pod_quiescent_current_mAh=round(c_quiescent_mAh, 4),
        c_sterilization_mAh=c_ster_mAh,
        c_shipping_mAh=c_ship_mAh,
        c_total_mAh=round(c_total_mAh, 4),
        discharge_minutes=discharge_minutes,
        battery_manufacture_date=battery_date,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute pre-drain minutes and related metrics.")
    parser.add_argument("battery_code", help="Battery code, e.g., 1YD082")
    parser.add_argument("pod_manu_date", help="Pod manufacturing date MM/DD/YYYY")
    parser.add_argument("pre_drain_date", help="Pre-drain start date MM/DD/YYYY")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    result = compute_pre_drain(args.battery_code, args.pod_manu_date, args.pre_drain_date)
    if args.pretty:
        print(json.dumps(asdict(result), default=str, indent=2))
    else:
        print(json.dumps(asdict(result), default=str))


if __name__ == "__main__":
    main()
