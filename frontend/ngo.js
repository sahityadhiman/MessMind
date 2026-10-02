const partnerForm = document.querySelector('#partner-form');
const partnerList = document.querySelector('#partner-list');
const partnerMessage = document.querySelector('#partner-message');
const offerForm = document.querySelector('#offer-form');
const offerList = document.querySelector('#offer-list');
const offerMessage = document.querySelector('#offer-message');
const partnerSelect = document.querySelector('#offer-partner');
const offerSubmit = document.querySelector('#offer-submit');
const safeCheckbox = document.querySelector('#safe-unserved-confirmed');

let partners = [];
let offers = [];

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

function setMessage(element, text, isError = false) {
  element.textContent = text;
  element.style.color = isError ? '#a34a3a' : '';
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers
    }
  });
  let body = {};
  try {
    body = response.status === 204 ? {} : await response.json();
  } catch {
    body = {};
  }
  if (!response.ok) {
    const message = Array.isArray(body.detail)
      ? 'Please check the entered values.'
      : body.detail;
    throw new Error(message || `Request failed (${response.status}).`);
  }
  return body;
}

function renderPartners() {
  partnerList.replaceChildren();
  const active = partners.filter((partner) => partner.status === 'active');
  document.querySelector('#active-partner-count').textContent = `${active.length} active`;

  partnerSelect.replaceChildren();
  if (active.length) {
    partnerSelect.add(new Option('Choose an approved partner', ''));
    for (const partner of active) {
      partnerSelect.add(new Option(`${partner.organization_name} · ${partner.service_area}`, String(partner.id)));
    }
  } else {
    partnerSelect.add(new Option('No active partner yet', ''));
  }
  partnerSelect.disabled = active.length === 0;
  offerSubmit.disabled = active.length === 0 || !safeCheckbox.checked;

  for (const partner of partners) {
    const card = document.createElement('article');
    card.className = 'ngo-entry';
    const heading = document.createElement('div');
    heading.className = 'ngo-entry-heading';
    const name = document.createElement('h3');
    name.textContent = partner.organization_name;
    const badge = document.createElement('span');
    badge.className = `ngo-status status-${partner.status}`;
    badge.textContent = partner.status.replaceAll('_', ' ');
    heading.append(name, badge);

    const detail = document.createElement('p');
    const contact = [partner.contact_person, partner.contact_phone, partner.contact_email].filter(Boolean).join(' · ');
    detail.textContent = [partner.service_area, contact, partner.accepted_food_notes].filter(Boolean).join(' · ');
    card.append(heading, detail);

    const actions = document.createElement('div');
    actions.className = 'ngo-entry-actions';
    if (partner.status !== 'active') {
      const action = document.createElement('button');
      action.className = 'secondary-button';
      action.type = 'button';
      action.textContent = partner.status === 'pending_approval' ? 'Approve and activate' : 'Reactivate';
      action.addEventListener('click', async () => {
        const approved = window.confirm(
          'Activate this NGO only after the college has approved the partnership, contact, and safe pickup arrangements. This will not send a message.'
        );
        if (!approved) return;
        try {
          await api(`/ngo/partners/${partner.id}/status`, {
            method: 'PATCH', body: JSON.stringify({ status: 'active' })
          });
          setMessage(partnerMessage, 'Partner is active. Contact the NGO directly to coordinate; MessMind sent no notification.');
          await loadPartners();
        } catch (error) {
          setMessage(partnerMessage, error.message, true);
        }
      });
      actions.append(action);
    } else {
      const action = document.createElement('button');
      action.className = 'secondary-button';
      action.type = 'button';
      action.textContent = 'Pause partner';
      action.addEventListener('click', async () => {
        try {
          await api(`/ngo/partners/${partner.id}/status`, {
            method: 'PATCH', body: JSON.stringify({ status: 'paused' })
          });
          await loadPartners();
          setMessage(partnerMessage, 'Partner paused. Existing offer history was retained.');
        } catch (error) {
          setMessage(partnerMessage, error.message, true);
        }
      });
      actions.append(action);
    }
    card.append(actions);
    partnerList.append(card);
  }
  document.querySelector('#partners-empty').hidden = partners.length > 0;
  document.querySelector('#ngo-setup-title').textContent = active.length
    ? `${active.length} approved partner${active.length === 1 ? '' : 's'} available`
    : 'Partner setup is pending';
  document.querySelector('#ngo-setup-message').textContent = active.length
    ? 'Only staff-confirmed, safe, untouched surplus can be recorded. Contact partners directly; MessMind does not send messages or confirm pickup automatically.'
    : 'Add an NGO only after the college confirms the partnership and pickup process. MessMind does not send NGO notifications yet; staff must contact the partner directly.';
}

