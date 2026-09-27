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

Open `http://127.0.0.1:8000/` for the role chooser, student account sign-in/sign-up, and meal planner; `/admin` is for protected staff records; `/docs` has the API documentation. Student account email addresses are not verified against a college. The local app uses `backend/messmind.db`.

## Main routes

- `POST /predict` accepts `meal`, `menu`, `students`, and optional `meal_date` (`YYYY-MM-DD`). It estimates attendance from non-demo rows and may return a measured-waste estimate.
- `GET /model/readiness` requires staff login and returns aggregate attendance/waste counts and model thresholds. It does not reveal records.
- `POST /auth/student/signup` creates an account and starts a student session. Sign-up requires an email and a password of at least 12 characters.
- `POST /auth/student/login` checks the password and starts a session. `GET /auth/student/session` reports whether the browser has a session; `POST /auth/student/logout` revokes it.
- `GET /demo/menu-plan` returns the supplied weekday menu, assumptions, and synthetic-only validation information.
- `POST /demo/student-plans` requires a student session, a date, and yes/no choices for each meal. The plan is keyed by a date-specific participant hash and returns aggregate counts plus only the signed-in student's own choices.
- `GET /demo/student-plans?meal_date=YYYY-MM-DD` requires a student session and returns combined yes/response counts by meal plus the signed-in student's own saved plan. It never returns other students' individual plans.
- `POST /demo/predict` requires a student session and `day`, `meal`, `students`, and `meal_date`. It rejects predictions unless a student plan has been submitted for that date and meal. Combined, unverified intentions drive 70–80% of the attendance forecast and the generated baseline supplies the rest. Food-waste values remain synthetic; student plans never affect `/predict`, staff records, or real estimates. The blank Sunday lunch is unavailable.
- `POST /demo/weekly-report` requires a student session and accepts an eligible-student count and optional `start_date`, then returns a seven-day simulation only if every scheduled meal on every report date has at least one student plan response. It never fills a missing slot with the generated baseline or saves report values as real data.
- `POST /records` saves a staff-entered aggregate meal record: `meal_date`, `meal`, `menu`, `students`, and `meals_served`, plus optional `prepared_portions` and `food_waste_kg`.
- `PUT /records/{id}` edits a saved record but keeps its DEMO or non-demo type unchanged. Blank measurements stay blank; they are never treated as zero.
- `GET /records` returns saved records to authenticated staff.
- `GET /records/export.csv` downloads non-demo aggregate rows only; no identity fields are stored or exported.
- `DELETE /records/{id}` deletes DEMO records only. Non-demo records are protected from this route.

## Data and model notes

Only enter real records if the mess or college has approved their use. Never enter student names, IDs, or room numbers. Student accounts store an email address and a salted password hash for sign-in; the email is not verified against a college, so this is not proof of student identity. Student meal intentions are not attendance records; their separate table is excluded from every real estimate. Meal plans use a date-specific participant hash and are returned as combined counts, with an individual student able to retrieve only their own saved choices. Use the same method each time you weigh food waste and enter the total in kg. If it was not measured, leave the field blank. The real-data model uses up to the latest 500 non-demo rows.

The demo model and `ml/data/demo_training_data.csv` use generated values, not college measurements. To recreate that CSV from the repository root, run `py -m ml.generate_demo_data`. Synthetic rows are not used by the real-history prediction path and are not valid for actual food-preparation decisions. No external AI API key is needed.

The staff page and record APIs require the configured login. Student sessions use a 14-day HTTP-only, same-site cookie and are stored server-side as hashed random tokens. Use HTTPS when the app is reachable over a network because HTTP Basic credentials are not encrypted over plain HTTP.

On Vercel, SQLite storage under `/tmp` is temporary. Student account sign-up and sign-in are disabled unless persistent PostgreSQL storage is configured through the private `DATABASE_URL` environment variable. The app also blocks adding or editing non-demo records until `MESSMIND_ENABLE_REAL_RECORDS=true` is explicitly set. Keep real-data collection disabled until the college approves it and storage persistence is confirmed. Connect Neon Postgres using the private `DATABASE_URL` environment variable. Set `MESSMIND_ADMIN_USERNAME` and `MESSMIND_ADMIN_PASSWORD` as private host environment variables.
