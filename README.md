# 🍽️ MessMind

### Smarter Meal Planning for Hostel Mess Kitchens

MessMind helps hostel mess staff plan meals by estimating student attendance from past meal records, with a demo mode for exploring portions and food-waste estimates. The goal is to help kitchens make better preparation decisions and reduce food waste.

---

## 🌐 Live Demo

🚀 **Try MessMind online:**

https://messmind-delta.vercel.app/

---

## 💡 Problem Statement

Mess kitchens often struggle with:

* Not knowing how many students will actually show up for a meal
* Over- or under-preparing food, leading to waste or shortages
* No easy way to record and reuse past attendance data
* No simple tool to test "what if" scenarios before committing to a menu plan

This leads to inconsistent portioning, avoidable food waste, and guesswork in daily kitchen planning.

---

## 🎯 Solution

MessMind gives mess staff two ways to plan:

* **Historical estimates** — grounded in real, recorded attendance for that meal
* **Simulated planning** — a demo mode to explore portions and waste for a given day, meal, and student count

Staff can record real meal data over time, and the app uses that history to produce more informed estimates — while keeping demo/simulated data clearly separate from real records.

---

## ⚙️ How It Works

1. Mess staff sign in and enter an aggregate record: date, meal, menu, eligible students, and meals served.
2. For a historical estimate, the student-facing page sends the selected meal and student count to the API.
3. The API uses up to 30 recent real records for that meal to calculate an attendance rate and estimate attendance. Demo records are ignored; if no real records exist, the app reports that a historical estimate isn't available.
4. For a simulation, the user picks a day and meal from the supplied menu plan. The model returns simulated attendance, suggested portions, and estimated food waste.
5. A seven-day demo report runs that simulation across the whole menu plan. Simulation results are never saved as real meal records.

---

## ✨ Features

* 📈 **Historical attendance estimate** — estimates attendance for a meal from up to 30 recent real records for that same meal
* 🧪 **Menu simulation** — choose a day, meal, and student count to see a simulated attendance estimate, suggested portions, and estimated waste
* 📊 **Seven-day demo report** — summarizes simulated servings and waste across the menu plan
* 🔐 **Staff record page** — password-protected page for adding and correcting aggregate meal records; demo records are kept separate from real records
* 🎨 **Interface options** — responsive layout with light/dark theme

---

## ⚠️ A Note on the Simulation Model

The simulation model uses generated examples, not measured mess data. Its attendance and waste estimates are **demonstrations, not validated kitchen recommendations**. The historical estimator uses real records when available, but currently considers the meal only — not the menu or weekday.

---

## 🛠️ Tech Stack

### Frontend

* HTML
* CSS
* JavaScript

### Backend / API

* Python
* FastAPI
* Uvicorn

### Database

* SQLite (local)
* PostgreSQL supported via `DATABASE_URL`

### Prediction Model

* A small Python ridge-regression model

### External AI Services

* None — the simulation model runs entirely within the app

### Deployment

* Prepared for Vercel
* Neon PostgreSQL as an option for persistent hosted storage

---

## 💻 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/sahityadhiman/MessMind.git
```

### 2. Navigate to the project folder

```bash
cd MessMind
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
uvicorn main:app --reload
```

### 5. Open in your browser

```text
http://127.0.0.1:8000
```

*(Adjust the module/app name and port above if your entry point differs.)*

---

## 📂 Project Structure

```text
MessMind/
│
├── frontend/             # The browser interface
├── backend/               # The API that connects the interface to the data and prediction logic
├── ml/                     # Attendance prediction work
├── .gitignore
├── README.md
├── pyproject.toml
└── requirements.txt       # Python dependencies
```

---

## 🎯 Future Improvements

* Train and validate predictions on approved real attendance data
* Factor menu and weekday into historical estimates, not just the meal
* Measure actual leftovers and waste to compare against estimates
* Connect persistent hosted storage (e.g. Neon PostgreSQL) before using a hosted version for real records

---

## 👨‍💻 Author

**@sahityadhiman**

*(No contributor list was found in the project files — add your preferred display name and any teammates who worked on this version.)*

---

## ⭐ Support

If you like this project, consider giving the repository a ⭐ on GitHub!

---

### 🍽️ MessMind

**Plan smarter. Waste less.**
