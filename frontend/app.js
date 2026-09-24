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
