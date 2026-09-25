# MessMind

MessMind is a student meal-planning project that will help a hostel mess estimate attendance and reduce food waste.

## Project folders

- `frontend/` — the browser interface
- `backend/` — the API that will connect the interface to the data and prediction logic
- `ml/` — attendance prediction work

## Current status

The frontend is connected to the backend API. When approved real attendance records exist, the API estimates attendance using the recent average for that meal. Demo records are excluded. A trained ML model may be added after enough real data has been collected and reviewed.

The student page only requests an estimate. Approved meal totals are entered through the password-protected staff page at `/admin`. The local password belongs in `backend/.env`; never commit that file or real meal records.

## Open the prototype

Start the backend using the instructions in `backend/README.md`, then open `http://127.0.0.1:8000/` in a web browser. Enter a meal, menu, and student count, then choose **Estimate attendance**.
