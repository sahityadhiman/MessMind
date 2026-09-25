# MessMind

MessMind is a student meal-planning project that will help a hostel mess estimate attendance and reduce food waste.

## Project folders

- `frontend/` — the browser interface
- `backend/` — the API that will connect the interface to the data and prediction logic
- `ml/` — attendance prediction work

## Current status

The frontend is connected to the backend API. When approved real attendance records exist, the API estimates attendance using the recent average for that meal. Demo records are excluded. This baseline does not use menu or weekday yet. A trained ML model may be added after enough real data has been collected and reviewed.

The student page only requests an estimate. Approved meal totals are entered through the password-protected staff page at `/admin`. The local password belongs in `backend/.env`; never commit that file or real meal records.

## Vercel demo deployment

Vercel can host this FastAPI app and its frontend. The Vercel version currently uses temporary demo storage, so demo records may reset after the server restarts. Real record creation and editing are disabled on Vercel until a permanent database is connected. Do not enter or share real attendance data on the demo deployment.

To deploy, push this repository to GitHub, import the `MessMind` repository at [vercel.com/new](https://vercel.com/new), then set these private project environment variables before deploying:

- `MESSMIND_ADMIN_USERNAME` — `mess-manager` (or a private username you choose)
- `MESSMIND_ADMIN_PASSWORD` — a strong password you choose; do not put it in GitHub or send it in chat

Vercel will use the root `requirements.txt` and `pyproject.toml` to locate the FastAPI app. The local development database remains `backend/messmind.db` and is not uploaded to GitHub.

## Open the prototype

Start the backend using the instructions in `backend/README.md`, then open `http://127.0.0.1:8000/` in a web browser. Enter a meal, menu, and student count, then choose **Estimate attendance**.
