# MessMind backend

This API estimates attendance from the recent average of approved real records for the same meal and saves aggregate meal records in a local SQLite database. It ignores demo records and reports when no real history is available. The baseline does not use menu or weekday yet, and it is not a trained ML model.

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

In the `.env` file, set a private staff password after `MESSMIND_ADMIN_PASSWORD=` and save it. Keep this password private; `.env` is excluded from Git. Use `mess-manager` as the username unless you change it in that file. The browser will ask for these credentials when you open the staff page.

When it starts, open `http://127.0.0.1:8000/` for the student estimate page, `http://127.0.0.1:8000/admin` for staff records, or `http://127.0.0.1:8000/docs` to see the API.

- `POST /predict` accepts `meal`, `menu`, and `students`, and uses up to the 30 latest real records for the same meal. It returns a message instead of a number when no real records are available.
- `POST /records` saves one aggregate meal record: `meal_date`, `meal`, `menu`, `students`, and `meals_served`.
- `PUT /records/{id}` lets authorized staff correct a saved record while keeping its DEMO or REAL type unchanged.
- `GET /records` returns saved meal records.
- `DELETE /records/{id}` removes a demo record only; real records are protected.

The local database is `messmind.db`. It is ignored by Git so meal data is not uploaded to GitHub. Only enter real records if the mess or college has approved their use; do not add student names, IDs, or room numbers.

The student-facing page does not expose record entry. The staff page and record APIs require the configured staff login. This setup is for local development; do not deploy it over plain HTTP. HTTP Basic credentials require HTTPS when used over a network.
