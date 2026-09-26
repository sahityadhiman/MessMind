"""Small, dependency-free ridge regression trained only on synthetic examples."""

import math

from ml.generate_demo_data import create_rows, model_features
from ml.menu_plan import MENU_PLAN

PORTION_KG = {"Breakfast": 0.38, "Lunch": 0.60, "Snacks": 0.18, "Dinner": 0.55}
MODEL_NAME = "Ridge regression"


def fit_ridge(features, targets, penalty=0.01):
    width = len(features[0])
    matrix = [[0.0] * width for _ in range(width)]
    vector = [0.0] * width
    for row, target in zip(features, targets):
        for i, left in enumerate(row):
            vector[i] += left * target
            for j, right in enumerate(row):
                matrix[i][j] += left * right
    for i in range(1, width):
        matrix[i][i] += penalty

    # Solve the small regularized normal-equation system with pivoted elimination.
    augmented = [matrix[row][:] + [vector[row]] for row in range(width)]
    for column in range(width):
        pivot = max(range(column, width), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            continue
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(width):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    value - factor * lead
                    for value, lead in zip(augmented[row], augmented[column])
                ]
    return [augmented[row][-1] for row in range(width)]


def predict(coefficients, features):
    return sum(weight * value for weight, value in zip(coefficients, features))


def training_features(row):
    weekday = row["weekday"]
    day_index = list(MENU_PLAN["days"]).index(weekday)
    return model_features(day_index, row["meal"], row["menu"])


def evaluate_holdout(rows):
    train_rows = [row for row in rows if int(row["scenario_week"]) < 8]
    holdout_rows = [row for row in rows if int(row["scenario_week"]) == 8]
    train_x = [training_features(row) for row in train_rows]
    attendance_model = fit_ridge(
        train_x, [float(row["attendance_rate_simulated"]) for row in train_rows]
    )
    waste_model = fit_ridge(
        train_x,
        [float(row["food_waste_kg_simulated"]) for row in train_rows],
    )
    attendance_errors = [
        abs(predict(attendance_model, training_features(row))
            - float(row["attendance_rate_simulated"]))
        for row in holdout_rows
    ]
    waste_errors = [
        abs(predict(waste_model, training_features(row))
            - float(row["food_waste_kg_simulated"]))
        for row in holdout_rows
    ]
    return {
        "holdout_rows": len(holdout_rows),
        "attendance_mae_rate": sum(attendance_errors) / len(attendance_errors),
        "waste_mae_kg_per_1000": sum(waste_errors) / len(waste_errors),
    }


DATASET_ROWS = create_rows()
TRAINING_ROWS = [row for row in DATASET_ROWS if int(row["scenario_week"]) < 8]
FEATURE_ROWS = [training_features(row) for row in TRAINING_ROWS]
ATTENDANCE_MODEL = fit_ridge(
    FEATURE_ROWS,
    [float(row["attendance_rate_simulated"]) for row in TRAINING_ROWS],
)
WASTE_MODEL = fit_ridge(
    FEATURE_ROWS,
    [float(row["food_waste_kg_simulated"]) for row in TRAINING_ROWS],
)
HOLDOUT = evaluate_holdout(DATASET_ROWS)


def predict_demo(day, meal, menu, students):
    day_index = list(MENU_PLAN["days"]).index(day)
    features = model_features(day_index, meal, menu)
    attendance_rate = min(0.97, max(0.15, predict(ATTENDANCE_MODEL, features)))
    expected = round(students * attendance_rate)
    reserve_portions = math.ceil(expected * 0.08)
    suggested = min(students, expected + reserve_portions)
    waste_per_1000 = max(0.0, predict(WASTE_MODEL, features))
    waste_kg = round(waste_per_1000 * students / 1000, 1)
    margin = math.ceil(students * HOLDOUT["attendance_mae_rate"])
    return {
        "day": day,
        "meal": meal,
        "menu": menu,
        "students_eligible": students,
        "expected_students": expected,
        "expected_students_low": max(0, expected - margin),
        "expected_students_high": min(students, expected + margin),
        "attendance_rate": round(attendance_rate, 4),
        "suggested_portions": suggested,
        "estimated_food_waste_kg": waste_kg,
        "is_simulation": True,
        "model_name": MODEL_NAME,
        "training_rows": len(TRAINING_ROWS),
        "dataset_rows": len(DATASET_ROWS),
        "holdout_rows": HOLDOUT["holdout_rows"],
        "synthetic_attendance_mae_percent": round(
            HOLDOUT["attendance_mae_rate"] * 100, 2
        ),
        "synthetic_waste_mae_kg_per_1000": round(
            HOLDOUT["waste_mae_kg_per_1000"], 2
        ),
        "portion_weight_kg_assumption": PORTION_KG[meal],
        "message": (
            "Simulation only. The model was trained and checked on generated examples, "
            "not measured mess records. Treat the output as a prototype illustration."
        ),
    }
