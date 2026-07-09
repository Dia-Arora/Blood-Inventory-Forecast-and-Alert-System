const API_BASE = 'http://localhost:8000';

export async function fetchSimulation(days = 30) {
  const res = await fetch(`${API_BASE}/api/simulate?days=${days}`);
  if (!res.ok) {
    throw new Error(`Simulate request failed with status ${res.status}`);
  }
  const json = await res.json();
  if (json.status !== 'success') {
    throw new Error(json.detail || 'Simulate request returned an error');
  }
  return json.data;
}

export async function fetchBacktest() {
  const res = await fetch(`${API_BASE}/api/backtest`);
  if (!res.ok) {
    throw new Error(`Backtest request failed with status ${res.status}`);
  }
  const json = await res.json();
  if (json.status !== 'success') {
    throw new Error(json.detail || 'Backtest request returned an error');
  }
  return json.data;
}
