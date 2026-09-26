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

MessMind gives mess staff two clearly separated ways to plan:

* **Real estimate** — grounded only in saved, non-demo attendance records
* **Demo simulation** — generated examples to explore attendance, portions, and waste for a selected meal

Staff can record aggregate meal data over time. The app keeps demo results separate so generated numbers are never presented as measured college data.

---

## ⚙️ How It Works

1. Mess staff sign in and enter an aggregate record: date, meal, menu, eligible students, meals served, and optional measured portions and food waste.
2. In **Real estimate** mode, the page sends the meal, menu, date, and eligible student count to the API.
3. The API ignores demo records. With at least three real records for that meal, it can use a weighted historical average. With 35 or more real records, it checks a ridge-regression model against a time-ordered holdout and uses it only if it beats that average. Otherwise, it keeps the simpler estimate or says there is not enough history.
4. A measured-waste estimate uses only records where waste was actually weighed. Blank waste entries are not treated as zero.
5. In **Demo simulation** mode, the model returns generated attendance, suggested portions, and estimated waste. The seven-day demo report summarizes the supplied menu plan. Simulation results are never saved as real meal records.

---

## ✨ Features

* 🔀 **Prediction mode switch** — choose between a real-history estimate and a clearly labeled demo simulation
* 📈 **Real-history attendance estimate** — starts with a same-meal average; a model is used only after a chronological check shows it performs better
* ⚖️ **Measured-waste estimate** — uses staff-entered waste measurements and keeps missing measurements blank
* 🧪 **Menu simulation** — choose a day, meal, and student count to see simulated attendance, suggested portions, and estimated waste
* 📊 **Seven-day demo report** — summarizes simulated servings and waste across the menu plan
* 🔐 **Staff record page** — password-protected page for adding and correcting aggregate records, checking model data readiness, and exporting real records as CSV
* 🎨 **Interface options** — responsive layout with light/dark theme

---

## ⚠️ A Note on the Simulation Model

The demo model uses generated examples based on the supplied menu plan, not measured mess data. Its estimates are **demonstrations, not validated kitchen recommendations**. The generated-data holdout check only shows how well the model fits its own simulation assumptions. Real-world accuracy still needs to be checked with college-approved meal records and consistently measured waste. The real-history model uses menu and weekday only when it outperforms the same-meal average on a chronological holdout.

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
* PostgreSQL via `DATABASE_URL` (Neon is configured for the hosted deployment)

### Prediction Model

* A small Python ridge-regression model

### External AI Services

* None — the simulation model runs entirely within the app

### Deployment

* Prepared for Vercel
* Neon PostgreSQL for persistent hosted storage

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

* Validate estimates with college-approved meal attendance records
* Add consistently measured leftovers and kitchen waste data to validate waste estimates
* Compare predictions with actual kitchen outcomes and adjust assumptions as needed

---

## 👨‍💻 Author

**@sahityadhiman**

---

## ⭐ Support

If you like this project, consider giving the repository a ⭐ on GitHub!

---

### 🍽️ MessMind

**Plan smarter. Waste less.**
