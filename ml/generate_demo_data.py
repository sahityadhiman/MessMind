"""Generate the reproducible, explicitly synthetic training examples."""

import csv
import math
import random
from pathlib import Path

from ml.menu_plan import MENU_PLAN

SEED = 20260925
WEEKS = 8
ELIGIBLE_STUDENTS = 1000
MEAL_RATES = {"Breakfast": 0.69, "Lunch": 0.83, "Snacks": 0.48, "Dinner": 0.75}
PORTION_KG = {"Breakfast": 0.38, "Lunch": 0.60, "Snacks": 0.18, "Dinner": 0.55}
POPULAR_ITEMS = (
    "paneer", "chole", "paratha", "poori", "puri", "bhature", "pizza",
    "patties", "rasgulla", "kheer", "haluwa", "halwa", "mushroom", "lassi",
    "sandwich", "ice cream", "pastrie", "pastry", "chaap",
)


def menu_features(menu):
    lowered = menu.lower()
    item_count = max(1, lowered.count("+") + lowered.count("/") + 1)
    appeal_count = sum(lowered.count(item) for item in POPULAR_ITEMS)
    return min(item_count, 12) / 12, min(appeal_count, 4) / 4


def model_features(day_index, meal, menu):
    variety, appeal = menu_features(menu)
    angle = (2 * math.pi * day_index) / 7
    return [
        1.0,
        float(meal == "Breakfast"),
        float(meal == "Lunch"),
        float(meal == "Dinner"),
        float(meal == "Snacks"),
        math.sin(angle),
        math.cos(angle),
        float(day_index >= 5),
        variety,
        appeal,
    ]


def create_rows(seed=SEED, weeks=WEEKS):
    rng = random.Random(seed)
    rows = []
    day_names = list(MENU_PLAN["days"])
    for week in range(1, weeks + 1):
        for day_index, day in enumerate(day_names):
            for meal in MENU_PLAN["meals"]:
                menu = MENU_PLAN["days"][day].get(meal)
                if not menu:
                    continue

                variety, appeal = menu_features(menu)
                angle = (2 * math.pi * day_index) / 7
                rate = (
                    MEAL_RATES[meal]
                    - (0.045 if day_index >= 5 else 0)
                    + 0.012 * math.sin(angle)
                    + 0.008 * math.cos(angle)
                    + (variety - 0.5) * 0.035
                    + appeal * 0.025
                    + rng.uniform(-0.035, 0.035)
                )
                rate = min(0.94, max(0.30, rate))
                served = round(ELIGIBLE_STUDENTS * rate)
                reserve_rate = rng.uniform(0.06, 0.11)
                prepared = min(
                    ELIGIBLE_STUDENTS,
                    math.ceil(served * (1 + reserve_rate)),
                )
                plate_leftover_kg = rng.uniform(0.020, 0.055)
                waste_kg = round(
                    max(0, (prepared - served) * PORTION_KG[meal]
                    + served * plate_leftover_kg),
                    2,
                )
                rows.append(
                    {
                        "scenario_week": week,
                        "weekday": day,
                        "meal": meal,
                        "meal_time": MENU_PLAN["meal_times"][meal],
                        "menu": menu,
                        "students_eligible": ELIGIBLE_STUDENTS,
                        "attendance_rate_simulated": round(rate, 4),
                        "meals_served_simulated": served,
                        "portions_prepared_simulated": prepared,
                        "food_waste_kg_simulated": waste_kg,
                    }
                )
    return rows


def write_csv(path=None):
    output = path or Path(__file__).parent / "data" / "demo_training_data.csv"
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = create_rows()
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic rows to {output}")


if __name__ == "__main__":
    write_csv()
