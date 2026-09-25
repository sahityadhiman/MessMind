# MessMind backend

This API estimates attendance from the recent average of approved real records for the same meal and saves aggregate meal records in a local SQLite database. It ignores demo records and reports when no real history is available. It does not use a trained ML model yet.

## Start it on Windows

Open PowerShell in this `backend` folder, then run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload
```

When it starts, open `http://127.0.0.1:8000/` to use the webpage, or `http://127.0.0.1:8000/docs` to see the API.

- `POST /predict` accepts `meal`, `menu`, and `students`, and uses up to the 30 latest real records for the same meal. It returns a message instead of a number when no real records are available.
- `POST /records` saves one aggregate meal record: `meal_date`, `meal`, `menu`, `students`, and `meals_served`.
- `GET /records` returns saved meal records.
- `DELETE /records/{id}` removes a demo record only; real records are protected.

The local database is `messmind.db`. It is ignored by Git so meal data is not uploaded to GitHub. Only enter real records if the mess or college has approved their use; do not add student names, IDs, or room numbers.

Before making this app available to students or deploying it publicly, protect record creation and deletion with staff access control. The student-facing page intentionally does not expose record entry.
