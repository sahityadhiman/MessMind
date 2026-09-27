from pathlib import Path
import csv
import base64
import hashlib
import hmac
import io
import math
import os
import re
import secrets
import sys
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    case,
    create_engine,
    delete,
    inspect,
    select,
    func,
    text,
)
from sqlalchemy.exc import IntegrityError
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
STUDENT_SESSION_COOKIE = "messmind_student_session"
STUDENT_SESSION_TTL_SECONDS = 14 * 24 * 60 * 60
STUDENT_PASSWORD_ITERATIONS = 600_000


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


class DemoStudentPlan(Base):
    """Demo-only meal intentions keyed by a per-account participant hash."""

    __tablename__ = "demo_student_plans"
    __table_args__ = (
        UniqueConstraint(
            "meal_date", "meal", "participant_hash",
            name="uq_demo_student_plan_date_meal_participant",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal: Mapped[str] = mapped_column(String(30), nullable=False)
    participant_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    will_attend: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class StudentAccount(Base):
    __tablename__ = "student_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class StudentWebSession(Base):
    __tablename__ = "student_web_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("student_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)


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
    meal_date: date


class DemoStudentPlanRequest(BaseModel):
    meal_date: date
    meals: dict[str, bool]


class StudentAuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def ensure_student_account_storage():
    if IS_VERCEL_DEPLOYMENT and not DATABASE_URL:
        raise HTTPException(
            status_code=503,
            detail="Student accounts need persistent PostgreSQL storage. Configure DATABASE_URL before enabling sign-up.",
        )


def normalize_student_email(email: str) -> str:
    normalized = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return normalized


def hash_student_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, STUDENT_PASSWORD_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        STUDENT_PASSWORD_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_student_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_digest = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256" or int(iterations) != STUDENT_PASSWORD_ITERATIONS:
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, STUDENT_PASSWORD_ITERATIONS
        )
        return hmac.compare_digest(actual_digest, expected_digest)
    except (ValueError, TypeError):
        return False


