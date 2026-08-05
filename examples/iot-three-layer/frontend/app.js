async function refresh() {
  const health = await fetch('/api/healthz').then((r) => r.json());
  const payload = await fetch('/api/v1/events?limit=200').then((r) => r.json());
  const telemetry = (payload.events || []).filter((event) => event.type === 'TelemetryReceived');
  const healthNode = document.querySelector('#health');
  healthNode.textContent = health.status;
  healthNode.className = 'metric ok';
  document.querySelector('#count').textContent = String(telemetry.length);
  document.querySelector('#event').textContent = telemetry.length
    ? JSON.stringify(telemetry.at(-1), null, 2)
    : 'Brak telemetrii.';
}
refresh().catch((error) => { document.querySelector('#health').textContent = error.message; });
setInterval(() => refresh().catch(() => {}), 2000);
