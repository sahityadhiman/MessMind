# MessMind

**Plan the right amount. Waste less.**

MessMind is a meal-planning prototype for hostel mess kitchens. Staff can record aggregate meal totals, and the app can use that history to estimate attendance and measured food waste. A separate demo mode lets people explore the idea with generated examples based on the supplied menu plan.

> **Important:** Demo results are simulations, not college measurements or validated kitchen recommendations. Real estimates use only staff-entered, non-demo records. Student accounts store an email address for sign-in, but do not verify college identity. Do not enter student names, IDs, room numbers, or other personal details.

[Open the live MessMind app](https://messmind-delta.vercel.app/) · [OpenAPI docs](https://messmind-delta.vercel.app/docs) · [Health check](https://messmind-delta.vercel.app/health)

## What you can do

- Choose **Real estimate** to estimate attendance from approved staff records, or **Demo simulation** to explore generated results.
- Explore a weekday, meal, and menu from the supplied menu plan, including suggested portions and illustrative waste.
- View a simulated seven-day report.
- Use the staff page to add and correct aggregate meal records, check data readiness, and export non-demo records as CSV.
- Create a student account with an email address and password to use Demo Simulation. Email addresses are not checked against a college.
- Switch between light and dark themes. The home page also includes the interactive sketchbook background.

## Try the live demo

1. Open the [MessMind app](https://messmind-delta.vercel.app/).
2. Choose **Student**, create an account or sign in, then submit a complete yes/no meal plan for a date.
3. Select the date and meal, set the eligible student count, and choose **Run simulated prediction**. Aggregate student plans are the primary attendance signal for that date and meal; the generated model supplies the remaining share.
4. Choose **View 7-day demo report** to see a simulated outlook for the supplied menu plan.

The demo starts with 1,000 eligible students per meal as an editable example. For a date and meal with submitted student plans, those unverified intentions account for 70–80% of its simulated attendance forecast; the generated model supplies the rest. A seven-day report requires student plan responses for every scheduled meal on every date in the report; it does not silently fill missing dates with the generated baseline. Portion and waste values remain synthetic assumptions. The report counts meal visits across the week; it does not count unique students.

Student accounts store an email address and a salted password hash. Passwords are not stored in plain text. Email addresses are not verified, so an account does not prove that someone attends a particular college. Student plans are stored separately under a date-specific participant hash; other students see combined totals, not individual choices. Use a password unique to MessMind. Sign-in sessions expire after 14 days or when the student signs out.

The **Real estimate** mode may say that there is not enough history yet. That is expected: it does not fill gaps with demo values.

## How predictions work

MessMind keeps generated examples separate from staff-entered records. Switching modes changes which workflow the app uses; running a simulation never creates a real meal record.

| Mode | Data used | What it returns |
| --- | --- | --- |
| **Real estimate** | Saved records marked non-demo | Estimated attendance from that meal's history; an optional waste estimate only when measured-waste history is available |
| **Demo simulation** | Reproducible synthetic examples generated from the supplied menu plan | Simulated attendance, an illustrative range, suggested portions, and assumed food waste |

### Real estimates

- Records marked **DEMO** are always excluded from real attendance and waste estimates.
- With at least **3 non-demo records for the selected meal**, MessMind can calculate a student-weighted average for that meal. If fewer than 3 exist, the app reports that there is not enough history.
- With at least **35 eligible real records**, the API also evaluates a small ridge-regression model using a chronological holdout. It uses the model only when it beats the simpler historical baseline; otherwise it keeps the average. The model considers meal, weekday, menu variety, and a small menu-keyword feature.
- The attendance model can use up to the latest **500 non-demo records**. The waste model follows the same approach but only uses rows with an actual waste measurement; blank measurements are not zeroes.
- Attendance and waste are evaluated separately. Waste can therefore remain unavailable even when an attendance estimate is ready.
- The code fits and checks models from the current records when a prediction is requested. There is no separate manual training command or background training job for real records; newly saved records can be considered by the next prediction.

These thresholds and checks make the prototype cautious about limited history. They do not guarantee that a prediction is accurate for a particular kitchen.

### Demo simulation

The supplied workbook contains menu names, not measured attendance or waste. For demonstration, `ml/generate_demo_data.py` repeats the menu scenarios across eight simulated weeks and creates synthetic training examples. The generator is seeded so the examples can be reproduced.

- The simulation dataset contains **216 generated examples**: **189** are used to fit the demo model and **27** from the final simulated week are held out for an illustrative check.
- A signed-in student must submit their yes/no intentions for a date before running that date's demo simulation or report.
- Aggregate student plans are the primary attendance signal for matching date-and-meal predictions; their influence grows from 70% toward 80% as more responses are submitted.
- The default eligible group is 1,000 students, but the demo form lets you change it.
- Suggested portions add an 8% reserve to simulated expected attendance.
- Synthetic waste assumes cooked portions of 0.38 kg for breakfast, 0.60 kg for lunch, 0.18 kg for snacks, and 0.55 kg for dinner, plus a generated preparation reserve and plate leftovers.
- The displayed range and error metrics come from generated holdout examples. They are **not** a confidence interval and do **not** measure real-world accuracy.
- Sunday lunch is blank in the source menu plan and is omitted from simulations and reports.

The generated CSV is included at [`ml/data/demo_training_data.csv`](ml/data/demo_training_data.csv). Recreate it from the repository root with:

```bash
python -m ml.generate_demo_data
```

The Python demo model uses the same generator to build and check its examples; the CSV is provided so the synthetic dataset can also be inspected.

## Student accounts, staff records, and data handling

Student sign-up and sign-in use the `/auth/student/*` routes. A successful sign-in sets an HTTP-only session cookie. On Vercel, student accounts require the persistent PostgreSQL database configured by `DATABASE_URL`; account creation is refused when only temporary `/tmp` storage is available. No email verification, password reset, or college identity check is implemented yet.

Open `/admin` on the live app or at `http://127.0.0.1:8000/admin` when running locally. Staff access uses HTTP Basic authentication. Set a private username and password in the environment before using the page.

Each record contains an aggregate meal date, meal, menu, number of eligible students, and number of meals served. Prepared portions and total discarded food in kilograms are optional. Enter waste only when it was measured consistently; leave it blank otherwise. Do not enter names, student IDs, room numbers, or individual attendance details.

- Mark examples as **demo data**. Demo records stay visible to staff but never affect real estimates.
- A record's demo/real type cannot be changed while editing it.
- The app prevents duplicate records for the same date, meal, and record type.
- Staff can edit saved records. The delete endpoint only removes demo records; real records are not deleted through that endpoint.
- **Download real CSV** exports aggregate non-demo records only. Store exported files carefully and share them only with approved people.
- Use HTTPS whenever staff pages are reachable over a network. Basic authentication credentials are not protected when sent over plain HTTP.

### Storage and production safety

Local development uses SQLite at `backend/messmind.db` by default. For hosted use, configure persistent PostgreSQL storage through a private `DATABASE_URL` (Neon is supported). SQLite files on Vercel's temporary filesystem do not provide durable record storage.

On Vercel, adding or editing non-demo records is enabled only when both a persistent database URL is present and `MESSMIND_ENABLE_REAL_RECORDS=true` is set. Keep those settings in the hosting provider's private environment variables, never in frontend code or a committed `.env` file. Enable real collection only after the college or mess has approved it and persistent storage has been checked.

## Run locally

Requirements: **Python 3.12 or newer**.

### Windows PowerShell

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

In `backend/.env`, set a private `MESSMIND_ADMIN_PASSWORD`. The default local username is `mess-manager`; you can change it with `MESSMIND_ADMIN_USERNAME`. Leave `DATABASE_URL` empty to use local SQLite. Then start the app from the repository root:

```powershell
py -m uvicorn main:app --app-dir backend --reload
```

### macOS or Linux

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set a private `MESSMIND_ADMIN_PASSWORD`, then run:

```bash
python -m uvicorn main:app --app-dir backend --reload
```

The local `.env` file is ignored by Git. Never replace it with a real credential in `.env.example` or commit it.

| Local URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8000/` | Student-facing planner and demo |
| `http://127.0.0.1:8000/admin` | Staff records (browser sign-in required) |
| `http://127.0.0.1:8000/docs` | Interactive FastAPI documentation |
| `http://127.0.0.1:8000/health` | API health check |

## API overview

Interactive request/response schemas are available at `/docs`.

| Method | Route | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | Public | API health check |
| `GET` | `/demo/menu-plan` | Public | Supplied menus and simulation assumptions |
| `POST` | `/auth/student/signup` | Public | Create a student account and start a session |
| `POST` | `/auth/student/login` | Public | Sign in and start a session |
| `GET` | `/auth/student/session` | Public | Check whether the browser has an active student session |
| `POST` | `/auth/student/logout` | Public | End the browser's student session |
| `GET` | `/demo/student-plans` | Student | Read combined counts and the signed-in student's saved plan |
| `POST` | `/demo/student-plans` | Student | Save or update the signed-in student's demo meal plan |
| `POST` | `/demo/predict` | Student | Simulate one day and meal; does not save a record |
| `POST` | `/demo/weekly-report` | Student | Generate a seven-day simulation report only when every scheduled date and meal has a student plan; does not save records |
| `POST` | `/predict` | Public | Estimate attendance and, when available, measured waste from non-demo history |
| `GET` | `/model/readiness` | Staff | Aggregate real-record counts and model thresholds |
| `GET` | `/records` | Staff | List saved aggregate records |
| `POST` | `/records` | Staff | Add a real or demo aggregate record |
| `PUT` | `/records/{id}` | Staff | Correct a record without changing its type |
| `DELETE` | `/records/{id}` | Staff | Delete a demo record only |
| `GET` | `/records/export.csv` | Staff | Download non-demo aggregate records as CSV |

Staff routes use the configured HTTP Basic credentials. The browser may show a username/password prompt when opening `/admin` or a staff-only route.

## Deploy on Vercel

This repository is configured for the Python FastAPI app through the Vercel entry point in `pyproject.toml`. The live deployment uses Neon PostgreSQL for persistent hosted storage.

Configure these as private Vercel project environment variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Private PostgreSQL connection string; Vercel's Neon integration can provide it |
| `MESSMIND_ADMIN_USERNAME` | Staff sign-in username |
| `MESSMIND_ADMIN_PASSWORD` | Staff sign-in password |
| `MESSMIND_ENABLE_REAL_RECORDS` | Set to `true` only after persistent storage is connected and real-data collection is approved |

Redeploy after changing deployment environment variables. Never put these values in the README, frontend JavaScript, screenshots, or Git history.

## Technology

- **Frontend:** HTML, CSS, and browser JavaScript
- **API:** Python, FastAPI, Uvicorn, and SQLAlchemy
- **Storage:** SQLite locally; PostgreSQL for persistent hosted storage
- **Prediction:** Small in-project ridge-regression implementation; no external AI service or API key is required
- **Deployment:** Vercel, with Neon PostgreSQL available for persistent records
- **Visual interaction:** Local Sketchbook DOM/CSS 3D component and authored local assets

## Repository layout

```text
MessMind/
├── backend/
│   ├── main.py                 # FastAPI routes, storage, validation, and authentication
│   ├── .env.example            # Safe template for local settings
│   └── README.md               # Additional API and backend notes
├── frontend/
│   ├── index.html              # Student planner, mode switch, and demo UI
│   ├── app.js                  # Theme, real-estimate, and mode behavior
│   ├── demo.js                 # Demo simulation and weekly report UI
│   ├── admin.html              # Staff record interface
│   ├── admin.js                # Record management and readiness display
│   ├── styles.css              # Responsive light/dark interface
│   ├── effects/sketchbook/     # Sketchbook renderer and host styles
│   └── sketchbook/             # Local artwork and font assets
├── ml/
│   ├── menu_plan.py            # Menu transcribed from the supplied workbook
│   ├── generate_demo_data.py   # Reproducible synthetic examples
│   ├── demo_model.py           # Simulation model and synthetic holdout check
│   ├── real_model.py           # Real-record estimators and model validation
│   └── data/demo_training_data.csv
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Limitations and next steps

- The source menu workbook does not provide attendance or measured waste. Demo outputs are generated examples, not observations from the college.
- Synthetic holdout metrics test the demo model against its own generated rules; they do not establish real-world accuracy.
- Real estimates become useful only after enough approved, consistently entered records exist. Waste estimates additionally require actual waste measurements.
- The real model uses simple menu and weekday features and falls back to a same-meal average when the more complex model does not validate better. Compare estimates with observed kitchen results before relying on them for preparation decisions.
- The app does not collect student names, IDs, or room numbers. Student account emails are stored for sign-in, while meal plans are stored under a date-specific participant hash and exposed to predictions as combined totals.

## Author

Built by [@sahityadhiman](https://github.com/sahityadhiman).

## Admin page

[Open the live staff admin page](https://messmind-delta.vercel.app/admin) (staff login required).
