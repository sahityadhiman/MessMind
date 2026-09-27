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

const portalChooser = document.querySelector('#portal-chooser');
const portalViews = [...document.querySelectorAll('[data-portal-view]')];
const homeLink = document.querySelector('#home-link');

function showPortal(view) {
  portalChooser.hidden = view !== 'chooser';
  portalViews.forEach((portal) => { portal.hidden = portal.id !== `${view}-portal`; });
  const headings = {
    chooser: '#portal-title',
    admin: '#admin-portal-title',
    'student-login': '#student-login-title',
    student: '#student-portal-title',
    staff: '#staff-portal-title'
  };
  setPredictionMode(view === 'student' ? 'demo' : 'real');
  const focusTarget = document.querySelector(headings[view] || headings.chooser);
  focusTarget?.focus({ preventScroll: true });
  if (view === 'student') {
    document.querySelector('#student-plan-date').value ||= document.querySelector('#demo-date').value || todayISODate();
    loadStudentPlanForDate();
  }
  window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}

document.querySelectorAll('[data-open-portal]').forEach((button) => {
  button.addEventListener('click', async () => {
    if (button.dataset.openPortal === 'student-login') {
      await openStudentArea();
      return;
    }
    showPortal(button.dataset.openPortal);
  });
});
document.querySelectorAll('[data-back-to-portals]').forEach((button) => {
  button.addEventListener('click', () => showPortal('chooser'));
});
document.querySelectorAll('[data-back-to-admin]').forEach((button) => {
  button.addEventListener('click', () => showPortal('admin'));
});
homeLink.addEventListener('click', (event) => {
  event.preventDefault();
  showPortal('chooser');
});

function todayISODate() {
  const localDate = new Date();
  localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
  return localDate.toISOString().slice(0, 10);
}

const studentPlanForm = document.querySelector('#student-plan-form');
const studentPlanDate = document.querySelector('#student-plan-date');
const studentPlanSummary = document.querySelector('#student-plan-summary');
const studentPlanMessage = document.querySelector('#student-plan-message');
const studentPlanList = document.querySelector('#student-plan-summary-list');
const studentPlanShareNote = document.querySelector('#student-plan-share-note');
const studentPlanSubmit = document.querySelector('#student-plan-submit');
const studentLoginMessage = document.querySelector('#student-login-message');
const studentAuthForm = document.querySelector('#student-auth-form');
const studentAuthEmail = document.querySelector('#student-auth-email');
const studentAuthPassword = document.querySelector('#student-auth-password');
const studentAuthSubmit = document.querySelector('#student-auth-submit');
const studentAuthPasswordHelp = document.querySelector('#student-auth-password-help');
const studentAccountEmail = document.querySelector('#student-account-email');
const studentMeals = [
  ['breakfast', 'Breakfast'], ['lunch', 'Lunch'], ['snacks', 'Snacks'], ['dinner', 'Dinner']
];
let studentAuthMode = 'login';
let signedInStudentEmail = '';
const studentPlanCache = new Map();
const submittedStudentPlanDates = new Set();
studentPlanDate.min = todayISODate();
studentPlanDate.max = dateOffsetISO(30);

function dateOffsetISO(offset) {
  const localDate = new Date();
  localDate.setDate(localDate.getDate() + offset);
  const month = String(localDate.getMonth() + 1).padStart(2, '0');
  const day = String(localDate.getDate()).padStart(2, '0');
  return `${localDate.getFullYear()}-${month}-${day}`;
}

function setStudentAuthMode(mode) {
  studentAuthMode = mode === 'signup' ? 'signup' : 'login';
  const signingUp = studentAuthMode === 'signup';
  document.querySelectorAll('[data-student-auth-mode]').forEach((tab) => {
    const active = tab.dataset.studentAuthMode === studentAuthMode;
    tab.classList.toggle('is-active', active);
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
  });
  studentAuthForm.setAttribute(
    'aria-labelledby',
    signingUp ? 'student-signup-tab' : 'student-login-tab'
  );
  studentAuthPassword.minLength = signingUp ? 12 : 0;
  studentAuthPassword.autocomplete = signingUp ? 'new-password' : 'current-password';
  studentAuthPasswordHelp.hidden = !signingUp;
  studentAuthSubmit.innerHTML = signingUp
    ? 'Create account <span aria-hidden="true">→</span>'
    : 'Sign in <span aria-hidden="true">→</span>';
  studentLoginMessage.textContent = '';
  studentLoginMessage.style.color = '';
}

document.querySelectorAll('[data-student-auth-mode]').forEach((tab) => {
  tab.addEventListener('click', () => setStudentAuthMode(tab.dataset.studentAuthMode));
});

