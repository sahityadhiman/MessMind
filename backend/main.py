from pathlib import Path
import csv
import io
import os
import secrets
import sys
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    inspect,
    select,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Keep project-local model imports available when launched as `main:app` from backend/.
from ml.demo_model import DATASET_ROWS, HOLDOUT, MODEL_NAME, TRAINING_ROWS, predict_demo
from ml.menu_plan import MENU_PLAN
from ml.real_model import (
    MAX_MODEL_HISTORY_ROWS,
    MIN_MEAL_HISTORY_ROWS,
    MIN_REAL_MODEL_ROWS,
    predict_from_real_records,
)

load_dotenv(BACKEND_DIR / ".env")
IS_VERCEL_DEPLOYMENT = os.getenv("VERCEL") == "1"

app = FastAPI(title="MessMind API", version="0.1.0")
DATABASE_URL = (
    os.getenv("DATABASE_URL", "").strip()
    or os.getenv("POSTGRES_URL", "").strip()
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=1, max_overflow=0)
else:
    DEFAULT_DATABASE_PATH = (
        Path("/tmp/messmind.db")
        if IS_VERCEL_DEPLOYMENT
        else BACKEND_DIR / "messmind.db"
    )
    DATABASE_PATH = Path(
        os.getenv("MESSMIND_DATABASE_PATH", str(DEFAULT_DATABASE_PATH))
    )
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite+pysqlite:///{DATABASE_PATH.as_posix()}",
        connect_args={"check_same_thread": False},
    )

ALLOW_REAL_RECORDS = (
    not IS_VERCEL_DEPLOYMENT
    or (
        bool(DATABASE_URL)
        and os.getenv("MESSMIND_ENABLE_REAL_RECORDS", "").strip().lower()
        in {"1", "true", "yes"}
    )
)
staff_auth = HTTPBasic()


class Base(DeclarativeBase):
    pass


class MealRecord(Base):
    __tablename__ = "meal_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meal_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal: Mapped[str] = mapped_column(String(30), nullable=False)
    menu: Mapped[str] = mapped_column(String(200), nullable=False)
    students: Mapped[int] = mapped_column(Integer, nullable=False)
    meals_served: Mapped[int] = mapped_column(Integer, nullable=False)
    prepared_portions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    food_waste_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_demo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


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
    Base.metadata.create_all(engine)
    existing_columns = {
        column["name"] for column in inspect(engine).get_columns("meal_records")
    }
    additions = {
        "is_demo": "BOOLEAN NOT NULL DEFAULT TRUE",
        "prepared_portions": "INTEGER NULL",
        "food_waste_kg": "FLOAT NULL",
    }
    with engine.begin() as connection:
        for name, column_type in additions.items():
            if name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE meal_records ADD COLUMN {name} {column_type}"
                )


initialize_database()


class MealPredictionRequest(BaseModel):
    meal: str = Field(min_length=1, max_length=30)
    menu: str = Field(min_length=1, max_length=200)
    students: int = Field(gt=0, le=100_000)
    meal_date: date = Field(default_factory=date.today)


class MealPredictionResponse(BaseModel):
    meal: str
    menu: str
    students: int
    students_expected: int | None
    attendance_rate: float | None
    records_used: int
    attendance_method: str | None = None
    attendance_validation_mae_rate: float | None = None
    estimated_food_waste_kg: float | None = None
    waste_records_used: int = 0
    waste_method: str | None = None
    waste_validation_mae_kg_per_1000: float | None = None
    is_sample: bool = False
    message: str


class DemoPredictionRequest(BaseModel):
    day: str = Field(min_length=1, max_length=12)
    meal: str = Field(min_length=1, max_length=30)
    students: int = Field(gt=0, le=10_000)


class DemoWeeklyReportRequest(BaseModel):
    students: int = Field(gt=0, le=10_000)


class MealRecordFields(BaseModel):
    meal_date: date
    meal: str = Field(min_length=1, max_length=30)
    menu: str = Field(min_length=1, max_length=200)
    students: int = Field(gt=0, le=100_000)
    meals_served: int = Field(ge=0, le=100_000)
    prepared_portions: int | None = Field(default=None, ge=0, le=100_000)
    food_waste_kg: float | None = Field(default=None, ge=0, le=100_000)


class MealRecordRequest(MealRecordFields):
    is_demo: bool = False


class MealRecordUpdate(MealRecordFields):
    pass


