const recordDate = document.querySelector('#record-date');
const message = document.querySelector('#record-message');
const tableBody = document.querySelector('#records-list');

function setToday() {
  const localDate = new Date();
  localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
  recordDate.value = localDate.toISOString().slice(0, 10);
}

function renderRecords(records) {
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

    const actionCell = document.createElement('td');
    if (record.is_demo) {
      const removeButton = document.createElement('button');
      removeButton.className = 'remove-record';
      removeButton.type = 'button';
      removeButton.dataset.recordId = record.id;
      removeButton.textContent = 'Remove';
      actionCell.append(removeButton);
    }

    row.append(dateCell, mealCell, totalsCell, typeCell, actionCell);
    tableBody.append(row);
  }

  document.querySelector('#records-empty').hidden = records.length > 0;
  document.querySelector('#record-count').textContent =
    `${records.length} ${records.length === 1 ? 'record' : 'records'}`;
}

async function loadRecords() {
  const response = await fetch('/records');
  if (!response.ok) throw new Error('Could not load meal records. Check staff sign-in.');
  renderRecords(await response.json());
}

document.querySelector('#fill-example').addEventListener('click', () => {
  setToday();
  document.querySelector('#record-meal').value = 'Lunch';
  document.querySelector('#record-menu').value = 'DEMO: dal, rice, chapati';
  document.querySelector('#record-students').value = 800;
  document.querySelector('#record-served').value = 640;
  document.querySelector('#record-demo').checked = true;
  message.textContent = 'Example filled in. These numbers are fake demo data.';
  message.style.color = '';
});

document.querySelector('#record-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const originalButtonText = button.innerHTML;
  const record = {
    meal_date: recordDate.value,
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
      ? 'Demo record saved locally. It will not affect estimates.'
      : 'Verified meal record saved locally. It can affect future estimates.';
    await loadRecords();
    form.reset();
    setToday();
  } catch (error) {
    message.textContent = error.message;
    message.style.color = '#a34a3a';
  } finally {
    button.disabled = false;
    button.innerHTML = originalButtonText;
  }
});

tableBody.addEventListener('click', async (event) => {
  const button = event.target.closest('.remove-record');
  if (!button || !window.confirm('Remove this demo record from this computer?')) return;

  message.textContent = '';
  message.style.color = '';
  try {
    const response = await fetch(`/records/${button.dataset.recordId}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('Could not remove that demo record.');
    await loadRecords();
    message.textContent = 'Demo record removed locally.';
  } catch (error) {
    message.textContent = error.message;
    message.style.color = '#a34a3a';
  }
});

setToday();
loadRecords().catch((error) => {
  message.textContent = error.message;
  message.style.color = '#a34a3a';
});
