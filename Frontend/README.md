# Grove — Focus (restructured)

The single-file `focus-extension.html` prototype, split into the modular
structure you specified. **Vanilla ES modules** — no framework, no build step;
loads straight into an MV3 popup.

```
Frontend/
├── pages/
│   ├── StartPage.js      # home + new-session setup   (was screens 1 Welcome, 2 Start, 6 Past)
│   ├── SessionPage.js    # running / paused / complete (was screens 3, 7, 4)
│   ├── BlockListPage.js  # edit blocked sites          (was the Blocklist row in Settings)
│   └── SettingsPage.js   # toggles + default length    (was screen 5)
│
├── components/
│   ├── Timer.js          # countdown dial + focus score
│   ├── WebsiteList.js    # add/remove blocked domains
│   └── NavigationBar.js  # reusable topbar
│
├── api/
│   └── backend.js        # api.* (REST) + bg() (background worker) + mock fallback
│
├── main.js               # state, router, mount
│
├── popup.html            # shell — <script type="module" src="main.js">   (glue)
├── styles.css            # design tokens + component CSS                    (glue)
└── manifest.json         # MV3                                             (glue)
```

`popup.html`, `styles.css`, `manifest.json` weren't in your diagram but are
required for the `.js` files to run as an extension.

## How it works

- **`main.js`** holds `state` (`page`, `session`, `settings`), a `navigate(page)`
  router, and mounts the current page into `#app`. It passes every page a
  `ctx = { navigate, state, api, bg }`.
- **Pages** are functions returning a `<section class="screen active">` element.
- **Components** are factories returning a DOM node (Timer also returns
  start/pause/resume/stop controls).
- **`api/backend.js`** is the single seam to the outside world. `USE_MOCK = true`
  means the whole UI runs with canned data and no server — flip it off when your
  backend is live.

## Run it now (no server)

Open `popup.html` via a local server (ES modules need http, not `file://`):

```bash
cd Frontend && python3 -m http.server 5173   # then open http://localhost:5173/popup.html
```

## Load as an extension

`chrome://extensions` → Developer mode → **Load unpacked** → select `Frontend/`.

## Next step: background service worker

A popup can't run a reliable timer or block tabs — it dies on focus loss. Move
the timer, `declarativeNetRequest` blocking, and drift scoring into a
`background.js` service worker. The seams already exist: pages call
`bg('SESSION_START' | 'SESSION_PAUSE' | 'SESSION_RESUME' | 'SESSION_END' | 'BLOCKLIST_UPDATED', payload)`.
The worker should push `{type:'TICK', remaining}` and `{type:'SCORE', score}`
messages back; wire them to `Timer`'s `remaining` repaint and `setScore()`.
