# Grove frontend

A vanilla JavaScript browser extension interface. No framework, build step, or external font downloads are required.

## Interactive design preview

From the repository root:

```powershell
python -m http.server 5173 --bind 127.0.0.1 --directory Frontend
```

Open http://127.0.0.1:5173/popup.html?preview=1.

The preview uses sample history and an in-memory API for starting, pausing, resuming, and ending sessions, changing settings, and editing the blocklist. Reloading resets the sample data. It does not connect to the backend or block websites. Preview mode is only enabled by `preview=1` on localhost or 127.0.0.1.

## Browser extension

Open `chrome://extensions` or `edge://extensions`, enable Developer mode, choose **Load unpacked**, and select the `Frontend` directory. Reload the extension after editing its files.

The extension uses `api/backend.js` to connect to the Python API at `http://127.0.0.1:8000/backend`. Opening `popup.html` without `preview=1` also uses the real API; localhost port 5173 is allowed by the server's CORS configuration.

The backend now persists session timelines, website visits, settings, and history. **History** provides session details and JSON/CSV exports. The extension tracks foreground website activity only during running sessions and requests the `idle` permission to distinguish machine inactivity. See [Activity tracking](../Documents/ActivityTracking.md) for the data format, timing limits, recovery behavior, and tests. Actual website blocking remains unimplemented.

## Files

- `main.js`: state, routing, page cleanup, and opt-in preview setup.
- `styles.css`: shared typography, colors, layout, and controls.
- `pages/`: session setup, active/paused/completed session, settings, blocklist, and history with exports.
- `components/`: navigation, timer, and editable website list.
- `api/backend.js`: existing Python API adapter.
- `api/preview.js`: isolated sample data for reviewing the interface.
- `popup.html`, `manifest.json`, `background.js`: extension entry points.
