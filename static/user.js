// User page: pick a trip and a preference, ask the server for routes, show them.
const $ = id => document.getElementById(id);
const { pretty, esc } = SafeMap;

const COLORS = { fast: "var(--fast)", bal: "var(--bal)", safe: "var(--safe)", custom: "var(--custom)" };
const LABELS = { fast: "Fastest", bal: "Balanced", safe: "Safest", custom: "Custom" };
const WEIGHTS = { fast: 1, bal: 0.5, safe: 0 };
const API_KEY = { fast: "fastest", bal: "balanced", safe: "safest" };   // names used in the JSON

let mapData = null;      // { locations, roads } from /api/map
let routes = null;       // answer from /api/routes
let state = { from: null, to: null, pref: "bal", custom: 70, view: "pref", nextClick: "from" };
let fittedTrip = "";     // which trip the map is currently zoomed to

const mapView = SafeMap.create($("map"), {
  onNode: id => {
    if (state.nextClick === "from") { state.from = id; state.nextClick = "to"; }
    else { state.to = id; state.nextClick = "from"; }
    state.view = "pref"; loadRoutes();
  },
});

const weight = () => state.pref === "custom" ? state.custom / 100 : WEIGHTS[state.pref];
const name = id => pretty(mapData.locations.find(l => l.id === id).name);

// fetch() sends an HTTP request. The browser includes the login cookie automatically.
async function getJSON(url) {
  const res = await fetch(url);
  if (res.status === 401) { location.href = "/login"; return null; }
  if (!res.ok) throw new Error((await res.json()).error || res.statusText);
  return res.json();
}

async function loadRoutes() {
  routes = await getJSON(`/api/routes?from=${state.from}&to=${state.to}&w=${weight()}`);
  render();
}

function routeStats(r) {
  if (!r.found) return `<p class="note">No road connects these places.</p>`;
  const empty = r.road_ids.length === 0;
  return `<div class="path">${r.path.map(id => `<b>${esc(name(id))}</b>`).join("<i>→</i>")}</div>
    <div class="stats">
      <div class="stat"><span>Time</span><strong>${r.time} min</strong></div>
      <div class="stat"><span>Avg safety</span><strong>${empty ? "—" : r.avg_safety.toFixed(1)}</strong></div>
      <div class="stat"><span>Worst road</span><strong>${empty ? "—" : r.worst_safety + "/10"}</strong></div>
    </div>`;
}

function render() {
  const pct = Math.round(weight() * 100);
  document.querySelectorAll(".seg button").forEach(b => b.setAttribute("aria-pressed", b.dataset.p === state.pref));
  $("w").value = pct;
  $("wLabel").textContent = `${pct}% speed`;
  $("from").value = state.from;
  $("to").value = state.to;
  if (!routes) return;

  const title = state.pref === "custom" ? `Custom: ${pct}% speed, ${100 - pct}% safety` : `${LABELS[state.pref]} route`;
  $("rec").innerHTML = `<div class="rec" style="--rc:${COLORS[state.pref]}"><div class="name">${title}</div>${routeStats(routes.preferred)}</div>`;

  $("cmp").innerHTML = ["fast", "bal", "safe"].map(k => {
    const r = routes[API_KEY[k]];
    const cells = !r.found ? `<td colspan="3">No route</td>`
      : r.road_ids.length === 0 ? `<td>0 min</td><td>—</td><td>—</td>`
      : `<td>${r.time} min</td><td>${r.avg_safety.toFixed(1)}</td><td>${r.worst_safety}</td>`;
    return `<tr class="row${state.view === k ? " on" : ""}" data-k="${k}" tabindex="0">
      <td><span class="dot" style="background:${COLORS[k]}"></span>${LABELS[k]}</td>${cells}</tr>`;
  }).join("");
  $("cmp").querySelectorAll(".row").forEach(tr => {
    const pick = () => { state.view = state.view === tr.dataset.k ? "pref" : tr.dataset.k; render(); };
    tr.onclick = pick;
    tr.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } };
  });

  const f = routes.fastest, s = routes.safest;
  $("insight").textContent = f.found && f.road_ids.length
    ? (f.time === s.time && f.avg_safety === s.avg_safety ? "The fastest route is also the safest for this trip."
       : `The safest route takes ${s.time - f.time} min longer than the fastest and raises average safety from ${f.avg_safety.toFixed(1)} to ${s.avg_safety.toFixed(1)}.`)
    : "";

  const shown = state.view === "pref" ? routes.preferred : routes[API_KEY[state.view]];
  mapView.draw(mapData, {
    routeRoads: shown.found ? shown.road_ids : [],
    routeColor: state.view === "pref" ? COLORS[state.pref] : COLORS[state.view],
    from: state.from, to: state.to,
  });
  // When the trip changes, zoom to the route. Changing only the preference keeps the view.
  const trip = `${state.from}-${state.to}`;
  if (trip !== fittedTrip && shown.found && shown.road_ids.length) { mapView.fitRoads(shown.road_ids, 13); fittedTrip = trip; }
  const label = state.view === "pref" ? "recommended" : LABELS[state.view].toLowerCase();
  $("hint").innerHTML = `Showing the <b>${label}</b> route. Click a place to set the <b>${state.nextClick === "from" ? "start" : "destination"}</b>.`;
}

function change(patch) { Object.assign(state, patch, { view: "pref" }); loadRoutes(); }

$("from").onchange = () => change({ from: +$("from").value });
$("to").onchange = () => change({ to: +$("to").value });
$("swap").onclick = () => change({ from: state.to, to: state.from });
document.querySelectorAll(".seg button").forEach(b => b.onclick = () => change({ pref: b.dataset.p }));
$("w").oninput = () => change({ pref: "custom", custom: +$("w").value });

(async function start() {
  mapData = await getJSON("/api/map");
  if (!mapData) return;
  const options = mapData.locations.map(l => `<option value="${l.id}">${esc(pretty(l.name))}</option>`).join("");
  $("from").innerHTML = $("to").innerHTML = options;
  // Default demo trip: each preference gives a different route here.
  const byName = n => (mapData.locations.find(l => l.name === n) || {}).id;
  state.from = byName("Mumbai Central") ?? mapData.locations[0].id;
  state.to = byName("Andheri") ?? mapData.locations[mapData.locations.length - 1].id;
  loadRoutes();
})();
