const demoForm = document.querySelector('#demo-form');

if (demoForm) {
  const daySelect = document.querySelector('#demo-day');
  const mealSelect = document.querySelector('#demo-meal');
  const studentInput = document.querySelector('#demo-students');
  const menuDisplay = document.querySelector('#demo-menu');
  const timeDisplay = document.querySelector('#demo-time');
  const message = document.querySelector('#demo-message');
  const submitButton = document.querySelector('#demo-submit');
  const reportButton = document.querySelector('#weekly-report-button');
  let menuPlan = null;

  function updateMenuPreview() {
    if (!menuPlan) return;
    const menu = menuPlan.days[daySelect.value]?.[mealSelect.value];
    menuDisplay.textContent = menu || 'No lunch menu was listed for Sunday.';
    timeDisplay.textContent = menuPlan.meal_times[mealSelect.value] || '';
    submitButton.disabled = !menu;
  }

  async function loadMenuPlan() {
    const response = await fetch('/demo/menu-plan');
    if (!response.ok) throw new Error('Could not load the demo menu.');
    menuPlan = await response.json();
    for (const day of Object.keys(menuPlan.days)) {
      const option = document.createElement('option');
      option.value = day;
      option.textContent = day;
      daySelect.append(option);
    }
    for (const meal of menuPlan.meals) {
      const option = document.createElement('option');
      option.value = meal;
      option.textContent = meal;
      mealSelect.append(option);
    }
    daySelect.value = 'Monday';
    mealSelect.value = 'Lunch';
    updateMenuPreview();
  }

  daySelect.addEventListener('change', updateMenuPreview);
  mealSelect.addEventListener('change', updateMenuPreview);

  reportButton.addEventListener('click', async () => {
    const modeRevision = window.messMindModeRevision;
    message.textContent = '';
    message.style.color = '';
    reportButton.disabled = true;
    reportButton.textContent = 'Preparing report…';
    try {
      const response = await fetch('/demo/weekly-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ students: Number(studentInput.value) })
      });
      const report = await response.json();
      if (!response.ok) throw new Error(report.detail || 'Could not prepare the report.');
      if (modeRevision !== window.messMindModeRevision) return;

      document.querySelector('#weekly-servings').textContent = report.estimated_weekly_meal_servings.toLocaleString();
      document.querySelector('#weekly-waste').textContent = report.estimated_weekly_food_waste_kg.toLocaleString(undefined, { maximumFractionDigits: 1 });
      document.querySelector('#weekly-highest').textContent =
        `Highest projected waste slot: ${report.highest_waste_slot.day} ${report.highest_waste_slot.meal} (${report.highest_waste_slot.estimated_food_waste_kg} kg).`;
      const rows = report.days.map((item) => {
        const row = document.createElement('tr');
        for (const value of [item.day, item.estimated_meal_servings.toLocaleString(), `${item.estimated_food_waste_kg} kg`]) {
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
    }
  });

  demoForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const modeRevision = window.messMindModeRevision;
    message.textContent = '';
    message.style.color = '';
    submitButton.disabled = true;
    submitButton.textContent = 'Simulating…';

    try {
      const response = await fetch('/demo/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          day: daySelect.value,
          meal: mealSelect.value,
          students: Number(studentInput.value)
        })
      });
      const prediction = await response.json();
      if (!response.ok) throw new Error(prediction.detail || 'Could not run the simulation.');
      if (modeRevision !== window.messMindModeRevision) return;

      document.querySelector('#demo-expected').textContent = prediction.expected_students.toLocaleString();
      document.querySelector('#demo-range').textContent =
        `Illustrative range: ${prediction.expected_students_low.toLocaleString()}–${prediction.expected_students_high.toLocaleString()} students`;
      document.querySelector('#demo-portions').textContent = prediction.suggested_portions.toLocaleString();
      document.querySelector('#demo-waste').textContent = prediction.estimated_food_waste_kg.toLocaleString(undefined, { maximumFractionDigits: 1 });
      document.querySelector('#demo-result-detail').textContent =
        `${prediction.day} ${prediction.meal}: ${prediction.menu}. ${prediction.message}`;
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
  });
}