class MealRecordResponse(MealRecordRequest):
    id: int


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "MessMind API is running"}


@app.get("/demo/menu-plan")
def demo_menu_plan():
    """Return the source menu and the assumptions behind the simulation."""
    return {
        "source_title": MENU_PLAN["source_title"],
        "source_period": MENU_PLAN["source_period"],
        "meals": MENU_PLAN["meals"],
        "meal_times": MENU_PLAN["meal_times"],
        "days": MENU_PLAN["days"],
        "assumptions": MENU_PLAN["assumptions"],
        "model_name": MODEL_NAME,
        "dataset_rows": len(DATASET_ROWS),
        "training_rows": len(TRAINING_ROWS),
        "synthetic_holdout_rows": HOLDOUT["holdout_rows"],
        "synthetic_attendance_mae_percent": round(
            HOLDOUT["attendance_mae_rate"] * 100, 2
        ),
        "synthetic_waste_mae_kg_per_1000": round(
            HOLDOUT["waste_mae_kg_per_1000"], 2
        ),
        "simulation_only": True,
    }


@app.post("/demo/predict")
def predict_demo_meal(request: DemoPredictionRequest):
    if request.day not in MENU_PLAN["days"]:
        raise HTTPException(status_code=422, detail="Choose a day from the menu plan.")
    if request.meal not in MENU_PLAN["meals"]:
        raise HTTPException(status_code=422, detail="Choose a meal from the menu plan.")
    menu = MENU_PLAN["days"][request.day].get(request.meal)
    if not menu:
        raise HTTPException(
            status_code=422,
            detail="The provided menu plan has no Sunday lunch, so it cannot be simulated.",
        )
    return predict_demo(request.day, request.meal, menu, request.students)


@app.get("/model/readiness")
def model_readiness(_staff: str = Depends(require_staff)):
    """Show real-data sample counts without exposing meal records."""
    with Session(engine) as session:
        attendance_count = session.scalar(
            select(func.count(MealRecord.id)).where(MealRecord.is_demo.is_(False))
        ) or 0
        waste_count = session.scalar(
            select(func.count(MealRecord.id)).where(
                MealRecord.is_demo.is_(False), MealRecord.food_waste_kg.is_not(None)
            )
        ) or 0
    return {
        "real_attendance_records": attendance_count,
        "measured_waste_records": waste_count,
        "minimum_meal_history_for_average": MIN_MEAL_HISTORY_ROWS,
        "minimum_records_for_validated_model": MIN_REAL_MODEL_ROWS,
        "model_history_limit": MAX_MODEL_HISTORY_ROWS,
        "attendance_model_ready": attendance_count >= MIN_REAL_MODEL_ROWS,
        "waste_model_ready": waste_count >= MIN_REAL_MODEL_ROWS,
        "simulation_rows_are_excluded": True,
        "message": (
            "Only staff-entered non-demo records count. Leave measurements blank when they were not taken; "
            "a blank waste value is never treated as zero."
        ),
    }


@app.post("/demo/weekly-report")
def demo_weekly_report(request: DemoWeeklyReportRequest):
    """Summarize a simulated week without saving generated rows as real records."""
    daily_rows = []
    meal_rows = []
    for day, day_menu in MENU_PLAN["days"].items():
        day_servings = 0
        day_waste = 0.0
        for meal in MENU_PLAN["meals"]:
            menu = day_menu.get(meal)
            if not menu:
                continue
            result = predict_demo(day, meal, menu, request.students)
            day_servings += result["expected_students"]
            day_waste += result["estimated_food_waste_kg"]
            meal_rows.append(
                {
                    "day": day,
                    "meal": meal,
                    "expected_students": result["expected_students"],
                    "estimated_food_waste_kg": result["estimated_food_waste_kg"],
                }
            )
        daily_rows.append(
            {
                "day": day,
                "estimated_meal_servings": day_servings,
                "estimated_food_waste_kg": round(day_waste, 1),
            }
        )

    highest_waste = max(meal_rows, key=lambda row: row["estimated_food_waste_kg"])
    return {
        "students_eligible_per_meal": request.students,
        "days": daily_rows,
        "meal_slots": meal_rows,
        "estimated_weekly_meal_servings": sum(
            row["estimated_meal_servings"] for row in daily_rows
        ),
        "estimated_weekly_food_waste_kg": round(
            sum(row["estimated_food_waste_kg"] for row in daily_rows), 1
        ),
        "highest_waste_slot": highest_waste,
        "is_simulation": True,
        "message": (
            "Simulation only. Meal servings count each meal visit and are not unique students. "
            "No report values are saved as real mess records."
        ),
    }


