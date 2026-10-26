// Shared map code used by both the user page and the admin page.
// It uses Leaflet (https://leafletjs.com), a free library for interactive maps.
// The background map tiles come from OpenStreetMap (free to use with attribution).
// On top of that we draw our own graph: places (vertices) and roads (edges).
const SafeMap = (() => {
  const pretty = name => name.replace(/_/g, " ");
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // Leaflet draws with SVG attributes, which can't read CSS variables like var(--fast),
  // so we look up the actual colour value from the stylesheet.
  function cssColor(value) {
    const m = /^var\((--[\w-]+)\)$/.exec(value);
    return m ? getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim() : value;
  }
  const safetyVar = s => s >= 8 ? "var(--risk-lo)" : s >= 5 ? "var(--risk-mid)" : "var(--risk-hi)";
  const safetyColor = s => safetyVar(s);   // for HTML, where var() works

  const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

  // Create a map inside `el`. Callbacks: onNode(locationId), onRoad(roadId).
  function create(el, { onNode, onRoad } = {}) {
    const map = L.map(el, { zoomSnap: 0.5 });
    L.tileLayer(TILES, {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    const routeLayer = L.layerGroup().addTo(map);   // wide coloured band under the route
    const roadLayer = L.layerGroup().addTo(map);    // every road, coloured by safety
    const placeLayer = L.layerGroup().addTo(map);   // place markers on top
    let data = null;
    let fitted = false;

    // opts: { routeRoads: [roadIds], routeColor, from, to, selectedRoad }
    function draw(newData, opts = {}) {
      data = newData;
      // The map needs a view (centre + zoom) before labels can be placed.
      if (!fitted) {
        map.fitBounds(data.locations.map(l => [l.lat, l.lng]), { padding: [20, 20] });
        fitted = true;
      }
      routeLayer.clearLayers();
      roadLayer.clearLayers();
      placeLayer.clearLayers();
      const name = id => pretty(data.locations.find(l => l.id === id).name);

      const onRoute = new Set(opts.routeRoads || []);
      for (const r of data.roads) {
        if (onRoute.has(r.id)) {
          L.polyline(r.shape, { color: cssColor(opts.routeColor), weight: 14, opacity: 0.45, interactive: false }).addTo(routeLayer);
        }
        const selected = r.id === opts.selectedRoad;
        L.polyline(r.shape, {
          color: selected ? cssColor("var(--ink)") : cssColor(safetyVar(r.safety)),
          weight: selected ? 7 : 4,
          opacity: 0.9,
        })
          .bindTooltip(`<b>${esc(r.name)}</b><br>${esc(name(r.from_id))} – ${esc(name(r.to_id))}<br>${r.km} km · ${r.time} min · safety ${r.safety}/10`, { sticky: true })
          .on("click", () => onRoad && onRoad(r.id))
          .addTo(roadLayer);
      }

      for (const l of data.locations) {
        const isStart = l.id === opts.from, isEnd = l.id === opts.to;
        L.circleMarker([l.lat, l.lng], {
          radius: isStart || isEnd ? 8 : 5,
          color: cssColor("var(--ink)"),
          weight: isEnd ? 4 : 2,
          fillColor: cssColor(isStart ? "var(--ink)" : "var(--panel)"),
          fillOpacity: 1,
        })
          .bindTooltip(esc(pretty(l.name)), { permanent: true, direction: "top", offset: [0, -6], className: "place-label" })
          .on("click", () => onNode && onNode(l.id))
          .addTo(placeLayer);
      }
    }

    // Zoom the map so these roads fill the view.
    function fitRoads(roadIds, maxZoom = 14) {
      const pts = data.roads.filter(r => roadIds.includes(r.id)).flatMap(r => r.shape);
      if (pts.length) map.fitBounds(pts, { padding: [40, 40], maxZoom });
    }

    return { draw, fitRoads, leaflet: map };
  }

  return { create, pretty, safetyColor, esc };
})();
