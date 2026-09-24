# MessMind backend

This API returns a clearly marked sample attendance estimate and saves aggregate meal records in a local SQLite database. It does not use a trained prediction model yet.

## Start it on Windows

Open PowerShell in this `backend` folder, then run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload
```

When it starts, open `http://127.0.0.1:8000/` to use the webpage, or `http://127.0.0.1:8000/docs` to see the API.

- `POST /predict` accepts `meal`, `menu`, and `students`, and returns a sample estimate.
- `POST /records` saves one aggregate meal record: `meal_date`, `meal`, `menu`, `students`, and `meals_served`.
- `GET /records` returns saved meal records.

The local database is `messmind.db`. It is ignored by Git so meal data is not uploaded to GitHub. Only enter real records if the mess or college has approved their use; do not add student names, IDs, or room numbers.
