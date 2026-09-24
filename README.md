# MessMind

MessMind is a student meal-planning project that will help a hostel mess estimate attendance and reduce food waste.

## Project folders

- `frontend/` — the browser interface
- `backend/` — the API that will connect the interface to the data and prediction logic
- `ml/` — attendance prediction work

## Current status

The frontend is an early prototype connected to the backend API. Its attendance number is still a sample calculation, not a real prediction. The backend can save aggregate meal records in a local SQLite database. Demo records are clearly marked and must not be used for predictions; a trained prediction model is still to come.

## Open the prototype

Start the backend using the instructions in `backend/README.md`, then open `http://127.0.0.1:8000/` in a web browser. Enter a meal, menu, and student count, then choose **Estimate attendance**.
