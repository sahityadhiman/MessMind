from pathlib import Path
import os
import secrets
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
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
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
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
    if engine.dialect.name == "sqlite":
        existing_columns = {
            column["name"] for column in inspect(engine).get_columns("meal_records")
        }
        if "is_demo" not in existing_columns:
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    "ALTER TABLE meal_records ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT 1"
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


class MealRecordFields(BaseModel):
    meal_date: date
    meal: str = Field(min_length=1, max_length=30)
    menu: str = Field(min_length=1, max_length=200)
    students: int = Field(gt=0, le=100_000)
    meals_served: int = Field(ge=0, le=100_000)


class MealRecordRequest(MealRecordFields):
    is_demo: bool = False


class MealRecordUpdate(MealRecordFields):
    pass


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
    with Session(engine) as session:
        history = session.execute(
            select(MealRecord.students, MealRecord.meals_served)
            .where(
                MealRecord.is_demo.is_(False),
                func.lower(MealRecord.meal) == request.meal.lower(),
            )
            .order_by(MealRecord.meal_date.desc(), MealRecord.id.desc())
            .limit(30)
        ).all()

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


# Serve the student page from this same local server so it can call the API.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
