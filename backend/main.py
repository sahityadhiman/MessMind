from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="MessMind API", version="0.1.0")


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


# Serve the webpage from this same local server so the browser can call the API.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
