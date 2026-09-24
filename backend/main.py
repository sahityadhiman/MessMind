from pathlib import Path
import sqlite3
from datetime import date, datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="MessMind API", version="0.1.0")
DATABASE_PATH = Path(__file__).resolve().parent / "messmind.db"


def initialize_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS meal_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_date TEXT NOT NULL,
                meal TEXT NOT NULL,
                menu TEXT NOT NULL,
                students INTEGER NOT NULL,
                meals_served INTEGER NOT NULL,
                is_demo INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        existing_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(meal_records)")
        }
        if "is_demo" not in existing_columns:
            connection.execute(
                "ALTER TABLE meal_records ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 1"
            )


initialize_database()


class MealPredictionRequest(BaseModel):
    meal: str = Field(min_length=1, max_length=30)
    menu: str = Field(min_length=1, max_length=200)
    students: int = Field(gt=0, le=100_000)


class MealPredictionResponse(BaseModel):
    meal: str
    menu: str
    students: int
    students_expected: int
    attendance_rate: float
    is_sample: bool = True


class MealRecordRequest(BaseModel):
    meal_date: date
    meal: str = Field(min_length=1, max_length=30)
    menu: str = Field(min_length=1, max_length=200)
    students: int = Field(gt=0, le=100_000)
    meals_served: int = Field(ge=0, le=100_000)
    is_demo: bool = True


class MealRecordResponse(MealRecordRequest):
    id: int


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "MessMind API is running"}


@app.post("/predict", response_model=MealPredictionResponse)
def predict_attendance(request: MealPredictionRequest):
    # Temporary baseline until the team adds real attendance data and an ML model.
    attendance_rate = 0.82
    return MealPredictionResponse(
        meal=request.meal,
        menu=request.menu,
        students=request.students,
        students_expected=round(request.students * attendance_rate),
        attendance_rate=attendance_rate,
    )


@app.post("/records", response_model=MealRecordResponse, status_code=201)
def create_meal_record(record: MealRecordRequest):
    if record.meals_served > record.students:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="Meals served cannot be greater than students eligible.",
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO meal_records
                (meal_date, meal, menu, students, meals_served, is_demo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.meal_date.isoformat(),
                record.meal,
                record.menu,
                record.students,
                record.meals_served,
                int(record.is_demo),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        record_id = cursor.lastrowid

    return MealRecordResponse(id=record_id, **record.model_dump())


@app.get("/records", response_model=list[MealRecordResponse])
def list_meal_records():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, meal_date, meal, menu, students, meals_served
                 , is_demo
            FROM meal_records
            ORDER BY meal_date DESC, id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


# Serve the webpage from this same local server so the browser can call the API.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
