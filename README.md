# MessMind

**Plan the right amount. Waste less.**

MessMind is a meal-planning prototype for hostel mess kitchens. Staff can record aggregate meal totals, and the app can use that history to estimate attendance and measured food waste. A separate demo mode lets people explore the idea with generated examples based on the supplied menu plan.

> **Important:** Demo results are simulations, not college measurements or validated kitchen recommendations. Real estimates use only staff-entered, non-demo records. Do not enter student names, IDs, room numbers, or other personal data.

[Open the live MessMind app](https://messmind-delta.vercel.app/) · [OpenAPI docs](https://messmind-delta.vercel.app/docs) · [Health check](https://messmind-delta.vercel.app/health)

## What you can do

- Choose **Real estimate** to estimate attendance from approved staff records, or **Demo simulation** to explore generated results.
- Explore a weekday, meal, and menu from the supplied menu plan, including suggested portions and illustrative waste.
- View a simulated seven-day report.
- Use the staff page to add and correct aggregate meal records, check data readiness, and export non-demo records as CSV.
- Switch between light and dark themes. The home page also includes the interactive sketchbook background.

## Try the live demo

1. Open the [MessMind app](https://messmind-delta.vercel.app/).
2. Choose **Demo simulation**.
3. Select a weekday and meal, adjust the eligible student count if you like, and choose **Run simulated prediction**.
4. Choose **View 7-day demo report** to see a simulated outlook for the supplied menu plan.

The demo starts with 1,000 eligible students per meal as an editable example. Its attendance, portion, and waste values are generated assumptions. The report counts meal visits across the week; it does not count unique students.

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

The supplied workbook contains menu names, not measured attendance or waste. For demonstration, **ml/generate_demo_data.py** repeats the menu scenarios across eight simulated weeks and creates synthetic training examples. The generator is seeded so the examples can be reproduced.

- The simulation dataset contains **216 generated examples**: **189** are used to fit the demo model and **27** from the final simulated week are held out for an illustrative check.
- The default eligible group is 1,000 students, but the demo form lets you change it.
- Suggested portions add an 8% reserve to simulated expected attendance.
- Synthetic waste assumes cooked portions of 0.38 kg for breakfast, 0.60 kg for lunch, 0.18 kg for snacks, and 0.55 kg for dinner, plus a generated preparation reserve and plate leftovers.
- The displayed range and error metrics come from generated holdout examples. They are **not** a confidence interval and do **not** measure real-world accuracy.
- Sunday lunch is blank in the source menu plan and is omitted from simulations and reports.

The generated CSV is included at [ml/data/demo_training_data.csv](ml/data/demo_training_data.csv). Recreate it from the repository root with:

~~~bash
python -m ml.generate_demo_data
~~~

The Python demo model uses the same generator to build and check its examples; the CSV is provided so the synthetic dataset can also be inspected.

## Staff records and data handling

Open **/admin** on the live app or at **http://127.0.0.1:8000/admin** when running locally. Staff access uses HTTP Basic authentication. Set a private username and password in the environment before using the page.

Each record contains an aggregate meal date, meal, menu, number of eligible students, and number of meals served. Prepared portions and total discarded food in kilograms are optional. Enter waste only when it was measured consistently; leave it blank otherwise. Do not enter names, student IDs, room numbers, or individual attendance details.

- Mark examples as **demo data**. Demo records stay visible to staff but never affect real estimates.
- A record's demo/real type cannot be changed while editing it.
- The app prevents duplicate records for the same date, meal, and record type.
- Staff can edit saved records. The delete endpoint only removes demo records; real records are not deleted through that endpoint.
- **Download real CSV** exports aggregate non-demo records only. Store exported files carefully and share them only with approved people.
- Use HTTPS whenever staff pages are reachable over a network. Basic authentication credentials are not protected when sent over plain HTTP.

### Storage and production safety

Local development uses SQLite at **backend/messmind.db** by default. For hosted use, configure persistent PostgreSQL storage through a private **DATABASE_URL** (Neon is supported). SQLite files on Vercel's temporary filesystem do not provide durable record storage.

On Vercel, adding or editing non-demo records is enabled only when both a persistent database URL is present and **MESSMIND_ENABLE_REAL_RECORDS=true** is set. Keep those settings in the hosting provider's private environment variables, never in frontend code or a committed **.env** file. Enable real collection only after the college or mess has approved it and persistent storage has been checked.

## Run locally

Requirements: **Python 3.12 or newer**.

### Windows PowerShell

From the repository root:

~~~powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item backend\.env.example backend\.env
notepad backend\.env
~~~

In **backend/.env**, set a private **MESSMIND_ADMIN_PASSWORD**. The default local username is **mess-manager**; you can change it with **MESSMIND_ADMIN_USERNAME**. Leave **DATABASE_URL** empty to use local SQLite. Then start the app from the repository root:

~~~powershell
py -m uvicorn main:app --app-dir backend --reload
~~~

### macOS or Linux

From the repository root:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp backend/.env.example backend/.env
~~~

Edit **backend/.env** and set a private **MESSMIND_ADMIN_PASSWORD**, then run:

~~~bash
python -m uvicorn main:app --app-dir backend --reload
~~~

The local **.env** file is ignored by Git. Never replace it with a real credential in **.env.example** or commit it.

| Local URL | Purpose |
| --- | --- |
| **http://127.0.0.1:8000/** | Student-facing planner and demo |
| **http://127.0.0.1:8000/admin** | Staff records (browser sign-in required) |
| **http://127.0.0.1:8000/docs** | Interactive FastAPI documentation |
| **http://127.0.0.1:8000/health** | API health check |

## API overview

Interactive request/response schemas are available at **/docs**.

| Method | Route | Access | Purpose |
| --- | --- | --- | --- |
| **GET** | **/health** | Public | API health check |
| **GET** | **/demo/menu-plan** | Public | Supplied menus and simulation assumptions |
| **POST** | **/demo/predict** | Public | Simulate one day and meal; does not save a record |
| **POST** | **/demo/weekly-report** | Public | Generate a seven-day simulation report; does not save records |
| **POST** | **/predict** | Public | Estimate attendance and, when available, measured waste from non-demo history |
| **GET** | **/model/readiness** | Staff | Aggregate real-record counts and model thresholds |
| **GET** | **/records** | Staff | List saved aggregate records |
| **POST** | **/records** | Staff | Add a real or demo aggregate record |
| **PUT** | **/records/{id}** | Staff | Correct a record without changing its type |
| **DELETE** | **/records/{id}** | Staff | Delete a demo record only |
| **GET** | **/records/export.csv** | Staff | Download non-demo aggregate records as CSV |

Staff routes use the configured HTTP Basic credentials. The browser may show a username/password prompt when opening **/admin** or a staff-only route.

## Deploy on Vercel

This repository is configured for the Python FastAPI app through the Vercel entry point in **pyproject.toml**. The live deployment uses Neon PostgreSQL for persistent hosted storage.

Configure these as private Vercel project environment variables:

| Variable | Purpose |
| --- | --- |
| **DATABASE_URL** | Private PostgreSQL connection string; Vercel's Neon integration can provide it |
| **MESSMIND_ADMIN_USERNAME** | Staff sign-in username |
| **MESSMIND_ADMIN_PASSWORD** | Staff sign-in password |
| **MESSMIND_ENABLE_REAL_RECORDS** | Set to **true** only after persistent storage is connected and real-data collection is approved |

Redeploy after changing deployment environment variables. Never put these values in the README, frontend JavaScript, screenshots, or Git history.

## Technology

- **Frontend:** HTML, CSS, and browser JavaScript
- **API:** Python, FastAPI, Uvicorn, and SQLAlchemy
- **Storage:** SQLite locally; PostgreSQL for persistent hosted storage
- **Prediction:** Small in-project ridge-regression implementation; no external AI service or API key is required
- **Deployment:** Vercel, with Neon PostgreSQL available for persistent records
- **Visual interaction:** Local Sketchbook DOM/CSS 3D component and authored local assets

## Repository layout

~~~text
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
~~~

## Limitations and next steps

- The source menu workbook does not provide attendance or measured waste. Demo outputs are generated examples, not observations from the college.
- Synthetic holdout metrics test the demo model against its own generated rules; they do not establish real-world accuracy.
- Real estimates become useful only after enough approved, consistently entered records exist. Waste estimates additionally require actual waste measurements.
- The real model uses simple menu and weekday features and falls back to a same-meal average when the more complex model does not validate better. Compare estimates with observed kitchen results before relying on them for preparation decisions.
- The app stores aggregate totals only. It is not designed to collect student-level attendance or personal information.

## Author

Built by [@sahityadhiman](https://github.com/sahityadhiman).


## Admin page

[Open the live staff admin page](https://messmind-delta.vercel.app/admin) (staff login required).
