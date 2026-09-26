"""Train on staff-entered, non-demo meal measurements only.

The model uses a chronological holdout and falls back to a same-meal historical
average unless the ridge model beats that simple baseline. This is a pilot
workflow, not a guarantee of kitchen accuracy.
"""

from datetime import date

from ml.demo_model import fit_ridge, predict as linear_predict
from ml.generate_demo_data import model_features

MIN_REAL_MODEL_ROWS = 35
MIN_MEAL_HISTORY_ROWS = 3
MAX_MODEL_HISTORY_ROWS = 500


def _features(row):
    meal_date = row["meal_date"]
    if isinstance(meal_date, str):
        meal_date = date.fromisoformat(meal_date)
    return model_features(meal_date.weekday(), row["meal"], row["menu"])


def _target(row, kind):
    if kind == "attendance":
        return row["meals_served"] / row["students"]
    return row["food_waste_kg"] * 1000 / row["students"]


def _meal_average(rows, meal, kind):
    matched = [row for row in rows if row["meal"].lower() == meal.lower()]
    if len(matched) < MIN_MEAL_HISTORY_ROWS:
        return None, len(matched)
    denominator = sum(row["students"] for row in matched)
    if kind == "attendance":
        return sum(row["meals_served"] for row in matched) / denominator, len(matched)
    return sum(row["food_waste_kg"] for row in matched) * 1000 / denominator, len(matched)


def _baseline_for_row(train_rows, row, kind):
    value, _count = _meal_average(train_rows, row["meal"], kind)
    if value is not None:
        return value
    denominator = sum(item["students"] for item in train_rows)
    if kind == "attendance":
        return sum(item["meals_served"] for item in train_rows) / denominator
    return sum(item["food_waste_kg"] for item in train_rows) * 1000 / denominator


def _validated_model(rows, kind):
    """Return a full-data model only when a time-ordered holdout beats baseline."""
    if len(rows) < MIN_REAL_MODEL_ROWS:
        return None

    ordered = sorted(rows, key=lambda row: (row["meal_date"], row.get("id", 0)))
    holdout_count = max(7, round(len(ordered) * 0.2))
    train_rows = ordered[:-holdout_count]
    holdout_rows = ordered[-holdout_count:]
    if len(train_rows) < 28:
        return None

    train_x = [_features(row) for row in train_rows]
    train_y = [_target(row, kind) for row in train_rows]
    holdout_x = [_features(row) for row in holdout_rows]
    holdout_y = [_target(row, kind) for row in holdout_rows]
    model = fit_ridge(train_x, train_y)

    model_mae = sum(
        abs(linear_predict(model, features) - actual)
        for features, actual in zip(holdout_x, holdout_y)
    ) / len(holdout_rows)
    baseline_mae = sum(
        abs(_baseline_for_row(train_rows, row, kind) - actual)
        for row, actual in zip(holdout_rows, holdout_y)
    ) / len(holdout_rows)

    # A small tolerance avoids switching to a more complex model on a rounding tie.
    if model_mae >= baseline_mae:
        return {
            "use_model": False,
            "rows": len(rows),
            "holdout_rows": len(holdout_rows),
            "validation_mae": model_mae,
            "baseline_mae": baseline_mae,
        }

    return {
        "use_model": True,
        "coefficients": fit_ridge(
            [_features(row) for row in ordered],
            [_target(row, kind) for row in ordered],
        ),
        "rows": len(rows),
        "holdout_rows": len(holdout_rows),
        "validation_mae": model_mae,
        "baseline_mae": baseline_mae,
    }


def predict_from_real_records(all_rows, meal, menu, target_date, students):
    """Return real-data estimates, or None until enough same-meal history exists."""
    attendance_rows = [
        row for row in all_rows
        if row["students"] > 0 and 0 <= row["meals_served"] <= row["students"]
    ]
    waste_rows = [
        row for row in attendance_rows
        if row.get("food_waste_kg") is not None and row["food_waste_kg"] >= 0
    ]

    attendance_model = _validated_model(attendance_rows, "attendance")
    if attendance_model and attendance_model["use_model"]:
        rate = linear_predict(
            attendance_model["coefficients"],
            model_features(target_date.weekday(), meal, menu),
        )
        attendance_method = "ridge model trained on real records"
        attendance_count = attendance_model["rows"]
        attendance_error = attendance_model["validation_mae"]
    else:
        rate, attendance_count = _meal_average(attendance_rows, meal, "attendance")
        attendance_method = "same-meal real-history average"
        attendance_error = None

    waste_model = _validated_model(waste_rows, "waste")
    if waste_model and waste_model["use_model"]:
        waste_per_1000 = linear_predict(
            waste_model["coefficients"],
            model_features(target_date.weekday(), meal, menu),
        )
        waste_method = "ridge model trained on measured waste"
        waste_count = waste_model["rows"]
        waste_error = waste_model["validation_mae"]
    else:
        waste_per_1000, waste_count = _meal_average(waste_rows, meal, "waste")
        waste_method = "same-meal measured-waste average"
        waste_error = None

    if rate is not None:
        rate = min(1.0, max(0.0, rate))
    if waste_per_1000 is not None:
        waste_per_1000 = max(0.0, waste_per_1000)

    return {
        "attendance_rate": rate,
        "attendance_records_used": attendance_count,
        "attendance_method": attendance_method if rate is not None else None,
        "attendance_validation_mae_rate": attendance_error,
        "food_waste_kg": (
            round(waste_per_1000 * students / 1000, 1)
            if waste_per_1000 is not None else None
        ),
        "waste_records_used": waste_count,
        "waste_method": waste_method if waste_per_1000 is not None else None,
        "waste_validation_mae_kg_per_1000": waste_error,
    }
