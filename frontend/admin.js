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
const csvImportForm = document.querySelector('#csv-import-form');
const csvFileInput = document.querySelector('#csv-file');
const csvConfirm = document.querySelector('#csv-confirm-real');
const csvImportButton = document.querySelector('#csv-import-button');
const csvImportMessage = document.querySelector('#csv-import-message');
let previewedCsvFile = null;
let previewedCsv = null;

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

    const preparedCell = document.createElement('td');
    preparedCell.textContent = record.prepared_portions == null
      ? '—'
      : record.prepared_portions.toLocaleString();

    const wasteCell = document.createElement('td');
    wasteCell.textContent = record.food_waste_kg == null
      ? '—'
      : Number(record.food_waste_kg).toLocaleString(undefined, { maximumFractionDigits: 1 });

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

    row.append(dateCell, mealCell, totalsCell, preparedCell, wasteCell, typeCell, actionCell);
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

async function loadReadiness() {
  const response = await fetch('/model/readiness');
  if (!response.ok) throw new Error('Could not load model readiness. Check staff sign-in.');
  const readiness = await response.json();
  const modelTarget = readiness.minimum_records_for_validated_model;
  const attendancePercent = Math.min(100, readiness.real_attendance_records / modelTarget * 100);
  const wastePercent = Math.min(100, readiness.measured_waste_records / modelTarget * 100);
  const attendanceBar = document.querySelector('#attendance-progress');
  const wasteBar = document.querySelector('#waste-progress');
  attendanceBar.style.setProperty('--progress', `${attendancePercent}%`);
  wasteBar.style.setProperty('--progress', `${wastePercent}%`);
  attendanceBar.setAttribute('aria-valuenow', String(Math.round(attendancePercent)));
  wasteBar.setAttribute('aria-valuenow', String(Math.round(wastePercent)));
  document.querySelector('#readiness-message').textContent =
    `Attendance: ${readiness.real_attendance_records}/${modelTarget} non-demo records. ` +
    `Measured waste: ${readiness.measured_waste_records}/${modelTarget}. ` +
    `A same-meal average starts after ${readiness.minimum_meal_history_for_average} matching records. ` +
    `The model checks up to the latest ${readiness.model_history_limit} records; demo rows never count.`;
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

function resetCsvPreview() {
  previewedCsvFile = null;
  previewedCsv = null;
  csvConfirm.checked = false;
  csvImportButton.disabled = true;
  document.querySelector('#csv-preview-panel').hidden = true;
  csvImportMessage.textContent = '';
  csvImportMessage.style.color = '';
}

function renderCsvPreview(preview) {
  const previewRows = document.querySelector('#csv-preview-rows');
  previewRows.replaceChildren();
  document.querySelector('#csv-preview-summary').textContent =
    `${preview.row_count.toLocaleString()} rows passed validation. The preview below shows up to the first 10; all rows will be imported together.`;
  for (const record of preview.preview) {
    const row = document.createElement('tr');
    const values = [
      record.meal_date,
      `${record.meal} — ${record.menu}`,
      `${record.meals_served.toLocaleString()} / ${record.students.toLocaleString()}`,
      record.prepared_portions == null ? '—' : record.prepared_portions.toLocaleString(),
      record.food_waste_kg == null ? '—' : Number(record.food_waste_kg).toLocaleString(undefined, { maximumFractionDigits: 1 })
    ];
    for (const value of values) {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.append(cell);
    }
    previewRows.append(row);
  }
  document.querySelector('#csv-preview-panel').hidden = false;
}

function apiErrorMessage(body, fallback) {
  if (Array.isArray(body.detail?.errors)) {
    return `${body.detail.message || fallback} ${body.detail.errors.join(' ')}`;
  }
  return typeof body.detail === 'string' ? body.detail : fallback;
}

csvFileInput.addEventListener('change', resetCsvPreview);
csvConfirm.addEventListener('change', () => {
  csvImportButton.disabled = !csvConfirm.checked || previewedCsvFile !== csvFileInput.files[0];
});

csvImportForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = csvFileInput.files[0];
  if (!file) return;
  resetCsvPreview();
  const previewButton = document.querySelector('#csv-preview-button');
  previewButton.disabled = true;
  previewButton.textContent = 'Checking…';
  csvImportMessage.textContent = 'Checking the file. Nothing will be saved yet.';
  try {
    const response = await fetch('/records/import/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'text/csv; charset=utf-8' },
      body: file
    });
    const result = await response.json();
    if (!response.ok) throw new Error(apiErrorMessage(result, 'CSV preview failed.'));
    previewedCsvFile = file;
    previewedCsv = result;
    renderCsvPreview(result);
    csvImportMessage.textContent = 'Preview passed. Confirm the file contents below to import.';
  } catch (error) {
    csvImportMessage.textContent = error.message;
    csvImportMessage.style.color = '#a34a3a';
  } finally {
    previewButton.disabled = false;
    previewButton.textContent = 'Preview CSV';
  }
});

csvImportButton.addEventListener('click', async () => {
  const file = csvFileInput.files[0];
  if (!file || file !== previewedCsvFile || !previewedCsv || !csvConfirm.checked) return;
  csvImportButton.disabled = true;
  csvImportButton.textContent = 'Importing…';
  csvImportMessage.textContent = 'Saving the validated rows together…';
  csvImportMessage.style.color = '';
  try {
    const response = await fetch('/records/import', {
      method: 'POST',
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'X-MessMind-Confirm-Real-Data': 'yes'
      },
      body: file
    });
    const result = await response.json();
    if (!response.ok) throw new Error(apiErrorMessage(result, 'CSV import failed.'));
    csvFileInput.value = '';
    resetCsvPreview();
    csvImportMessage.textContent = `Imported ${result.imported_rows.toLocaleString()} real meal records. The uploaded file was not stored.`;
    csvImportMessage.style.color = '';
    await loadRecords();
    await loadReadiness();
  } catch (error) {
    csvImportMessage.textContent = error.message;
    csvImportMessage.style.color = '#a34a3a';
  } finally {
    csvImportButton.textContent = 'Import all real records';
    csvImportButton.disabled = !csvConfirm.checked || previewedCsvFile !== csvFileInput.files[0];
  }
});

function startEditing(record) {
  editingRecordId = record.id;
  recordDate.value = record.meal_date;
  document.querySelector('#record-meal').value = record.meal;
  document.querySelector('#record-menu').value = record.menu;
  document.querySelector('#record-students').value = record.students;
  document.querySelector('#record-served').value = record.meals_served;
  document.querySelector('#record-prepared').value = record.prepared_portions ?? '';
  document.querySelector('#record-waste').value = record.food_waste_kg ?? '';
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
  document.querySelector('#record-prepared').value = 690;
  document.querySelector('#record-waste').value = 42.5;
  demoCheckbox.checked = true;
  message.textContent = 'Example filled in. Every value here is fake demo data.';
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
    meals_served: Number(document.querySelector('#record-served').value),
    prepared_portions: document.querySelector('#record-prepared').value === ''
      ? null
      : Number(document.querySelector('#record-prepared').value),
    food_waste_kg: document.querySelector('#record-waste').value === ''
      ? null
      : Number(document.querySelector('#record-waste').value)
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
        ? 'Demo record saved. It will not affect estimates.'
        : 'Verified meal record saved. It can affect future estimates.';
    await loadRecords();
    await loadReadiness();
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
loadReadiness().catch((error) => {
  document.querySelector('#readiness-message').textContent = error.message;
});
