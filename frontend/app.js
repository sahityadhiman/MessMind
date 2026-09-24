const date = new Date();
document.querySelector('#today').textContent = new Intl.DateTimeFormat('en', {
  weekday: 'short', month: 'short', day: 'numeric'
}).format(date);

document.querySelector('#meal-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const students = Number(document.querySelector('#students').value);
  const meal = document.querySelector('#meal').value;
  const menu = document.querySelector('#menu').value.trim();
  const button = event.currentTarget.querySelector('button[type="submit"]');
  const originalButtonText = button.innerHTML;

  button.disabled = true;
  button.textContent = 'Getting estimate…';

  try {
    const response = await fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meal, menu, students })
    });

    if (!response.ok) {
      throw new Error(`The API returned an error (${response.status}).`);
    }

    const prediction = await response.json();
    document.querySelector('#estimate').textContent =
      prediction.students_expected.toLocaleString();
    document.querySelector('#result-detail').textContent =
      `${prediction.students_expected.toLocaleString()} of ${prediction.students.toLocaleString()} students may attend ${prediction.meal.toLowerCase()} for ${prediction.menu}.`;
    document.querySelector('#result').hidden = false;
  } catch (error) {
    window.alert(`Couldn't get an estimate. Make sure the MessMind server is running. ${error.message}`);
  } finally {
    button.disabled = false;
    button.innerHTML = originalButtonText;
  }
});

const today = new Date();
today.setMinutes(today.getMinutes() - today.getTimezoneOffset());
document.querySelector('#record-date').value = today.toISOString().slice(0, 10);

document.querySelector('#fill-example').addEventListener('click', () => {
  document.querySelector('#record-date').value = today.toISOString().slice(0, 10);
  document.querySelector('#record-meal').value = 'Lunch';
  document.querySelector('#record-menu').value = 'DEMO: dal, rice, chapati';
  document.querySelector('#record-students').value = 800;
  document.querySelector('#record-served').value = 640;
  document.querySelector('#record-demo').checked = true;
  document.querySelector('#record-message').textContent =
    'Example values filled in. They are fake demo data.';
});

function renderRecords(records) {
  const tableBody = document.querySelector('#records-list');
  tableBody.replaceChildren();

  for (const record of records) {
    const row = document.createElement('tr');
    const dateCell = document.createElement('td');
    dateCell.textContent = record.meal_date;

    const mealCell = document.createElement('td');
    mealCell.textContent = record.meal;
    const menu = document.createElement('div');
    menu.className = 'record-menu';
    menu.textContent = record.menu;
    mealCell.append(menu);

    const totalsCell = document.createElement('td');
    totalsCell.textContent = `${record.meals_served.toLocaleString()} / ${record.students.toLocaleString()}`;

    const typeCell = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = record.is_demo ? 'record-type' : 'record-type real';
    badge.textContent = record.is_demo ? 'DEMO' : 'REAL';
    typeCell.append(badge);

    row.append(dateCell, mealCell, totalsCell, typeCell);
    tableBody.append(row);
  }

  document.querySelector('#records-empty').hidden = records.length > 0;
  document.querySelector('#record-count').textContent =
    `${records.length} ${records.length === 1 ? 'record' : 'records'}`;
}

async function loadRecords() {
  const response = await fetch('/records');
  if (!response.ok) throw new Error('Could not load meal records.');
  renderRecords(await response.json());
}

document.querySelector('#record-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const message = document.querySelector('#record-message');
  const originalButtonText = button.innerHTML;
  const record = {
    meal_date: document.querySelector('#record-date').value,
    meal: document.querySelector('#record-meal').value,
    menu: document.querySelector('#record-menu').value.trim(),
    students: Number(document.querySelector('#record-students').value),
    meals_served: Number(document.querySelector('#record-served').value),
    is_demo: document.querySelector('#record-demo').checked
  };

  button.disabled = true;
  button.textContent = 'Saving…';
  message.textContent = '';
  message.style.color = '';

  try {
    const response = await fetch('/records', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record)
    });
    const savedRecord = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(savedRecord.detail)
        ? 'Please check the date and meal totals.'
        : savedRecord.detail;
      throw new Error(detail || 'Could not save this record.');
    }

    message.textContent = savedRecord.is_demo
      ? 'Demo record saved on this computer. It is not real attendance data.'
      : 'Meal record saved on this computer.';
    await loadRecords();
    form.reset();
    document.querySelector('#record-date').value = today.toISOString().slice(0, 10);
    document.querySelector('#record-demo').checked = true;
  } catch (error) {
    message.textContent = error.message;
    message.style.color = '#a34a3a';
  } finally {
    button.disabled = false;
    button.innerHTML = originalButtonText;
  }
});

loadRecords().catch((error) => {
  document.querySelector('#record-message').textContent = error.message;
});