function addDetail(parent, label, value) {
  const item = document.createElement('div');
  item.className = 'ngo-detail';
  const key = document.createElement('span');
  key.textContent = label;
  const text = document.createElement('strong');
  text.textContent = value;
  item.append(key, text);
  parent.append(item);
}

function createActionButton(label, action) {
  const button = document.createElement('button');
  button.className = 'secondary-button';
  button.type = 'button';
  button.textContent = label;
  button.addEventListener('click', action);
  return button;
}

async function updateOffer(offer, payload) {
  try {
    await api(`/ngo/offers/${offer.id}/status`, {
      method: 'PATCH', body: JSON.stringify(payload)
    });
    setMessage(offerMessage, 'Offer history updated.');
    await loadOffers();
  } catch (error) {
    setMessage(offerMessage, error.message, true);
  }
}

function renderOfferActions(offer, actions) {
  if (offer.status === 'pending_contact' && !offer.is_expired) {
    actions.append(createActionButton('Mark accepted', () => {
      if (!window.confirm('Has the NGO directly confirmed that it can collect this food before the safe-consumption deadline?')) return;
      updateOffer(offer, { status: 'accepted', note: 'Acceptance confirmed by staff after direct contact.' });
    }));
    actions.append(createActionButton('Mark declined', () => {
      updateOffer(offer, { status: 'declined', note: 'NGO declined after direct contact.' });
    }));
    actions.append(createActionButton('Cancel offer', () => {
      if (!window.confirm('Cancel this surplus offer?')) return;
      updateOffer(offer, { status: 'cancelled', note: 'Cancelled by mess staff.' });
    }));
  } else if (offer.status === 'accepted' && !offer.is_expired) {
    const collection = document.createElement('form');
    collection.className = 'ngo-transition-form';
    const quantityLabel = document.createElement('label');
    quantityLabel.textContent = 'Collected (kg)';
    const quantity = document.createElement('input');
    quantity.type = 'number';
    quantity.min = '0.1';
    quantity.max = String(offer.offered_quantity_kg);
    quantity.step = '0.1';
    quantity.value = String(offer.offered_quantity_kg);
    quantity.required = true;
    const tempLabel = document.createElement('label');
    tempLabel.textContent = 'Pickup temperature (°C)';
    const temperature = document.createElement('input');
    temperature.type = 'number';
    temperature.min = '-50';
    temperature.max = '100';
    temperature.step = '0.1';
    temperature.required = true;
    const safetyLabel = document.createElement('label');
    safetyLabel.className = 'ngo-confirm';
    const safety = document.createElement('input');
    safety.type = 'checkbox';
    safety.required = true;
    const safetyText = document.createElement('span');
    safetyText.textContent = 'I verified the food still meets the college-approved safe-handling rules at pickup.';
    safetyLabel.append(safety, safetyText);
    const button = document.createElement('button');
    button.className = 'secondary-button';
    button.type = 'submit';
    button.textContent = 'Record pickup';
    collection.addEventListener('submit', (event) => {
      event.preventDefault();
      updateOffer(offer, {
        status: 'collected',
        collected_quantity_kg: Number(quantity.value),
        pickup_temperature_c: Number(temperature.value),
        pickup_safe_confirmed: safety.checked,
        note: 'Pickup confirmed by mess staff.'
      });
    });
    collection.append(quantityLabel, quantity, tempLabel, temperature, safetyLabel, button);
    actions.append(collection);
    actions.append(createActionButton('Cancel offer', () => {
      if (!window.confirm('Cancel this accepted pickup?')) return;
      updateOffer(offer, { status: 'cancelled', note: 'Pickup cancelled by mess staff.' });
    }));
  } else if (offer.status === 'collected') {
    const distribution = document.createElement('form');
    distribution.className = 'ngo-transition-form';
    const quantityLabel = document.createElement('label');
    quantityLabel.textContent = 'Distributed (kg)';
    const quantity = document.createElement('input');
    quantity.type = 'number';
    quantity.min = '0.1';
    quantity.max = String(offer.collected_quantity_kg);
    quantity.step = '0.1';
    quantity.value = String(offer.collected_quantity_kg);
    quantity.required = true;
    const areaLabel = document.createElement('label');
    areaLabel.textContent = 'Distribution area';
    const area = document.createElement('input');
    area.maxLength = 200;
    area.required = true;
    const button = document.createElement('button');
    button.className = 'secondary-button';
    button.type = 'submit';
    button.textContent = 'Record distribution';
    distribution.addEventListener('submit', (event) => {
      event.preventDefault();
      updateOffer(offer, {
        status: 'distributed',
        distributed_quantity_kg: Number(quantity.value),
        distribution_area: area.value.trim(),
        note: 'Distribution confirmed by staff after partner follow-up.'
      });
    });
    distribution.append(quantityLabel, quantity, areaLabel, area, button);
    actions.append(distribution);
  } else if (offer.is_expired) {
    actions.append(createActionButton('Close expired offer', () => {
      updateOffer(offer, { status: 'cancelled', note: 'Safe-consumption deadline passed before collection.' });
    }));
  }
}

