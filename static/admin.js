// Admin page: edit each road's time and safety, save with PUT /api/roads/<id>.
const $ = id => document.getElementById(id);
const { pretty, safetyColor, esc } = SafeMap;

let mapData = null;
let selected = null;
const mapView = SafeMap.create($("map"), { onRoad: id => select(id, true) });

function say(text, isError = false) {
  $("msg").textContent = text;
  $("msg").className = isError ? "msg err" : "msg";
}

async function loadMap() {
  const res = await fetch("/api/map");
  if (res.status === 401) { location.href = "/login"; return; }
  mapData = await res.json();
  render();
}

function roadName(r) {
  const n = id => pretty(mapData.locations.find(l => l.id === id).name);
  return `${n(r.from_id)} – ${n(r.to_id)}`;
}

function render() {
  $("roads").innerHTML = mapData.roads.map(r => `
    <tr data-id="${r.id}" class="${r.id === selected ? "sel" : ""}">
      <td><b>${esc(r.name)}</b><br><span class="when">${esc(roadName(r))} · ${r.km} km</span></td>
      <td><input type="number" id="time-${r.id}" min="1" max="999" value="${r.time}" aria-label="Time for ${esc(roadName(r))}"></td>
      <td><input type="number" id="safety-${r.id}" min="1" max="10" value="${r.safety}" aria-label="Safety for ${esc(roadName(r))}">
        <span class="dot" style="background:${safetyColor(r.safety)};margin-left:6px"></span></td>
      <td class="when">${r.updated_by ? `${esc(r.updated_by)}<br>${esc(r.updated_at)} UTC` : "Original"}</td>
      <td><button class="btn save" disabled>Save</button></td>
    </tr>`).join("");

  $("roads").querySelectorAll("tr").forEach(tr => {
    const id = +tr.dataset.id;
    const road = mapData.roads.find(r => r.id === id);
    const btn = tr.querySelector(".save");
    const inputs = tr.querySelectorAll("input");
    // Enable Save only when a value differs from what is stored.
    inputs.forEach(inp => {
      inp.oninput = () => {
        btn.disabled = +$(`time-${id}`).value === road.time && +$(`safety-${id}`).value === road.safety;
      };
      inp.onkeydown = e => { if (e.key === "Enter" && !btn.disabled) btn.click(); };
      inp.onfocus = () => select(id, false);
    });
    btn.onclick = () => saveRoad(id);
  });

  mapView.draw(mapData, { selectedRoad: selected });
}

function select(id, focus) {
  if (selected === id) return;
  selected = id;
  document.querySelectorAll("#roads tr").forEach(tr => tr.classList.toggle("sel", +tr.dataset.id === id));
  mapView.draw(mapData, { selectedRoad: selected });
  if (!focus) mapView.fitRoads([id], 14);   // picked from the table: show it on the map
  if (focus) {
    const inp = $(`safety-${id}`);
    inp.scrollIntoView({ block: "nearest", behavior: "smooth" });
    inp.focus();
  }
}

async function saveRoad(id) {
  const body = { time: Number($(`time-${id}`).value), safety: Number($(`safety-${id}`).value) };
  const res = await fetch(`/api/roads/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) { say(data.error, true); return; }
  say(`Saved ${mapData.roads.find(r => r.id === id).name} (${roadName(mapData.roads.find(r => r.id === id))}).`);
  loadMap();
}

$("reset").onclick = async () => {
  if (!confirm("Put every road back to the original Mumbai values? Your changes will be lost.")) return;
  const res = await fetch("/api/roads/reset", { method: "POST" });
  if (!res.ok) { say("Reset failed.", true); return; }
  selected = null;
  say("Demo map restored.");
  loadMap();
};

loadMap();
