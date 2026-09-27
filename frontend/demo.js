const demoForm = document.querySelector('#demo-form');

if (demoForm) {
  const dateInput = document.querySelector('#demo-date');
  const dayLabel = document.querySelector('#demo-day-label');
  const mealSelect = document.querySelector('#demo-meal');
  const studentInput = document.querySelector('#demo-students');
  const menuDisplay = document.querySelector('#demo-menu');
  const timeDisplay = document.querySelector('#demo-time');
  const message = document.querySelector('#demo-message');
  const submitButton = document.querySelector('#demo-submit');
  const reportButton = document.querySelector('#weekly-report-button');
  const planRequirement = document.querySelector('#demo-plan-requirement');
  const planSignal = document.querySelector('#demo-plan-signal');
  let menuPlan = null;

  function hasStudentPlan(mealDate) {
    if (window.messMindHasStudentPlan) return window.messMindHasStudentPlan(mealDate);
    return false;
  }

  function localISODate(value) {
    const localDate = new Date(value);
    const month = String(localDate.getMonth() + 1).padStart(2, '0');
    const day = String(localDate.getDate()).padStart(2, '0');
    return `${localDate.getFullYear()}-${month}-${day}`;
  }

  function weekdayForISO(value) {
    if (!value) return '';
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString('en', { weekday: 'long' });
  }

  function clearOldResults() {
    document.querySelector('#demo-result').hidden = true;
    document.querySelector('#weekly-report').hidden = true;
  }

  function updateMenuPreview() {
    if (!menuPlan) return;
    const day = weekdayForISO(dateInput.value);
    dayLabel.textContent = day || 'Choose a date';
    const menu = menuPlan.days[day]?.[mealSelect.value];
    menuDisplay.textContent = menu || 'No lunch menu was listed for Sunday.';
    timeDisplay.textContent = menuPlan.meal_times[mealSelect.value] || '';
    const planSaved = hasStudentPlan(dateInput.value);
    submitButton.disabled = !menu || !dateInput.value || !planSaved;
    reportButton.disabled = !dateInput.value || !planSaved;
    planRequirement.textContent = planSaved
      ? `Required plan saved for ${dateInput.value}. Combined plans lead 70–80% of matching attendance forecasts. For a 7-day report, save a plan for every date in that week.`
      : 'First sign in and save your student meal plan for this date above. Combined plans lead the attendance simulation and never affect Real Estimation.';
  }

  async function loadMenuPlan() {
    const response = await fetch('/demo/menu-plan');
    if (!response.ok) throw new Error('Could not load the demo menu.');
    menuPlan = await response.json();
    for (const meal of menuPlan.meals) {
      const option = document.createElement('option');
      option.value = meal;
      option.textContent = meal;
      mealSelect.append(option);
    }
    const nextMonday = new Date();
    nextMonday.setDate(nextMonday.getDate() + ((8 - nextMonday.getDay()) % 7));
    dateInput.min = localISODate(new Date());
    const maximumDate = new Date();
    maximumDate.setDate(maximumDate.getDate() + 30);
    dateInput.max = localISODate(maximumDate);
    const target = window.messMindDemoTarget;
    dateInput.value = target?.date || localISODate(nextMonday);
    mealSelect.value = target?.meal || 'Lunch';
    const studentPlanDate = document.querySelector('#student-plan-date');
    if (studentPlanDate && !studentPlanDate.dataset.userSelected) {
      studentPlanDate.value = dateInput.value;
      studentPlanDate.dispatchEvent(new Event('change'));
    }
    window.messMindDemoTarget = null;
    updateMenuPreview();
  }

  dateInput.addEventListener('change', () => {
    clearOldResults();
    updateMenuPreview();
  });
  mealSelect.addEventListener('change', () => {
    clearOldResults();
    updateMenuPreview();
  });
  studentInput.addEventListener('input', clearOldResults);
  window.addEventListener('messmind:student-plan-saved', (event) => {
    if (event.detail?.mealDate) dateInput.value = event.detail.mealDate;
    clearOldResults();
    updateMenuPreview();
  });
  window.addEventListener('messmind:student-plan-status', (event) => {
    if (event.detail?.mealDate === dateInput.value) {
      clearOldResults();
      updateMenuPreview();
    }
  });

  reportButton.addEventListener('click', async () => {
    if (!hasStudentPlan(dateInput.value)) {
      message.textContent = 'Sign in and save your student meal plan for this date before running the demo report.';
      message.style.color = '#a34a3a';
      return;
    }
    const modeRevision = window.messMindModeRevision;
    clearOldResults();
    message.textContent = '';
    message.style.color = '';
    reportButton.disabled = true;
    reportButton.textContent = 'Preparing report…';
    try {
      const response = await fetch('/demo/weekly-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ students: Number(studentInput.value), start_date: dateInput.value })
      });
      const report = await response.json();
      if (response.status === 401) {
        window.messMindShowStudentLogin?.();
        return;
      }
      if (!response.ok) throw new Error(report.detail || 'Could not prepare the report.');
      if (modeRevision !== window.messMindModeRevision) return;

      document.querySelector('#weekly-servings').textContent = report.estimated_weekly_meal_servings.toLocaleString();
      document.querySelector('#weekly-waste').textContent = report.estimated_weekly_food_waste_kg.toLocaleString(undefined, { maximumFractionDigits: 1 });
      document.querySelector('#weekly-highest').textContent =
        `Highest projected waste slot: ${report.highest_waste_slot.day} ${report.highest_waste_slot.meal} (${report.highest_waste_slot.estimated_food_waste_kg} kg).`;
      const rows = report.days.map((item) => {
        const row = document.createElement('tr');
        for (const value of [`${item.day} · ${item.date}`, item.estimated_meal_servings.toLocaleString(), `${item.estimated_food_waste_kg} kg`]) {
          const cell = document.createElement('td');
          cell.textContent = value;
          row.append(cell);
        }
        return row;
      });
      document.querySelector('#weekly-days').replaceChildren(...rows);
      document.querySelector('#weekly-note').textContent = report.message;
      document.querySelector('#weekly-report').hidden = false;
    } catch (error) {
      if (modeRevision !== window.messMindModeRevision) return;
      message.textContent = error.message;
      message.style.color = '#a34a3a';
    } finally {
      reportButton.disabled = false;
      reportButton.textContent = 'View 7-day demo report';
      updateMenuPreview();
    }
  });

  demoForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!hasStudentPlan(dateInput.value)) {
      message.textContent = 'Sign in and save your student meal plan for this date before running the simulation.';
      message.style.color = '#a34a3a';
      return;
    }
    const modeRevision = window.messMindModeRevision;
    clearOldResults();
    message.textContent = '';
    message.style.color = '';
    submitButton.disabled = true;
    submitButton.textContent = 'Simulating…';

    try {
      const response = await fetch('/demo/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          day: weekdayForISO(dateInput.value),
          meal: mealSelect.value,
          students: Number(studentInput.value),
          meal_date: dateInput.value
        })
      });
      const prediction = await response.json();
      if (response.status === 401) {
        window.messMindShowStudentLogin?.();
        return;
      }
      if (!response.ok) throw new Error(prediction.detail || 'Could not run the simulation.');
      if (modeRevision !== window.messMindModeRevision) return;

      document.querySelector('#demo-expected').textContent = prediction.expected_students.toLocaleString();
      document.querySelector('#demo-range').textContent =
        `Illustrative range: ${prediction.expected_students_low.toLocaleString()}–${prediction.expected_students_high.toLocaleString()} students`;
      document.querySelector('#demo-portions').textContent = prediction.suggested_portions.toLocaleString();
      document.querySelector('#demo-waste').textContent = prediction.estimated_food_waste_kg.toLocaleString(undefined, { maximumFractionDigits: 1 });
      document.querySelector('#demo-result-detail').textContent =
        `${prediction.meal_date || prediction.day} · ${prediction.day} ${prediction.meal}: ${prediction.menu}. ${prediction.message}`;
      planSignal.textContent = prediction.student_plan_responses
        ? `Primary student-plan signal for ${prediction.day} ${prediction.meal}: ${prediction.student_plan_yes} of ${prediction.student_plan_responses} plan responses say yes. Plans contribute ${Math.round(prediction.student_plan_influence * 100)}% of this attendance forecast; the generated baseline contributes the rest. Intentions are unverified, and waste is synthetic, not measured kitchen data.`
        : `No student plans are recorded for ${prediction.day} ${prediction.meal} on ${prediction.meal_date}. Attendance uses the generated baseline; portions and waste use synthetic assumptions.`;
      document.querySelector('#synthetic-evaluation').textContent =
        `Model: ${prediction.model_name}, fitted on ${prediction.training_rows} generated examples and checked on ${prediction.holdout_rows} separate generated examples (from ${prediction.dataset_rows} total). Mean error on that synthetic holdout was ${prediction.synthetic_attendance_mae_percent} percentage points for attendance and ${prediction.synthetic_waste_mae_kg_per_1000} kg per 1,000 students for waste. This only checks the simulation against its own generated data; it is not real-world accuracy.`;
      document.querySelector('#demo-result').hidden = false;
    } catch (error) {
      if (modeRevision !== window.messMindModeRevision) return;
      message.textContent = error.message;
      message.style.color = '#a34a3a';
    } finally {
      submitButton.disabled = false;
      submitButton.innerHTML = 'Run simulated prediction <span aria-hidden="true">→</span>';
      updateMenuPreview();
    }
  });

  loadMenuPlan().catch((error) => {
    menuDisplay.textContent = 'The menu could not be loaded.';
    message.textContent = error.message;
    message.style.color = '#a34a3a';
    submitButton.disabled = true;
    reportButton.disabled = true;
  });
}
