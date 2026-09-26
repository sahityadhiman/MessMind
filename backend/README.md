# MessMind backend

The API keeps a separate simulation path and staff-entered record path. Real-history estimates exclude DEMO rows. After three non-demo records for the selected meal, the app can show a weighted same-meal average. With at least 35 non-demo rows, it evaluates ridge regression on an older/newer chronological split and uses the model only if it beats the simple average. Measured-waste predictions follow the same process using rows that actually contain a waste measurement. These checks help avoid using a more complex model when it performs worse; they do not prove accuracy for real kitchen decisions.

## Start it on Windows

Open PowerShell in this `backend` folder, then run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
notepad .env
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload
```

In `.env`, set a private value for `MESSMIND_ADMIN_PASSWORD`. Keep this password private; `.env` is excluded from Git. The default username is `mess-manager`. The browser asks for these credentials when you open the staff page.

Open `http://127.0.0.1:8000/` for the student page, `/admin` for staff records, and `/docs` for API documentation. The local app uses `backend/messmind.db`.

## Main routes

- `POST /predict` accepts `meal`, `menu`, `students`, and optional `meal_date` (`YYYY-MM-DD`). It estimates attendance from non-demo rows and may return a measured-waste estimate.
- `GET /model/readiness` requires staff login and returns aggregate attendance/waste counts and model thresholds. It does not reveal records.
- `GET /demo/menu-plan` returns the supplied weekday menu, assumptions, and synthetic-only validation information.
- `POST /demo/predict` accepts `day`, `meal`, and `students`, then returns simulated attendance, suggested portions, and simulated waste. The blank Sunday lunch is unavailable.
- `POST /demo/weekly-report` summarizes a simulated menu week and does not save the report as real data.
- `POST /records` saves a staff-entered aggregate meal record: `meal_date`, `meal`, `menu`, `students`, and `meals_served`, plus optional `prepared_portions` and `food_waste_kg`.
- `PUT /records/{id}` edits a saved record but keeps its DEMO or non-demo type unchanged. Blank measurements stay blank; they are never treated as zero.
- `GET /records` returns saved records to authenticated staff.
- `GET /records/export.csv` downloads non-demo aggregate rows only; no identity fields are stored or exported.
- `DELETE /records/{id}` deletes DEMO records only. Non-demo records are protected from this route.

## Data and model notes

Only enter real records if the mess or college has approved their use. Never enter student names, IDs, or room numbers. Use the same method each time you weigh food waste and enter the total in kg. If it was not measured, leave the field blank. The real-data model uses up to the latest 500 non-demo rows.

The demo model and `ml/data/demo_training_data.csv` use generated values, not college measurements. To recreate that CSV from the repository root, run `py -m ml.generate_demo_data`. Synthetic rows are not used by the real-history prediction path and are not valid for actual food-preparation decisions. No external AI API key is needed.

The staff page and record APIs require the configured login. Use HTTPS when the app is reachable over a network because HTTP Basic credentials are not encrypted over plain HTTP.

On Vercel, SQLite storage under `/tmp` is temporary. The app blocks adding or editing non-demo records until persistent storage is connected and `MESSMIND_ENABLE_REAL_RECORDS=true` is explicitly set. Keep real-data collection disabled until the college approves it and storage persistence is confirmed. Connect Neon Postgres using the private `DATABASE_URL` environment variable. Set `MESSMIND_ADMIN_USERNAME` and `MESSMIND_ADMIN_PASSWORD` as private host environment variables.
