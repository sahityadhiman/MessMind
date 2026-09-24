# MessMind backend

This is the first API version. It accepts meal details and returns a clearly marked sample attendance estimate. It does not use a database or a trained prediction model yet.

## Start it on Windows

Open PowerShell in this `backend` folder, then run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload
```

When it starts, open `http://127.0.0.1:8000/` to use the webpage, or `http://127.0.0.1:8000/docs` to see and try the API. The sample endpoint is `POST /predict` and expects `meal`, `menu`, and `students`.