async function openStudentArea() {
  studentLoginMessage.textContent = '';
  try {
    const response = await fetch('/auth/student/session');
    const current = await response.json();
    if (response.ok && current.authenticated) {
      signedInStudentEmail = current.email;
      studentAccountEmail.textContent = current.email;
      showPortal('student');
      return;
    }
    signedInStudentEmail = '';
    studentPlanCache.clear();
    submittedStudentPlanDates.clear();
    setStudentAuthMode('login');
    showPortal('student-login');
  } catch {
    setStudentAuthMode('login');
    showPortal('student-login');
    studentLoginMessage.textContent = 'Could not reach the sign-in service. Please try again.';
    studentLoginMessage.style.color = '#a34a3a';
  }
}

studentAuthForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  studentLoginMessage.textContent = '';
  studentLoginMessage.style.color = '';
  studentAuthSubmit.disabled = true;
  studentAuthSubmit.textContent = studentAuthMode === 'signup' ? 'Creating account…' : 'Signing in…';
  try {
    const response = await fetch(`/auth/student/${studentAuthMode}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: studentAuthEmail.value.trim(), password: studentAuthPassword.value })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Could not sign in. Please try again.');
    studentPlanCache.clear();
    submittedStudentPlanDates.clear();
    signedInStudentEmail = result.email;
    studentAccountEmail.textContent = result.email;
    studentAuthPassword.value = '';
    showPortal('student');
    studentPlanMessage.textContent = '';
  } catch (error) {
    studentLoginMessage.textContent = error.message || 'Could not sign in. Please try again.';
    studentLoginMessage.style.color = '#a34a3a';
  } finally {
    studentAuthSubmit.disabled = false;
    studentAuthSubmit.innerHTML = studentAuthMode === 'signup'
      ? 'Create account <span aria-hidden="true">→</span>'
      : 'Sign in <span aria-hidden="true">→</span>';
  }
});

document.querySelector('#student-logout').addEventListener('click', async () => {
  const logoutButton = document.querySelector('#student-logout');
  logoutButton.disabled = true;
  try {
    const response = await fetch('/auth/student/logout', { method: 'POST' });
    if (!response.ok) throw new Error('The server could not end the session.');
    signedInStudentEmail = '';
    studentAccountEmail.textContent = '';
    studentPlanCache.clear();
    submittedStudentPlanDates.clear();
    studentPlanSummary.hidden = true;
    setStudentAuthMode('login');
    showPortal('student-login');
    studentLoginMessage.textContent = 'You have signed out.';
  } catch {
    studentPlanMessage.textContent = 'Could not reach the sign-out service. Your session may still be active.';
    studentPlanMessage.style.color = '#a34a3a';
  } finally {
    logoutButton.disabled = false;
  }
});

window.messMindShowStudentLogin = (message = 'Your session ended. Please sign in again.') => {
  signedInStudentEmail = '';
  studentAccountEmail.textContent = '';
  studentPlanCache.clear();
  submittedStudentPlanDates.clear();
  setStudentAuthMode('login');
  showPortal('student-login');
  studentLoginMessage.textContent = message;
  studentLoginMessage.style.color = '#a34a3a';
};

window.messMindHasStudentPlan = (mealDate) => submittedStudentPlanDates.has(mealDate);

function renderStudentPlanSummary(plan, aggregate = null) {
  studentPlanList.replaceChildren();
  if (!plan) {
    studentPlanSummary.hidden = true;
    return;
  }
  for (const [meal, label] of studentMeals) {
    const item = document.createElement('li');
    const counts = aggregate?.meals?.[label];
    item.textContent = counts
      ? `${label}: ${plan[meal] === 'yes' ? 'Planning to eat' : 'Not planning to eat'} · ${counts.yes_count} of ${counts.response_count} combined plans say yes`
      : `${label}: ${plan[meal] === 'yes' ? 'Planning to eat' : 'Not planning to eat'}`;
    studentPlanList.append(item);
  }
  studentPlanShareNote.textContent = aggregate
    ? `Combined student totals are the primary attendance signal in Demo Simulation for ${studentPlanDate.value}. Intentions are unverified, not confirmed attendance.`
    : 'Your plan is stored with your account. Combined demo totals could not be loaded right now.';
  studentPlanSummary.hidden = false;
}

async function loadStudentPlanForDate() {
  const selectedDate = studentPlanDate.value;
  for (const [meal] of studentMeals) {
    studentPlanForm.querySelectorAll(`input[name="${meal}"]`).forEach((input) => {
      input.checked = false;
    });
  }
  studentPlanMessage.textContent = '';
  studentPlanMessage.style.color = '';
  studentPlanSummary.hidden = true;
  if (!selectedDate || !signedInStudentEmail) return;
  try {
    const response = await fetch(`/demo/student-plans?meal_date=${encodeURIComponent(selectedDate)}`);
    const aggregate = await response.json();
    if (response.status === 401) {
      window.messMindShowStudentLogin();
      return;
    }
    if (!response.ok) throw new Error(aggregate.detail || 'Could not load your saved plan.');
    const saved = aggregate.own_plan
      ? Object.fromEntries(studentMeals.map(([meal]) => [meal, aggregate.own_plan[meal] ? 'yes' : 'no']))
      : null;
    if (saved) {
      studentPlanCache.set(selectedDate, saved);
      submittedStudentPlanDates.add(selectedDate);
    } else {
      studentPlanCache.delete(selectedDate);
      submittedStudentPlanDates.delete(selectedDate);
    }
    if (studentPlanDate.value !== selectedDate) return;
    for (const [meal] of studentMeals) {
      const choice = saved?.[meal];
      const radio = choice === 'yes' || choice === 'no'
        ? studentPlanForm.querySelector(`input[name="${meal}"][value="${choice}"]`)
        : null;
      studentPlanForm.querySelectorAll(`input[name="${meal}"]`).forEach((input) => {
        input.checked = input === radio;
      });
    }
    renderStudentPlanSummary(saved, aggregate);
    window.dispatchEvent(new CustomEvent('messmind:student-plan-status', {
      detail: { mealDate: selectedDate, hasPlan: Boolean(saved) }
    }));
  } catch (error) {
    studentPlanMessage.textContent = error.message || 'Could not load your saved plan.';
    studentPlanMessage.style.color = '#a34a3a';
  }
}

studentPlanDate.addEventListener('change', (event) => {
  if (event.isTrusted) studentPlanDate.dataset.userSelected = 'true';
  loadStudentPlanForDate();
  const demoDate = document.querySelector('#demo-date');
  if (demoDate.value !== studentPlanDate.value) {
    demoDate.value = studentPlanDate.value;
    demoDate.dispatchEvent(new Event('change'));
  }
});
studentPlanForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (studentPlanDate.value < todayISODate()) {
    studentPlanMessage.textContent = 'Choose today or a future date.';
    return;
  }
  if (studentPlanDate.value > dateOffsetISO(30)) {
    studentPlanMessage.textContent = 'Choose a date within the next 30 days.';
    return;
  }
  studentPlanMessage.style.color = '';
  const plan = Object.fromEntries(studentMeals.map(([meal]) => [
    meal,
    new FormData(studentPlanForm).get(meal)
  ]));
  studentPlanSubmit.disabled = true;
  studentPlanSubmit.textContent = 'Saving required plan…';
  try {
    const response = await fetch('/demo/student-plans', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        meal_date: studentPlanDate.value,
        meals: Object.fromEntries(studentMeals.map(([key, label]) => [label, plan[key] === 'yes']))
      })
    });
    const aggregate = await response.json();
    if (response.status === 401) {
      window.messMindShowStudentLogin();
      return;
    }
    if (!response.ok) throw new Error(aggregate.detail || 'Could not save your demo plan.');

    studentPlanCache.set(studentPlanDate.value, plan);
    submittedStudentPlanDates.add(studentPlanDate.value);
    window.dispatchEvent(new CustomEvent('messmind:student-plan-saved', {
      detail: { mealDate: studentPlanDate.value }
    }));
    window.dispatchEvent(new CustomEvent('messmind:student-plan-status', {
      detail: { mealDate: studentPlanDate.value, hasPlan: true }
    }));
    studentPlanMessage.textContent = 'Saved to your account. Combined student plans now shape the matching Demo Simulation; your plan is not sent to the kitchen.';
    renderStudentPlanSummary(plan, aggregate);
  } catch (error) {
    studentPlanMessage.textContent = error.message || 'Could not save your plan. Please try again when the server is available.';
    studentPlanMessage.style.color = '#a34a3a';
  } finally {
    studentPlanSubmit.disabled = false;
    studentPlanSubmit.innerHTML = 'Save required demo plan <span aria-hidden="true">→</span>';
  }
});

document.querySelector('#student-open-demo').addEventListener('click', () => {
  const plan = studentPlanCache.get(studentPlanDate.value) || {};
  const firstYesMeal = studentMeals.find(([meal]) => plan[meal] === 'yes')?.[1];
  const demoDateInput = document.querySelector('#demo-date');
  const demoMealSelect = document.querySelector('#demo-meal');
  demoDateInput.value = studentPlanDate.value;
  if (firstYesMeal) demoMealSelect.value = firstYesMeal;
  demoDateInput.dispatchEvent(new Event('change'));
  demoMealSelect.dispatchEvent(new Event('change'));
  document.querySelector('#demo-form').scrollIntoView({
    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    block: 'start'
  });
  demoDateInput.focus({ preventScroll: true });
});

const modePanels = [...document.querySelectorAll('[data-mode-panel]')];
window.messMindModeRevision = 0;

function setPredictionMode(mode) {
  const selectedMode = mode === 'demo' ? 'demo' : 'real';
  document.documentElement.dataset.mode = selectedMode;
  window.messMindModeRevision += 1;
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
}

setPredictionMode('real');

const date = new Date();
const forecastDate = document.querySelector('#forecast-date');
if (forecastDate) {
  forecastDate.value = todayISODate();
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
