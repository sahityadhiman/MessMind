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
      resultLabel.textContent = 'HISTORICAL ESTIMATE';
      document.querySelector('#result-detail').textContent =
        `${prediction.message} Average attendance: ${(prediction.attendance_rate * 100).toFixed(1)}%.`;
    }
    document.querySelector('#result').hidden = false;
  } catch (error) {
    window.alert(`Couldn't get an estimate. Make sure the MessMind server is running. ${error.message}`);
  } finally {
    button.disabled = false;
    button.innerHTML = originalButtonText;
  }
});
