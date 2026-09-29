# OpenStreetMap (OSM) Integration Guide

**Project:** Where Is My Stuff?
**Stack:** Django + Leaflet.js + OpenStreetMap tiles (no Google Maps API key required)

## 1. Architecture

```
Django (backend + DB)
    -> Django Templates (HTML/CSS/JS delivery)
        -> Leaflet.js (map rendering, markers, clicks, geolocation)
            -> OpenStreetMap tiles (basemap)
```

Django owns application logic and storage. Leaflet owns everything visual: rendering the map, placing markers, handling clicks, and reading the browser's location. Coordinates flow one way: Django serializes them into the template, Leaflet reads them and draws markers. The map itself is never stored, only latitude/longitude values.

## 2. Data Model

Store coordinates as decimal fields. Minimum required fields:

```python
latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
location_name = models.CharField(max_length=255, blank=True)
```

> Add these to the existing `Report` model (and mirror on `Draft.data` as JSON, the same pattern already used for the private photo field) rather than introducing a separate model.

## 3. Implementation Phases

### Phase 1: Django Foundation
- Add `latitude`, `longitude`, `location_name` to `Report` and `Draft`
- Migration
- Confirm existing report views pass the new fields through

### Phase 2: Render the Map
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<div id="map" style="height: 400px;"></div>
```
```javascript
const map = L.map("map").setView([24.8607, 67.0011], 13); // Karachi default
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
```

### Phase 3: Location Picker (Report Form)
Clicking the map sets a draggable marker and writes into hidden form fields.
```javascript
let marker;
map.on("click", (e) => {
  const { lat, lng } = e.latlng;
  if (marker) map.removeLayer(marker);
  marker = L.marker([lat, lng], { draggable: true }).addTo(map);
  document.getElementById("latitude").value = lat;
  document.getElementById("longitude").value = lng;
});
```
```html
<input type="hidden" id="latitude" name="latitude">
<input type="hidden" id="longitude" name="longitude">
```
Flow: click on map, Leaflet reads coordinates, JS fills hidden inputs, Django form submits, values saved to DB.

### Phase 4: Display Reports on the Map
```python
def map_view(request):
    reports = Report.objects.filter(latitude__isnull=False)
    return render(request, "map.html", {"reports": reports})
```
```javascript
const reports = {{ reports_json|safe }};  // use Django's JSON serializer, never raw string interpolation
reports.forEach(r => {
  L.marker([r.latitude, r.longitude])
    .addTo(map)
    .bindPopup(`<b>${r.title}</b><br>${r.kind}`);
});
```

### Phase 5: "Use My Current Location"
```javascript
map.locate({ setView: true, maxZoom: 16 });
map.on("locationfound", (e) => {
  L.marker(e.latlng).addTo(map).bindPopup("Your current location").openPopup();
});
```
Requires the browser to grant geolocation permission.

### Phase 6: Location Search (later increment)
Use Nominatim, OSM's geocoding service, for a search box, not autocomplete:
```
"NED University" -> Nominatim -> lat/lng -> map recenters -> user confirms
```
One request on explicit submit is within policy; a request per keystroke is not.

## 4. Usage Policy Notes

- **Tiles:** `tile.openstreetmap.org` is community-funded, not an unlimited API. Required: visible attribution, HTTPS, tile caching, no bulk/offline downloading. Fine for localhost or a small deployment; self-host or use a commercial OSM-derived provider (e.g. MapTiler, Stadia Maps) at production scale.
- **Nominatim:** max 1 request/second, requires an identifying User-Agent, no client-side autocomplete. A user-triggered search on submit is acceptable.
- **No API key required.** Leaflet is provider-agnostic, so the tile source can be swapped later without touching application code.

## 5. MVP Checklist

1. `latitude` / `longitude` / `location_name` added to `Report`, migration applied
2. Map renders on the report form
3. Clicking the map sets a marker and fills the hidden fields
4. Form submit saves coordinates to the DB
5. Map view lists reports with saved coordinates as markers
6. Marker popup shows report title and kind
7. Missing coordinates do not block report submission (same tolerance already used for the optional photo field)

Ship these seven before adding current-location, search, radius filtering, or a LOST/FOUND map toggle.

## 6. References

- Leaflet Quick Start: https://leafletjs.com/examples/quick-start/
- Leaflet Geolocation: https://leafletjs.com/examples/mobile/
- Nominatim Usage Policy: https://operations.osmfoundation.org/policies/nominatim/
- OSM Tile Usage Policy: https://operations.osmfoundation.org/policies/tiles/
