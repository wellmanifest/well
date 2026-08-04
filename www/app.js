const health = document.querySelector('#health');
const sourceText = document.querySelector('#sourceText');
const outputText = document.querySelector('#outputText');
const sourceDialect = document.querySelector('#sourceDialect');
const targetDialect = document.querySelector('#targetDialect');
const diagnostics = document.querySelector('#diagnostics');
const convertButton = document.querySelector('#convertButton');

async function checkHealth() {
  try {
    const response = await fetch('/healthz', {headers: {'accept': 'application/json'}});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    health.textContent = `runtime ${data.version}: online`;
    health.className = 'health ok';
  } catch (error) {
    health.textContent = 'runtime: offline demo';
    health.className = 'health error';
  }
}

function renderDiagnostics(items = [], fallback = 'Conversion complete.') {
  if (!items.length) {
    diagnostics.innerHTML = `<span class="info">INFO</span> ${fallback}`;
    return;
  }
  diagnostics.textContent = '';
  for (const item of items) {
    const line = document.createElement('div');
    const severity = String(item.severity || 'INFO').toLowerCase();
    const badge = document.createElement('span');
    badge.className = severity;
    badge.textContent = String(item.severity || 'INFO');
    line.append(badge, document.createTextNode(` ${item.code || 'WM'} — ${item.message || ''}`));
    diagnostics.append(line);
  }
}

async function convert() {
  convertButton.disabled = true;
  convertButton.textContent = '…';
  diagnostics.innerHTML = '<span class="info">INFO</span> Contacting runtime…';
  try {
    const response = await fetch('/v1/convert', {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({
        source: sourceText.value,
        source_dialect: sourceDialect.value,
        target_dialect: targetDialect.value,
        projection: 'data',
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail?.message || `HTTP ${response.status}`);
    outputText.value = data.output ?? JSON.stringify(data, null, 2);
    renderDiagnostics(data.diagnostics, `${data.quality || 'NORMALIZED'} conversion complete.`);
  } catch (error) {
    outputText.value = 'The static page is available, but the WellManifest API is not reachable.\n\nStart it with:\n  wellmanifest serve\nor:\n  docker compose up --build runtime';
    diagnostics.innerHTML = `<span class="error">ERROR</span> ${String(error.message || error)}`;
  } finally {
    convertButton.disabled = false;
    convertButton.textContent = '⇄';
  }
}

convertButton.addEventListener('click', convert);
checkHealth();