@app.get("/admin", include_in_schema=False)
def staff_admin_page(_staff: str = Depends(require_staff)):
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.post("/predict", response_model=MealPredictionResponse)
def predict_attendance(request: MealPredictionRequest):
    # Demo records are never part of the real-history prediction path.
    with Session(engine) as session:
        history = session.execute(
            select(
                MealRecord.id,
                MealRecord.meal_date,
                MealRecord.meal,
                MealRecord.menu,
                MealRecord.students,
                MealRecord.meals_served,
                MealRecord.food_waste_kg,
            )
            .where(MealRecord.is_demo.is_(False))
            .order_by(MealRecord.meal_date.desc(), MealRecord.id.desc())
            .limit(MAX_MODEL_HISTORY_ROWS)
        ).all()

    real_rows = [dict(row._mapping) for row in reversed(history)]
    prediction = predict_from_real_records(
        real_rows, request.meal, request.menu, request.meal_date, request.students
    )
    if prediction["attendance_rate"] is None:
        return MealPredictionResponse(
            meal=request.meal,
            menu=request.menu,
            students=request.students,
            students_expected=None,
            attendance_rate=None,
            records_used=prediction["attendance_records_used"],
            estimated_food_waste_kg=prediction["food_waste_kg"],
            waste_records_used=prediction["waste_records_used"],
            waste_method=prediction["waste_method"],
            message=(
                f"Need at least {MIN_MEAL_HISTORY_ROWS} non-demo records for this meal before showing an attendance average. "
                f"There are {prediction['attendance_records_used']} so far. Only enter approved totals."
            ),
        )

    attendance_rate = prediction["attendance_rate"]
    attendance_method = prediction["attendance_method"]
    validation_note = ""
    if prediction["attendance_validation_mae_rate"] is not None:
        validation_note = (
            f" Chronological holdout MAE: "
            f"{prediction['attendance_validation_mae_rate'] * 100:.1f} percentage points."
        )
    waste_detail = (
        f" Estimated measured waste: {prediction['food_waste_kg']:.1f} kg "
        f"from {prediction['waste_records_used']} measured records."
        if prediction["food_waste_kg"] is not None
        else " Add measured total waste consistently to start a waste estimate."
    )
    return MealPredictionResponse(
        meal=request.meal,
        menu=request.menu,
        students=request.students,
        students_expected=round(request.students * attendance_rate),
        attendance_rate=attendance_rate,
        records_used=prediction["attendance_records_used"],
        attendance_method=attendance_method,
        attendance_validation_mae_rate=prediction["attendance_validation_mae_rate"],
        estimated_food_waste_kg=prediction["food_waste_kg"],
        waste_records_used=prediction["waste_records_used"],
        waste_method=prediction["waste_method"],
        waste_validation_mae_kg_per_1000=prediction["waste_validation_mae_kg_per_1000"],
        message=(
            f"{attendance_method.capitalize()} using {prediction['attendance_records_used']} non-demo records for "
            f"{request.meal.lower()}. The selected meal date and menu enter the trend model only when it beats "
            f"a same-meal average on a chronological holdout.{validation_note}{waste_detail} "
            "Treat this as a pilot estimate and compare it with kitchen results."
        ),
    )


@app.post("/records", response_model=MealRecordResponse, status_code=201)
def create_meal_record(
    record: MealRecordRequest, _staff: str = Depends(require_staff)
):
    if IS_VERCEL_DEPLOYMENT and not ALLOW_REAL_RECORDS and not record.is_demo:
        raise HTTPException(
            status_code=503,
            detail=(
                "Real attendance entry is disabled until permanent storage is "
                "connected and verified-record collection is explicitly enabled."
            ),
        )
    if record.meals_served > record.students:
        raise HTTPException(
            status_code=400,
            detail="Meals served cannot be greater than students eligible.",
        )
    if record.prepared_portions is not None and record.prepared_portions < record.meals_served:
        raise HTTPException(
            status_code=400,
            detail="Prepared portions cannot be fewer than meals served. Leave it blank if it was not measured.",
        )

    with Session(engine) as session:
        duplicate = session.scalar(
            select(MealRecord.id)
            .where(
                MealRecord.meal_date == record.meal_date,
                func.lower(MealRecord.meal) == record.meal.lower(),
                MealRecord.is_demo.is_(record.is_demo),
            )
            .limit(1)
        )
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

        saved_record = MealRecord(
            **record.model_dump(),
            created_at=datetime.now(timezone.utc),
        )
        session.add(saved_record)
        session.commit()
        session.refresh(saved_record)
        record_id = saved_record.id

    return MealRecordResponse(id=record_id, **record.model_dump())


