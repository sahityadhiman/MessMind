from pathlib import Path
import os
import secrets
import sqlite3
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
load_dotenv(BACKEND_DIR / ".env")

app = FastAPI(title="MessMind API", version="0.1.0")
DATABASE_PATH = BACKEND_DIR / "messmind.db"
staff_auth = HTTPBasic()


def require_staff(credentials: HTTPBasicCredentials = Depends(staff_auth)):
    expected_username = os.getenv("MESSMIND_ADMIN_USERNAME", "mess-manager")
    expected_password = os.getenv("MESSMIND_ADMIN_PASSWORD", "")
    if not expected_password:
        raise HTTPException(
            status_code=503,
            detail="Staff access is not configured. Set it in backend/.env first.",
        )

    username_matches = secrets.compare_digest(
        credentials.username.encode("utf-8"), expected_username.encode("utf-8")
    )
    password_matches = secrets.compare_digest(
        credentials.password.encode("utf-8"), expected_password.encode("utf-8")
    )
    if not (username_matches and password_matches):
        raise HTTPException(
            status_code=401,
            detail="Incorrect staff username or password.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


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
    students_expected: int | None
    attendance_rate: float | None
    records_used: int
    is_sample: bool = False
    message: str


class MealRecordRequest(BaseModel):
    meal_date: date
    meal: str = Field(min_length=1, max_length=30)
    menu: str = Field(min_length=1, max_length=200)
    students: int = Field(gt=0, le=100_000)
    meals_served: int = Field(ge=0, le=100_000)
    is_demo: bool = False


class MealRecordResponse(MealRecordRequest):
    id: int


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "MessMind API is running"}


@app.get("/admin", include_in_schema=False)
def staff_admin_page(_staff: str = Depends(require_staff)):
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.post("/predict", response_model=MealPredictionResponse)
def predict_attendance(request: MealPredictionRequest):
    # Use recent records for this meal only. Demo rows are never prediction data.
    with sqlite3.connect(DATABASE_PATH) as connection:
        history = connection.execute(
            """
            SELECT students, meals_served
            FROM meal_records
            WHERE is_demo = 0 AND LOWER(meal) = LOWER(?)
            ORDER BY meal_date DESC, id DESC
            LIMIT 30
            """,
            (request.meal,),
        ).fetchall()

    if not history:
        return MealPredictionResponse(
            meal=request.meal,
            menu=request.menu,
            students=request.students,
            students_expected=None,
            attendance_rate=None,
            records_used=0,
            message=(
                "No real attendance records are available for this meal yet. "
                "Add approved real records to get a history-based estimate."
            ),
        )

    total_students = sum(row[0] for row in history)
    total_meals_served = sum(row[1] for row in history)
    attendance_rate = total_meals_served / total_students
    return MealPredictionResponse(
        meal=request.meal,
        menu=request.menu,
        students=request.students,
        students_expected=round(request.students * attendance_rate),
        attendance_rate=attendance_rate,
        records_used=len(history),
        message=(
            f"Rough estimate from the last {len(history)} real "
            f"{request.meal.lower()} meal records. Menu and weekday are not "
            "included yet."
        ),
    )


@app.post("/records", response_model=MealRecordResponse, status_code=201)
def create_meal_record(
    record: MealRecordRequest, _staff: str = Depends(require_staff)
):
    if record.meals_served > record.students:
        raise HTTPException(
            status_code=400,
            detail="Meals served cannot be greater than students eligible.",
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        duplicate = connection.execute(
            """
            SELECT id
            FROM meal_records
            WHERE meal_date = ?
              AND LOWER(meal) = LOWER(?)
              AND is_demo = ?
            LIMIT 1
            """,
            (record.meal_date.isoformat(), record.meal, int(record.is_demo)),
        ).fetchone()
        if duplicate:
            record_type = "demo" if record.is_demo else "real"
            raise HTTPException(
                status_code=409,
                detail=(
                    f"A {record_type} {record.meal.lower()} record already exists "
                    f"for {record.meal_date.isoformat()}. Each date and meal can "
                    "only be entered once."
                ),
            )

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
def list_meal_records(_staff: str = Depends(require_staff)):
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


@app.delete("/records/{record_id}", status_code=204)
def delete_demo_meal_record(
    record_id: int, _staff: str = Depends(require_staff)
):
    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(
            "DELETE FROM meal_records WHERE id = ? AND is_demo = 1",
            (record_id,),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Demo record not found. Real records cannot be removed here.",
            )
    return Response(status_code=204)


# Serve the student page from this same local server so it can call the API.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
