const date = new Date();
document.querySelector('#today').textContent = new Intl.DateTimeFormat('en', {
  weekday: 'short', month: 'short', day: 'numeric'
}).format(date);

document.querySelector('#meal-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const students = Number(document.querySelector('#students').value);
  const meal = document.querySelector('#meal').value.toLowerCase();
  const menu = document.querySelector('#menu').value.trim();
  // Temporary demo estimate. The backend and ML model will replace this later.
  const estimate = Math.round(students * 0.82);
  document.querySelector('#estimate').textContent = estimate.toLocaleString();
  document.querySelector('#result-detail').textContent =
    `${estimate.toLocaleString()} of ${students.toLocaleString()} students may attend ${meal}${menu ? ` for ${menu}` : ''}.`;
  document.querySelector('#result').hidden = false;
});