@app.put("/records/{record_id}", response_model=MealRecordResponse)
def update_meal_record(
    record_id: int, record: MealRecordUpdate, _staff: str = Depends(require_staff)
):
    if record.meals_served > record.students:
        raise HTTPException(
            status_code=400,
            detail="Meals served cannot be greater than students eligible.",
        )
    if record.prepared_portions is not None and record.prepared_portions < record.meals_served:
        raise HTTPException(
            status_code=400,
            detail="Prepared portions cannot be fewer than meals served. Leave it blank if it was not measured.",
        )

    with Session(engine) as session:
        existing = session.get(MealRecord, record_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Meal record not found.")

        is_demo = existing.is_demo
        if IS_VERCEL_DEPLOYMENT and not ALLOW_REAL_RECORDS and not is_demo:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Real attendance editing is disabled until permanent storage "
                    "is connected and verified-record collection is explicitly enabled."
                ),
            )
        duplicate = session.scalar(
            select(MealRecord.id)
            .where(
                MealRecord.meal_date == record.meal_date,
                func.lower(MealRecord.meal) == record.meal.lower(),
                MealRecord.is_demo.is_(is_demo),
                MealRecord.id != record_id,
            )
            .limit(1)
        )
        if duplicate:
            record_type = "demo" if is_demo else "real"
            raise HTTPException(
                status_code=409,
                detail=(
                    f"A {record_type} {record.meal.lower()} record already exists "
                    f"for {record.meal_date.isoformat()}. Each date and meal can "
                    "only be entered once."
                ),
            )

        existing.meal_date = record.meal_date
        existing.meal = record.meal
        existing.menu = record.menu
        existing.students = record.students
        existing.meals_served = record.meals_served
        existing.prepared_portions = record.prepared_portions
        existing.food_waste_kg = record.food_waste_kg
        session.commit()

    return MealRecordResponse(
        id=record_id, is_demo=bool(is_demo), **record.model_dump()
    )


@app.get("/records", response_model=list[MealRecordResponse])
def list_meal_records(_staff: str = Depends(require_staff)):
    with Session(engine) as session:
        records = session.scalars(
            select(MealRecord).order_by(
                MealRecord.meal_date.desc(), MealRecord.id.desc()
            )
        ).all()

    return [
        {
            "id": record.id,
            "meal_date": record.meal_date,
            "meal": record.meal,
            "menu": record.menu,
            "students": record.students,
            "meals_served": record.meals_served,
            "prepared_portions": record.prepared_portions,
            "food_waste_kg": record.food_waste_kg,
            "is_demo": record.is_demo,
        }
        for record in records
    ]


@app.delete("/records/{record_id}", status_code=204)
def delete_demo_meal_record(
    record_id: int, _staff: str = Depends(require_staff)
):
    with Session(engine) as session:
        record = session.get(MealRecord, record_id)
        if record is None or not record.is_demo:
            raise HTTPException(
                status_code=404,
                detail="Demo record not found. Real records cannot be removed here.",
            )
        session.delete(record)
        session.commit()
    return Response(status_code=204)


@app.get("/records/export.csv", include_in_schema=False)
def export_real_meal_records(_staff: str = Depends(require_staff)):
    """Download only aggregate non-demo records for backup or later analysis."""
    with Session(engine) as session:
        records = session.scalars(
            select(MealRecord)
            .where(MealRecord.is_demo.is_(False))
            .order_by(MealRecord.meal_date, MealRecord.id)
        ).all()

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        ["meal_date", "meal", "menu", "students", "meals_served", "prepared_portions", "food_waste_kg"]
    )
    for record in records:
        writer.writerow(
            [
                record.meal_date.isoformat(),
                record.meal,
                record.menu,
                record.students,
                record.meals_served,
                record.prepared_portions if record.prepared_portions is not None else "",
                record.food_waste_kg if record.food_waste_kg is not None else "",
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=messmind-real-records.csv"},
    )


# Serve the student page from this same local server so it can call the API.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