def student_session_cookie_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def issue_student_session(session: Session, student_id: str) -> str:
    now = int(time.time())
    session.execute(delete(StudentWebSession).where(StudentWebSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    session.add(
        StudentWebSession(
            token_hash=student_session_cookie_hash(token),
            student_id=student_id,
            expires_at=now + STUDENT_SESSION_TTL_SECONDS,
        )
    )
    return token


def set_student_session_cookie(response: Response, token: str):
    response.set_cookie(
        STUDENT_SESSION_COOKIE,
        token,
        max_age=STUDENT_SESSION_TTL_SECONDS,
        httponly=True,
        secure=IS_VERCEL_DEPLOYMENT,
        samesite="lax",
        path="/",
    )


def current_student(request: Request):
    token = request.cookies.get(STUDENT_SESSION_COOKIE, "")
    if not token or len(token) > 100:
        return None
    now = int(time.time())
    with Session(engine) as session:
        saved_session = session.get(
            StudentWebSession, student_session_cookie_hash(token)
        )
        if saved_session is None or saved_session.expires_at <= now:
            if saved_session is not None:
                session.delete(saved_session)
                session.commit()
            return None
        account = session.get(StudentAccount, saved_session.student_id)
        if account is None:
            session.delete(saved_session)
            session.commit()
            return None
        return {"id": account.id, "email": account.email}


def require_student(request: Request):
    student = current_student(request)
    if student is None:
        raise HTTPException(status_code=401, detail="Sign in to use student demo features.")
    return student


def require_same_origin(request: Request):
    origin = request.headers.get("origin")
    if not origin:
        return
    origin_host = urlsplit(origin).netloc.lower()
    request_host = request.headers.get("host", "").lower()
    if not origin_host or origin_host != request_host:
        raise HTTPException(status_code=403, detail="This request must come from MessMind.")


DUMMY_STUDENT_PASSWORD_HASH = None


def dummy_student_password_hash() -> str:
    global DUMMY_STUDENT_PASSWORD_HASH
    if DUMMY_STUDENT_PASSWORD_HASH is None:
        DUMMY_STUDENT_PASSWORD_HASH = hash_student_password(secrets.token_urlsafe(32))
    return DUMMY_STUDENT_PASSWORD_HASH


class DemoWeeklyReportRequest(BaseModel):
    students: int = Field(gt=0, le=10_000)
    start_date: date | None = None


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


@app.post("/auth/student/signup")
def student_signup(
    request: StudentAuthRequest,
    response: Response,
    _origin: None = Depends(require_same_origin),
):
    ensure_student_account_storage()
    if len(request.password) < 12:
        raise HTTPException(
            status_code=422, detail="Use a password with at least 12 characters."
        )
    email = normalize_student_email(request.email)
    try:
        with Session(engine) as session:
            account = StudentAccount(
                email=email, password_hash=hash_student_password(request.password)
            )
            session.add(account)
            session.flush()
            token = issue_student_session(session, account.id)
            session.commit()
            student_email = account.email
    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="That email may already have an account. Try signing in instead.",
        ) from error

    set_student_session_cookie(response, token)
    return {"authenticated": True, "email": student_email, "email_verified": False}


@app.post("/auth/student/login")
def student_login(
    request: StudentAuthRequest,
    response: Response,
    _origin: None = Depends(require_same_origin),
):
    ensure_student_account_storage()
    email = normalize_student_email(request.email)
    with Session(engine) as session:
        account = session.scalar(
            select(StudentAccount).where(StudentAccount.email == email)
        )
        password_hash = (
            account.password_hash if account is not None else dummy_student_password_hash()
        )
        password_matches = verify_student_password(request.password, password_hash)
        if account is None or not password_matches:
            raise HTTPException(status_code=401, detail="Email or password is incorrect.")
        token = issue_student_session(session, account.id)
        session.commit()
        student_email = account.email

    set_student_session_cookie(response, token)
    return {"authenticated": True, "email": student_email, "email_verified": False}


@app.get("/auth/student/session")
def student_session(request: Request):
    student = current_student(request)
    if student is None:
        return {"authenticated": False}
    return {"authenticated": True, "email": student["email"], "email_verified": False}


@app.post("/auth/student/logout", status_code=204)
def student_logout(
    request: Request,
    response: Response,
    _origin: None = Depends(require_same_origin),
):
    token = request.cookies.get(STUDENT_SESSION_COOKIE, "")
    if token and len(token) <= 100:
        with Session(engine) as session:
            saved_session = session.get(
                StudentWebSession, student_session_cookie_hash(token)
            )
            if saved_session is not None:
                session.delete(saved_session)
                session.commit()
    response.delete_cookie(
        STUDENT_SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=IS_VERCEL_DEPLOYMENT,
        samesite="lax",
    )
    return None


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


def validate_demo_plan_date(meal_date: date):
    today = date.today()
    if meal_date < today:
        raise HTTPException(status_code=422, detail="Student plans are only accepted for today or a future date.")
    if meal_date > today + timedelta(days=30):
        raise HTTPException(status_code=422, detail="Choose a date within the next 30 days.")


def get_demo_plan_counts(session: Session, meal_date: date, meal: str):
    yes_count, response_count = session.execute(
        select(
            func.coalesce(
                func.sum(case((DemoStudentPlan.will_attend.is_(True), 1), else_=0)),
                0,
            ),
            func.count(DemoStudentPlan.id),
        ).where(
            DemoStudentPlan.meal_date == meal_date,
            DemoStudentPlan.meal == meal,
        )
    ).one()
    return {"yes_count": int(yes_count), "response_count": int(response_count)}


def student_plan_participant_hash(student_id: str, meal_date: date) -> str:
    return hashlib.sha256(
        f"messmind-student-plan-v1:{student_id}:{meal_date.isoformat()}".encode("utf-8")
    ).hexdigest()


def student_plan_summary(
    session: Session, meal_date: date, participant_hash: str | None = None
):
    summary = {
        "meal_date": meal_date.isoformat(),
        "meals": {
            meal: get_demo_plan_counts(session, meal_date, meal)
            for meal in MENU_PLAN["meals"]
        },
        "demo_only": True,
    }
    if participant_hash:
        own_rows = session.scalars(
            select(DemoStudentPlan).where(
                DemoStudentPlan.meal_date == meal_date,
                DemoStudentPlan.participant_hash == participant_hash,
            )
        ).all()
        if own_rows:
            summary["own_plan"] = {
                row.meal: row.will_attend for row in own_rows
            }
    return summary


def apply_demo_student_plan(prediction: dict, students: int, plan_counts: dict):
    """Blend aggregate demo intentions as the primary signal with a synthetic baseline."""
    response_count = plan_counts["response_count"]
    yes_count = plan_counts["yes_count"]
    influence = (
        min(0.80, 0.70 + 0.10 * response_count / (response_count + 20))
        if response_count
        else 0.0
    )
    if response_count:
        base_portions = prediction["suggested_portions"]
        plan_rate = yes_count / response_count
        blended_rate = (
            prediction["attendance_rate"] * (1 - influence)
            + plan_rate * influence
        )
        blended_rate = min(0.97, max(0.15, blended_rate))
        prediction["base_expected_students"] = prediction["expected_students"]
        prediction["attendance_rate"] = round(blended_rate, 4)
        prediction["expected_students"] = round(students * blended_rate)
        prediction["suggested_portions"] = min(
            students,
            prediction["expected_students"]
            + math.ceil(prediction["expected_students"] * 0.08),
        )
        prediction["estimated_food_waste_kg"] = round(
            prediction["estimated_food_waste_kg"]
            * prediction["suggested_portions"]
            / max(1, base_portions),
            1,
        )
        # Keep the interval wide when the aggregate is based on few unverified intentions.
        illustrative_margin = math.ceil(
            students
            * (
                (1 - influence) * HOLDOUT["attendance_mae_rate"]
                + 0.5 * influence / math.sqrt(response_count)
            )
        )
        prediction["expected_students_low"] = max(
            0, prediction["expected_students"] - illustrative_margin
        )
        prediction["expected_students_high"] = min(
            students, prediction["expected_students"] + illustrative_margin
        )
        prediction["message"] = (
            "Demo only: combined student plans are the primary attendance signal, with the generated "
            "baseline supplying the remainder. Plans are unverified intentions, not confirmed attendance. "
            "Suggested portions and illustrative waste scale with this forecast; waste is not measured kitchen data."
        )
    else:
        prediction["message"] = (
            "Demo only: no student plans were submitted for this date and meal, so attendance "
            "uses the generated baseline. Suggested portions and illustrative waste use synthetic assumptions."
        )
    prediction["student_plan_yes"] = yes_count
    prediction["student_plan_responses"] = response_count
    prediction["student_plan_influence"] = round(influence, 4)
    return prediction


@app.get("/demo/student-plans")
def read_demo_student_plans(
    meal_date: date, student: dict = Depends(require_student)
):
    """Return combined counts and only the signed-in student's saved choices."""
    validate_demo_plan_date(meal_date)
    with Session(engine) as session:
        participant_hash = student_plan_participant_hash(student["id"], meal_date)
        return student_plan_summary(session, meal_date, participant_hash)


@app.post("/demo/student-plans")
def save_demo_student_plans(
    request: DemoStudentPlanRequest,
    student: dict = Depends(require_student),
    _origin: None = Depends(require_same_origin),
):
    """Upsert an authenticated student's demo-only meal intentions."""
    validate_demo_plan_date(request.meal_date)
    valid_meals = set(MENU_PLAN["meals"])
    if set(request.meals) != valid_meals:
        raise HTTPException(
            status_code=422,
            detail="Choose yes or no for each meal: breakfast, lunch, snacks, and dinner.",
        )

    participant_hash = student_plan_participant_hash(student["id"], request.meal_date)
    with Session(engine) as session:
        session.execute(
            delete(DemoStudentPlan).where(
                DemoStudentPlan.meal_date < date.today() - timedelta(days=30)
            )
        )
        for meal, will_attend in request.meals.items():
            saved_plan = session.scalar(
                select(DemoStudentPlan).where(
                    DemoStudentPlan.meal_date == request.meal_date,
                    DemoStudentPlan.meal == meal,
                    DemoStudentPlan.participant_hash == participant_hash,
                )
            )
            if saved_plan is None:
                saved_plan = DemoStudentPlan(
                    meal_date=request.meal_date,
                    meal=meal,
                    participant_hash=participant_hash,
                    will_attend=will_attend,
                )
                session.add(saved_plan)
            else:
                saved_plan.will_attend = will_attend
                saved_plan.updated_at = datetime.now(timezone.utc)
        session.commit()
        return student_plan_summary(session, request.meal_date, participant_hash)


@app.post("/demo/predict")
def predict_demo_meal(
    request: DemoPredictionRequest,
    _student: dict = Depends(require_student),
    _origin: None = Depends(require_same_origin),
):
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
    prediction = predict_demo(request.day, request.meal, menu, request.students)
    validate_demo_plan_date(request.meal_date)
    actual_day = list(MENU_PLAN["days"])[request.meal_date.weekday()]
    if actual_day != request.day:
        raise HTTPException(
            status_code=422,
            detail="The selected weekday does not match the meal date.",
        )
    with Session(engine) as session:
        plan_counts = get_demo_plan_counts(session, request.meal_date, request.meal)
    if plan_counts["response_count"] == 0:
        raise HTTPException(
            status_code=422,
            detail="Submit a student meal plan for this date before running the demo prediction.",
        )

    prediction["meal_date"] = request.meal_date.isoformat()
    return apply_demo_student_plan(prediction, request.students, plan_counts)


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
def demo_weekly_report(
    request: DemoWeeklyReportRequest,
    _student: dict = Depends(require_student),
    _origin: None = Depends(require_same_origin),
):
    """Summarize a simulated week only when every scheduled slot has plan responses."""
    report_start = request.start_date or date.today()
    validate_demo_plan_date(report_start)
    report_end = report_start + timedelta(days=6)
    if report_end > date.today() + timedelta(days=30):
        raise HTTPException(
            status_code=422,
            detail="Choose a report start date so all seven days fall within the next 30 days.",
        )

    plan_counts_by_slot = {}
    missing_plan_slots = []
    with Session(engine) as session:
        for date_offset in range(7):
            meal_date = report_start + timedelta(days=date_offset)
            day = list(MENU_PLAN["days"])[meal_date.weekday()]
            day_menu = MENU_PLAN["days"][day]
            for meal in MENU_PLAN["meals"]:
                if not day_menu.get(meal):
                    continue
                plan_counts = get_demo_plan_counts(session, meal_date, meal)
                plan_counts_by_slot[(meal_date, meal)] = plan_counts
                if plan_counts["response_count"] == 0:
                    missing_plan_slots.append(f"{day} {meal} ({meal_date.isoformat()})")
    if missing_plan_slots:
        raise HTTPException(
            status_code=422,
            detail=(
                "Save student meal plans for every scheduled meal in the seven-day report before running it. "
                "Missing plans: " + "; ".join(missing_plan_slots)
            ),
        )
    daily_rows = []
    meal_rows = []
    adjusted_slots = 0
    total_plan_responses = 0
    for date_offset in range(7):
        meal_date = report_start + timedelta(days=date_offset)
        day = list(MENU_PLAN["days"])[meal_date.weekday()]
        day_menu = MENU_PLAN["days"][day]
        day_servings = 0
        day_waste = 0.0
        for meal in MENU_PLAN["meals"]:
            menu = day_menu.get(meal)
            if not menu:
                continue
            plan_counts = plan_counts_by_slot[(meal_date, meal)]
            result = apply_demo_student_plan(
                predict_demo(day, meal, menu, request.students),
                request.students,
                plan_counts,
            )
            adjusted_slots += bool(plan_counts["response_count"])
            total_plan_responses += plan_counts["response_count"]
            day_servings += result["expected_students"]
            day_waste += result["estimated_food_waste_kg"]
            meal_rows.append(
                {
                    "date": meal_date.isoformat(),
                    "day": day,
                    "meal": meal,
                    "expected_students": result["expected_students"],
                    "estimated_food_waste_kg": result["estimated_food_waste_kg"],
                    "student_plan_responses": plan_counts["response_count"],
                }
            )
        daily_rows.append(
            {
                "date": meal_date.isoformat(),
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
        "student_plan_adjusted_slots": adjusted_slots,
        "student_plan_responses": total_plan_responses,
        "is_simulation": True,
        "message": (
            "Demo simulation only. Student plans were required for every scheduled meal and drive "
            "70–80% of each attendance forecast; the generated baseline supplies the remainder. "
            "Plans are unverified intentions and waste is synthetic, not measured. Meal servings count "
            "visits, not unique students. No report values are saved as real mess records."
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
