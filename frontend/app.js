const themeToggle = document.querySelector('#theme-toggle');
if (themeToggle) {
  const themeLabel = document.querySelector('#theme-label');
  const syncThemeControl = (theme) => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    themeToggle.setAttribute('aria-pressed', String(theme === 'dark'));
    themeToggle.setAttribute('aria-label', `Switch to ${nextTheme} mode`);
    themeToggle.title = `Switch to ${nextTheme} mode`;
    themeLabel.textContent = nextTheme === 'dark' ? 'Dark' : 'Light';
  };

  syncThemeControl(document.documentElement.dataset.theme || 'light');
  themeToggle.addEventListener('click', () => {
    const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = nextTheme;
    syncThemeControl(nextTheme);
    try {
      localStorage.setItem('messmind-theme', nextTheme);
    } catch {
      // The selected mode still works for this page if storage is unavailable.
    }
  });
}

const realModeButton = document.querySelector('#real-mode-button');
const demoModeButton = document.querySelector('#demo-mode-button');
const modeDescription = document.querySelector('#mode-description');
const modePanels = [...document.querySelectorAll('[data-mode-panel]')];
const modeCopy = {
  real: 'Uses staff-entered records only. If there isn’t enough history yet, MessMind will say so instead of inventing a real-data estimate.',
  demo: 'Uses clearly labeled generated examples based on the supplied menu plan. Demo predictions and reports never become real staff records.'
};
window.messMindModeRevision = 0;

function setPredictionMode(mode, persist = true) {
  const selectedMode = mode === 'demo' ? 'demo' : 'real';
  document.documentElement.dataset.mode = selectedMode;
  window.messMindModeRevision += 1;
  realModeButton.classList.toggle('is-active', selectedMode === 'real');
  demoModeButton.classList.toggle('is-active', selectedMode === 'demo');
  realModeButton.setAttribute('aria-pressed', String(selectedMode === 'real'));
  demoModeButton.setAttribute('aria-pressed', String(selectedMode === 'demo'));
  modeDescription.textContent = modeCopy[selectedMode];
  modePanels.forEach((panel) => { panel.hidden = panel.dataset.modePanel !== selectedMode; });

  // A mode change starts a fresh view, so results from the other mode cannot be mistaken for current output.
  for (const id of ['result', 'demo-result', 'weekly-report']) {
    const result = document.getElementById(id);
    if (result) result.hidden = true;
  }
  for (const id of ['demo-message']) {
    const message = document.getElementById(id);
    if (message) message.textContent = '';
  }
  if (persist) {
    try { localStorage.setItem('messmind-prediction-mode', selectedMode); } catch { /* Mode remains usable for this page. */ }
  }
}

realModeButton.addEventListener('click', () => setPredictionMode('real'));
demoModeButton.addEventListener('click', () => setPredictionMode('demo'));
let savedMode = 'real';
try { savedMode = localStorage.getItem('messmind-prediction-mode') || 'real'; } catch { /* Use the safe real-data default. */ }
setPredictionMode(savedMode, false);

const date = new Date();
const forecastDate = document.querySelector('#forecast-date');
if (forecastDate) {
  const localDate = new Date();
  localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
  forecastDate.value = localDate.toISOString().slice(0, 10);
}
document.querySelector('#today').textContent = new Intl.DateTimeFormat('en', {
  weekday: 'short', month: 'short', day: 'numeric'
}).format(date);

document.querySelector('#meal-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const modeRevision = window.messMindModeRevision;
  const students = Number(document.querySelector('#students').value);
  const meal = document.querySelector('#meal').value;
  const menu = document.querySelector('#menu').value.trim();
  const mealDate = forecastDate.value;
  const button = event.currentTarget.querySelector('button[type="submit"]');
  const originalButtonText = button.innerHTML;

  button.disabled = true;
  button.textContent = 'Getting estimate…';

  try {
    const response = await fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meal, menu, students, meal_date: mealDate })
    });

    if (!response.ok) {
      throw new Error(`The API returned an error (${response.status}).`);
    }

    const prediction = await response.json();
    if (modeRevision !== window.messMindModeRevision) return;
    const estimate = document.querySelector('#estimate');
    const estimateUnit = document.querySelector('#estimate-unit');
    const resultLabel = document.querySelector('#result-label');
    if (prediction.students_expected === null) {
      estimate.textContent = 'Not ready';
      estimateUnit.textContent = '';
      resultLabel.textContent = 'REAL RECORDS NEEDED';
      document.querySelector('#result-detail').textContent = prediction.message;
    } else {
      estimate.textContent = prediction.students_expected.toLocaleString();
      estimateUnit.textContent = 'students expected';
      resultLabel.textContent = prediction.attendance_method?.includes('ridge')
        ? 'REAL-DATA TREND MODEL'
        : 'HISTORICAL AVERAGE';
      document.querySelector('#result-detail').textContent =
        `${prediction.message} Estimated attendance: ${(prediction.attendance_rate * 100).toFixed(1)}%.`;
    }
    const wasteSummary = document.querySelector('#historical-waste');
    wasteSummary.textContent = prediction.estimated_food_waste_kg == null
      ? 'Measured-waste estimate is not ready yet. Add at least 3 same-meal real waste measurements; blanks are not counted as zero.'
      : `Estimated measured food waste: ${Number(prediction.estimated_food_waste_kg).toLocaleString(undefined, { maximumFractionDigits: 1 })} kg (${prediction.waste_method}, ${prediction.waste_records_used} measured records).`;
    document.querySelector('#result').hidden = false;
  } catch (error) {
    if (modeRevision !== window.messMindModeRevision) return;
    window.alert(`Couldn't get an estimate. Make sure the MessMind server is running. ${error.message}`);
  } finally {
    button.disabled = false;
    button.innerHTML = originalButtonText;
  }
});
