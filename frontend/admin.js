const recordForm = document.querySelector('#record-form');
const recordDate = document.querySelector('#record-date');
const message = document.querySelector('#record-message');
const tableBody = document.querySelector('#records-list');
const demoCheckbox = document.querySelector('#record-demo');
const demoLabel = document.querySelector('#record-demo-label');
const formTitle = document.querySelector('#records-title');
const submitButton = document.querySelector('#record-submit');
const cancelButton = document.querySelector('#cancel-edit');
const exampleButton = document.querySelector('#fill-example');

let editingRecordId = null;
let savedRecords = [];

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
    const editButton = document.createElement('button');
    editButton.className = 'edit-record';
    editButton.type = 'button';
    editButton.dataset.recordId = record.id;
    editButton.textContent = 'Edit';
    actionCell.append(editButton);

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
  savedRecords = await response.json();
  renderRecords(savedRecords);
}

function resetRecordForm() {
  editingRecordId = null;
  recordForm.reset();
  setToday();
  demoCheckbox.disabled = false;
  demoLabel.textContent = 'Mark this as demo data';
  formTitle.textContent = 'Add a meal record';
  submitButton.innerHTML = 'Save meal record <span aria-hidden="true">→</span>';
  cancelButton.hidden = true;
  exampleButton.hidden = false;
}

function startEditing(record) {
  editingRecordId = record.id;
  recordDate.value = record.meal_date;
  document.querySelector('#record-meal').value = record.meal;
  document.querySelector('#record-menu').value = record.menu;
  document.querySelector('#record-students').value = record.students;
  document.querySelector('#record-served').value = record.meals_served;
  demoCheckbox.checked = record.is_demo;
  demoCheckbox.disabled = true;
  demoLabel.textContent = record.is_demo
    ? 'DEMO type (fixed while editing)'
    : 'REAL type (fixed while editing)';
  formTitle.textContent = 'Correct a meal record';
  submitButton.innerHTML = 'Update meal record <span aria-hidden="true">→</span>';
  cancelButton.hidden = false;
  exampleButton.hidden = true;
  message.textContent = record.is_demo
    ? 'Editing a demo record. It will still be ignored by estimates.'
    : 'Editing a real record. The corrected totals will affect future estimates.';
  message.style.color = '';
  recordForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

exampleButton.addEventListener('click', () => {
  setToday();
  document.querySelector('#record-meal').value = 'Lunch';
  document.querySelector('#record-menu').value = 'DEMO: dal, rice, chapati';
  document.querySelector('#record-students').value = 800;
  document.querySelector('#record-served').value = 640;
  demoCheckbox.checked = true;
  message.textContent = 'Example filled in. These numbers are fake demo data.';
  message.style.color = '';
});

recordForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const editing = editingRecordId !== null;
  const record = {
    meal_date: recordDate.value,
    meal: document.querySelector('#record-meal').value,
    menu: document.querySelector('#record-menu').value.trim(),
    students: Number(document.querySelector('#record-students').value),
    meals_served: Number(document.querySelector('#record-served').value)
  };
  if (!editing) record.is_demo = demoCheckbox.checked;

  submitButton.disabled = true;
  submitButton.textContent = editing ? 'Updating…' : 'Saving…';
  message.textContent = '';
  message.style.color = '';

  try {
    const response = await fetch(editing ? `/records/${editingRecordId}` : '/records', {
      method: editing ? 'PUT' : 'POST',
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

    message.textContent = editing
      ? `${savedRecord.is_demo ? 'Demo' : 'Real'} meal record updated.`
      : savedRecord.is_demo
        ? 'Demo record saved on this server. It will not affect estimates and may reset after a restart.'
        : 'Verified meal record saved. It can affect future estimates.';
    await loadRecords();
    resetRecordForm();
  } catch (error) {
    message.textContent = error.message;
    message.style.color = '#a34a3a';
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = editingRecordId !== null
      ? 'Update meal record <span aria-hidden="true">→</span>'
      : 'Save meal record <span aria-hidden="true">→</span>';
  }
});

cancelButton.addEventListener('click', () => {
  resetRecordForm();
  message.textContent = 'Editing canceled; the saved record was not changed.';
  message.style.color = '';
});

tableBody.addEventListener('click', async (event) => {
  const editButton = event.target.closest('.edit-record');
  if (editButton) {
    const record = savedRecords.find((item) => item.id === Number(editButton.dataset.recordId));
    if (record) startEditing(record);
    return;
  }

  const removeButton = event.target.closest('.remove-record');
  if (!removeButton || !window.confirm('Remove this demo record?')) return;

  message.textContent = '';
  message.style.color = '';
  try {
    const response = await fetch(`/records/${removeButton.dataset.recordId}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('Could not remove that demo record.');
    await loadRecords();
    message.textContent = 'Demo record removed.';
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