function renderOffers() {
  offerList.replaceChildren();
  const awaitingPickup = offers.filter((offer) => ['pending_contact', 'accepted'].includes(offer.status) && !offer.is_expired).length;
  const distributedKg = offers.reduce((sum, offer) => sum + Number(offer.distributed_quantity_kg || 0), 0);
  document.querySelector('#ngo-offer-count').textContent = String(offers.length);
  document.querySelector('#ngo-pending-count').textContent = String(awaitingPickup);
  document.querySelector('#ngo-distributed-kg').textContent = distributedKg.toLocaleString(undefined, { maximumFractionDigits: 1 });
  for (const offer of offers) {
    const card = document.createElement('article');
    card.className = 'ngo-entry ngo-offer-entry';
    const heading = document.createElement('div');
    heading.className = 'ngo-entry-heading';
    const name = document.createElement('h3');
    name.textContent = `${offer.food_description} · ${offer.meal}`;
    const badge = document.createElement('span');
    badge.className = `ngo-status status-${offer.status}`;
    badge.textContent = offer.status.replaceAll('_', ' ');
    heading.append(name, badge);
    card.append(heading);

    const facts = document.createElement('div');
    facts.className = 'ngo-details-grid';
    addDetail(facts, 'Partner', offer.partner_name);
    addDetail(facts, 'Donor / pickup', `${offer.donor_name} · ${offer.pickup_location}`);
    addDetail(facts, 'Date / meal', `${offer.meal_date} · ${offer.meal}`);
    addDetail(facts, 'Offered', `${Number(offer.offered_quantity_kg).toFixed(1)} kg · ${offer.food_category.replaceAll('_', ' ')}`);
    addDetail(facts, 'Safe to consume by', new Date(offer.consume_by).toLocaleString());
    addDetail(facts, 'Prepared / stored at', `${new Date(offer.prepared_at).toLocaleString()} · ${offer.storage_temperature_c} °C`);
    if (offer.collected_quantity_kg != null) addDetail(facts, 'Collected', `${Number(offer.collected_quantity_kg).toFixed(1)} kg · ${offer.pickup_temperature_c} °C at pickup`);
    if (offer.distributed_quantity_kg != null) addDetail(facts, 'Distributed', `${Number(offer.distributed_quantity_kg).toFixed(1)} kg · ${offer.distribution_area}`);
    if (offer.allergen_notes) addDetail(facts, 'Allergens', offer.allergen_notes);
    if (offer.handling_notes) addDetail(facts, 'Handling', offer.handling_notes);
    if (offer.batch_reference) addDetail(facts, 'Batch reference', offer.batch_reference);
    card.append(facts);

    if (offer.events?.length) {
      const history = document.createElement('details');
      history.className = 'ngo-event-history';
      const summary = document.createElement('summary');
      summary.textContent = 'Handover history';
      const list = document.createElement('ul');
      for (const event of offer.events) {
        const item = document.createElement('li');
        const eventText = [event.status.replaceAll('_', ' '), event.note, event.quantity_kg == null ? '' : `${event.quantity_kg} kg`, event.temperature_c == null ? '' : `${event.temperature_c} °C`, event.distribution_area || ''].filter(Boolean).join(' · ');
        item.textContent = `${new Date(event.created_at).toLocaleString()} — ${eventText} · by ${event.recorded_by}`;
        list.append(item);
      }
      history.append(summary, list);
      card.append(history);
    }

    const actions = document.createElement('div');
    actions.className = 'ngo-entry-actions ngo-offer-actions';
    renderOfferActions(offer, actions);
    if (actions.childElementCount) card.append(actions);
    offerList.append(card);
  }
  document.querySelector('#offers-empty').hidden = offers.length > 0;
}

async function loadPartners() {
  partners = await api('/ngo/partners');
  renderPartners();
}

async function loadOffers() {
  offers = await api('/ngo/offers');
  renderOffers();
}

partnerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const values = new FormData(partnerForm);
  const payload = Object.fromEntries(values.entries());
  payload.contact_person ||= null;
  payload.contact_phone ||= null;
  payload.contact_email ||= null;
  payload.accepted_food_notes ||= null;
  const button = document.querySelector('#partner-submit');
  button.disabled = true;
  setMessage(partnerMessage, 'Saving partner…');
  try {
    await api('/ngo/partners', { method: 'POST', body: JSON.stringify(payload) });
    partnerForm.reset();
    setMessage(partnerMessage, 'Partner saved as pending approval. Nothing was sent to the NGO.');
    await loadPartners();
  } catch (error) {
    setMessage(partnerMessage, error.message, true);
  } finally {
    button.disabled = false;
  }
});

safeCheckbox.addEventListener('change', () => {
  offerSubmit.disabled = partners.every((partner) => partner.status !== 'active') || !safeCheckbox.checked;
});

offerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const values = new FormData(offerForm);
  const payload = {
    partner_id: Number(values.get('partner_id')),
    donor_name: String(values.get('donor_name')).trim(),
    pickup_location: String(values.get('pickup_location')).trim(),
    batch_reference: String(values.get('batch_reference')).trim() || null,
    meal_date: values.get('meal_date'),
    meal: values.get('meal'),
    food_description: String(values.get('food_description')).trim(),
    food_category: values.get('food_category'),
    offered_quantity_kg: Number(values.get('offered_quantity_kg')),
    prepared_at: new Date(values.get('prepared_at')).toISOString(),
    consume_by: new Date(values.get('consume_by')).toISOString(),
    storage_temperature_c: Number(values.get('storage_temperature_c')),
    allergen_notes: String(values.get('allergen_notes')).trim() || null,
    handling_notes: String(values.get('handling_notes')).trim() || null,
    safe_unserved_confirmed: safeCheckbox.checked
  };
  offerSubmit.disabled = true;
  setMessage(offerMessage, 'Recording offer…');
  try {
    await api('/ngo/offers', { method: 'POST', body: JSON.stringify(payload) });
    const meal = payload.meal;
    offerForm.reset();
    document.querySelector('#offer-meal').value = meal;
    resetOfferDefaults();
    setMessage(offerMessage, 'Offer recorded. Contact the NGO directly and update its status after you hear back.');
    await Promise.all([loadPartners(), loadOffers()]);
  } catch (error) {
    setMessage(offerMessage, error.message, true);
  } finally {
    offerSubmit.disabled = partners.every((partner) => partner.status !== 'active') || !safeCheckbox.checked;
  }
});

document.querySelector('#refresh-ngo').addEventListener('click', async () => {
  try {
    await Promise.all([loadPartners(), loadOffers()]);
    setMessage(offerMessage, 'Partner and offer lists refreshed.');
  } catch (error) {
    setMessage(offerMessage, error.message, true);
  }
});

async function loadPage() {
  try {
    await Promise.all([loadPartners(), loadOffers()]);
  } catch (error) {
    document.querySelector('#ngo-setup-title').textContent = 'NGO Connect is not enabled';
    document.querySelector('#ngo-setup-message').textContent = error.message;
    setMessage(partnerMessage, error.message, true);
    setMessage(offerMessage, error.message, true);
  }
}

function localDateTimeValue(value) {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

const dateInput = document.querySelector('#offer-date');
function resetOfferDefaults() {
  const now = new Date();
  dateInput.value = localDateTimeValue(now).slice(0, 10);
  document.querySelector('#offer-prepared').value = localDateTimeValue(now);
}
resetOfferDefaults();

const estimationContext = new URLSearchParams(window.location.search);
const contextMealDate = estimationContext.get('meal_date');
const contextMeal = estimationContext.get('meal');
const allowedMeals = new Set(['Breakfast', 'Lunch', 'Snacks', 'Dinner']);
let contextCopied = false;
if (contextMealDate && /^\d{4}-\d{2}-\d{2}$/.test(contextMealDate)) {
  const parsedDate = new Date(`${contextMealDate}T00:00:00Z`);
  if (!Number.isNaN(parsedDate.getTime()) && parsedDate.toISOString().slice(0, 10) === contextMealDate) {
    dateInput.value = contextMealDate;
    contextCopied = true;
  }
}
if (contextMeal && allowedMeals.has(contextMeal)) {
  document.querySelector('#offer-meal').value = contextMeal;
  contextCopied = true;
}
if (contextCopied) {
  setMessage(offerMessage, 'Meal and date copied from Real Estimation. Enter actual safe surplus only; nothing has been offered yet.');
}
loadPage();
