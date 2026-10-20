const { app, BrowserWindow, Menu, Tray, shell, dialog, ipcMain, globalShortcut, screen } = require("electron");
const { autoUpdater } = require("electron-updater");
const path = require("path");
const fs = require("fs");
const https = require("https");
const { execFile } = require("child_process");

let mainWin = null, splash = null;

function createWindow() {
  mainWin = new BrowserWindow({
    width: 1180,
    height: 900,
    minWidth: 420,
    minHeight: 500,
    title: "Rift Roulette",
    backgroundColor: "#0b1118",
    icon: path.join(__dirname, "build", "icon.png"),
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, "preload.js") },
  });
  // Any web link opens in the user's browser, never inside the app.
  mainWin.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  mainWin.webContents.on("will-navigate", (e, url) => { if (!url.startsWith("file://")) { e.preventDefault(); shell.openExternal(url); } });
  mainWin.loadFile(path.join(__dirname, "src", "index.html"), { query: { v: app.getVersion() } });
  mainWin.on("closed", () => { mainWin = null; app.quit(); });   // closing the app also closes the overlay
}

// ---------- Overlay ----------
// The overlay is a compact copy of the app (the same page with ?view=overlay) in a small
// always-on-top window. It never touches League: clicking it doesn't take focus from the game, and
// it shows over League in Borderless or Windowed mode (not exclusive Fullscreen).
// Overlay mode hides the main window to the tray, so the overlay is the whole app until you open
// the full window again. Ctrl+Shift+B shows or hides the overlay in either mode.
const OVERLAY_KEY = "CommandOrControl+Shift+B";
const SIZES = { compact: { w: 400, h: 640 }, modal: { w: 820, h: 680 } };
let overlay = null, overlaySize = "compact", compactPos = null, tray = null, overlayMode = false;

// Where the overlay sits is remembered in the app's data folder. A saved spot that no longer
// lands on any screen (say a monitor was unplugged) falls back to the top-right corner.
const posFile = () => path.join(app.getPath("userData"), "overlay-position.json");
function overlayStartPosition() {
  try {
    const p = JSON.parse(fs.readFileSync(posFile(), "utf8"));
    const onScreen = screen.getAllDisplays().some(d => { const a = d.workArea;
      return p.x + 40 > a.x && p.x + 40 < a.x + a.width && p.y + 20 > a.y && p.y + 20 < a.y + a.height; });
    if (onScreen && Number.isFinite(p.x) && Number.isFinite(p.y)) return p;
  } catch {}
  const { workArea } = screen.getPrimaryDisplay();
  return { x: workArea.x + workArea.width - SIZES.compact.w - 16, y: workArea.y + 90 };
}
function saveOverlayPosition() {
  if (!overlay || overlaySize !== "compact") return;
  const [x, y] = overlay.getPosition();
  try { fs.writeFileSync(posFile(), JSON.stringify({ x, y })); } catch {}
}

function createOverlay() {
  const start = overlayStartPosition();
  overlay = new BrowserWindow({
    width: SIZES.compact.w, height: SIZES.compact.h, x: start.x, y: start.y,
    frame: false, transparent: true, resizable: false, movable: false, focusable: true,
    skipTaskbar: true, alwaysOnTop: true, hasShadow: false, show: false, backgroundColor: "#00000000",
    icon: path.join(__dirname, "build", "icon.png"),
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, "preload.js") },
  });
  overlay.setAlwaysOnTop(true, "screen-saver");
  overlay.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  overlay.loadFile(path.join(__dirname, "src", "index.html"), { query: { v: app.getVersion(), view: "overlay" } });
  overlay.on("closed", () => { overlay = null; overlaySize = "compact"; });
}
// While League has focus it keeps the mouse, so clicks never reach another window. So the shortcut
// hands focus to the overlay (and remembers the game), and hiding the overlay hands focus back.
let win32;
function getWin32() {
  if (win32 !== undefined) return win32;
  try {
    const koffi = require("koffi");
    const u = koffi.load("user32.dll"), k = koffi.load("kernel32.dll");
    win32 = {
      keyState: u.func("short __stdcall GetAsyncKeyState(int vKey)"),
      foreground: u.func("intptr_t __stdcall GetForegroundWindow()"),
      setForeground: u.func("bool __stdcall SetForegroundWindow(intptr_t hWnd)"),
      threadOf: u.func("uint32_t __stdcall GetWindowThreadProcessId(intptr_t hWnd, void *pid)"),
      attachInput: u.func("bool __stdcall AttachThreadInput(uint32_t idAttach, uint32_t idAttachTo, bool fAttach)"),
      currentThread: k.func("uint32_t __stdcall GetCurrentThreadId()"),
    };
  } catch { win32 = null; }
  return win32;
}
const hwndOf = w => { const b = w.getNativeWindowHandle(); return b.length >= 8 ? Number(b.readBigUInt64LE(0)) : b.readUInt32LE(0); };
let returnTo = 0;                                     // the window (League) to give focus back to

function focusOverlay() {
  if (!overlay) createOverlay();
  const w = getWin32();
  if (w) {
    const fg = Number(w.foreground()), ours = [overlay, mainWin].filter(Boolean).map(hwndOf);
    if (fg && !ours.includes(fg)) returnTo = fg;
  }
  overlay.show();
  if (w) {
    // Windows only lets the app that has the input give focus away, so briefly share League's
    // input queue while asking for focus (a standard, documented technique).
    const me = w.currentThread(), theirs = w.threadOf(w.foreground(), null);
    const share = theirs && theirs !== me;
    if (share) w.attachInput(me, theirs, true);
    w.setForeground(hwndOf(overlay));
    if (share) w.attachInput(me, theirs, false);
  }
  overlay.focus();
}
function hideOverlay() {
  if (!overlay) return;
  const hadFocus = overlay.isFocused();
  overlay.hide();
  const w = getWin32();
  if (w && returnTo && hadFocus) w.setForeground(returnTo);
  returnTo = 0;
}
// Shortcut: hidden -> show and focus; showing but the game has focus -> focus it; focused -> hide.
function toggleOverlay() {
  if (!overlay || !overlay.isVisible() || !overlay.isFocused()) focusOverlay();
  else hideOverlay();
}

// Gamba, the case and the FF15 prompt need more room than the compact panel: grow while one is
// open (kept on screen), then shrink back to where the panel was.
function setOverlaySize(kind) {
  if (!overlay || !SIZES[kind]) return;
  const { w, h } = SIZES[kind];
  const [cw, chh] = overlay.getSize();
  if (cw === w && chh === h) { overlaySize = kind; return; }   // judge by the real size, not a remembered one
  const [x, y] = overlay.getPosition();
  if (cw === SIZES.compact.w && chh === SIZES.compact.h) compactPos = { x, y };
  overlaySize = kind;
  let nx = x, ny = y;
  if (kind === "compact" && compactPos) ({ x: nx, y: ny } = compactPos);
  else {
    const a = screen.getDisplayNearestPoint({ x: x + 20, y: y + 20 }).workArea;
    nx = Math.max(a.x, Math.min(x, a.x + a.width - w)); ny = Math.max(a.y, Math.min(y, a.y + a.height - h));
  }
  overlay.setBounds({ x: nx, y: ny, width: w, height: h });
}

function createTray() {
  if (tray) return;
  tray = new Tray(path.join(__dirname, "build", "icon.png"));
  tray.setToolTip("Rift Roulette (overlay mode): Ctrl+Shift+B shows the overlay");
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Show / hide overlay (Ctrl+Shift+B)", click: toggleOverlay },
    { label: "Open full app", click: exitOverlayMode },
    { type: "separator" },
    { label: "Quit Rift Roulette", click: () => app.quit() },
  ]));
  tray.on("click", exitOverlayMode);
}
function enterOverlayMode() {
  overlayMode = true;
  createTray();
  if (mainWin) mainWin.hide();
  focusOverlay();
}
function exitOverlayMode() {
  overlayMode = false;
  if (overlay) overlay.hide();
  if (tray) { tray.destroy(); tray = null; }
  if (mainWin) { mainWin.show(); mainWin.focus(); }
}

const fromOverlay = e => overlay && e.sender === overlay.webContents;
ipcMain.on("overlay-drag", (e, d) => {
  if (!fromOverlay(e) || !d || !Number.isFinite(d.dx) || !Number.isFinite(d.dy)) return;
  const [x, y] = overlay.getPosition();
  overlay.setPosition(Math.round(x + d.dx), Math.round(y + d.dy));
  if (overlaySize !== "compact") compactPos = null;   // moved while enlarged: shrink back where it is now
});
ipcMain.on("overlay-drag-end", e => { if (fromOverlay(e)) saveOverlayPosition(); });
ipcMain.on("overlay-size", (e, kind) => { if (fromOverlay(e)) setOverlaySize(kind); });
ipcMain.on("overlay-hide", e => { if (fromOverlay(e)) hideOverlay(); });
ipcMain.on("overlay-mode", (_e, on) => (on ? enterOverlayMode() : exitOverlayMode()));
global.riftToggleOverlay = toggleOverlay;        // reachable from a debugger for testing; not exposed to any page
global.riftEnterOverlayMode = enterOverlayMode;
global.riftExitOverlayMode = exitOverlayMode;

// League switches off Windows hotkeys while the game has focus, so instead of registering one we
// read the keyboard's up/down state (GetAsyncKeyState) about 25 times a second and toggle when
// Ctrl+Shift+B goes down. Read-only: nothing is intercepted, blocked or recorded.
let keyWatch = null;
function watchOverlayKeys() {
  const w = getWin32();
  if (!w) return false;
  const down = vk => (w.keyState(vk) & 0x8000) !== 0;
  const pressed = vk => (w.keyState(vk) & 0x8001) !== 0;    // held now, or tapped since the last check
  let wasB = false;
  keyWatch = setInterval(() => {
    const b = down(0x11) && down(0x10) && pressed(0x42);    // Ctrl + Shift + B
    if (b && !wasB) toggleOverlay();
    wasB = b;
  }, 40);
  return true;
}
ipcMain.handle("overlay-shortcut", () => (keyWatch || globalShortcut.isRegistered(OVERLAY_KEY) ? "Ctrl+Shift+B" : null));

// ---------- Champion detection (League's own local APIs, no screenshots) ----------
// In a game, Riot's Live Client Data API (port 2999) lists every player and their champion.
// In champion select, the League client's local API reports the champion you're on. Both only
// answer on this PC, over HTTPS with Riot's self-signed certificate, so certificate checks are
// relaxed for these 127.0.0.1 requests only.
function localJSON(url, password) {
  return new Promise((resolve, reject) => {
    const headers = password ? { Authorization: "Basic " + Buffer.from("riot:" + password).toString("base64") } : {};
    const req = https.get(url, { rejectUnauthorized: false, headers, timeout: 2000 }, res => {
      let body = "";
      res.on("data", c => body += c);
      res.on("end", () => {
        if (res.statusCode >= 400) return reject(new Error("HTTP " + res.statusCode));
        try { resolve(JSON.parse(body)); } catch (e) { reject(e); }
      });
    });
    req.on("timeout", () => req.destroy(new Error("timeout")));
    req.on("error", reject);
  });
}

// The League client writes its port and password to a lockfile; if it isn't in a usual install
// folder, read them from the running client's command line instead.
async function clientCredentials() {
  for (const dir of ["C:\\Riot Games\\League of Legends", "D:\\Riot Games\\League of Legends", "E:\\Riot Games\\League of Legends"]) {
    try {
      const [, , port, password] = fs.readFileSync(path.join(dir, "lockfile"), "utf8").split(":");
      if (port && password) return { port, password };
    } catch {}
  }
  const cmd = await new Promise(resolve => execFile("powershell.exe",
    ["-NoProfile", "-Command", "(Get-CimInstance Win32_Process -Filter \"name='LeagueClientUx.exe'\").CommandLine"],
    { windowsHide: true, timeout: 6000 }, (err, out) => resolve(out || "")));
  const port = (/--app-port=(\d+)/.exec(cmd) || [])[1], password = (/--remoting-auth-token=([\w-]+)/.exec(cmd) || [])[1];
  return port && password ? { port, password } : null;
}

ipcMain.handle("detect-champion", async () => {
  try {
    const [me, players] = await Promise.all([
      localJSON("https://127.0.0.1:2999/liveclientdata/activeplayername"),
      localJSON("https://127.0.0.1:2999/liveclientdata/playerlist"),
    ]);
    const mine = players.find(p => p.riotId === me || p.summonerName === me) ||
                 players.find(p => p.riotIdGameName && String(me).startsWith(p.riotIdGameName + "#"));
    if (mine) return { source: "game", name: mine.championName };
  } catch {}
  try {
    const creds = await clientCredentials();
    if (creds) {
      const id = await localJSON(`https://127.0.0.1:${creds.port}/lol-champ-select/v1/current-champion`, creds.password);
      if (id) return { source: "champ-select", key: String(id) };
      return { error: "You don't have a champion yet. Try again once you're assigned one." };
    }
  } catch {}
  return { error: "League isn't in champion select or a game right now." };
});

// ---------- Forced updates (GitHub Releases) ----------
// On launch: check, and if a newer version exists, download it, install it and restart before the
// app opens. Offline or slow? The app opens anyway after a short wait. While running, it checks
// hourly and restarts into any new version it finds.
const SPLASH_HTML = `<!doctype html><meta charset="utf-8"><body style="margin:0;height:100vh;display:grid;place-items:center;
  background:#0b1118;color:#e7e2d4;font:15px 'Segoe UI',sans-serif;border:1px solid #c8a65a;box-sizing:border-box">
  <div style="text-align:center"><div style="font:700 22px Georgia,serif;color:#c8a65a;letter-spacing:.06em;margin-bottom:10px">RIFT ROULETTE</div>
  <div id="msg">Checking for updatesâ€¦</div></div></body>`;

function showSplash() {
  splash = new BrowserWindow({ width: 360, height: 170, frame: false, resizable: false, show: true, backgroundColor: "#0b1118",
    icon: path.join(__dirname, "build", "icon.png"), webPreferences: { contextIsolation: true, sandbox: true } });
  splash.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(SPLASH_HTML));
  splash.on("closed", () => { splash = null; });
}
function splashText(text) {
  if (splash) splash.webContents.executeJavaScript(`document.getElementById("msg").textContent = ${JSON.stringify(text)}`).catch(() => {});
}

function startWithUpdateCheck() {
  if (!app.isPackaged) { createWindow(); return; }        // `npm start` during development skips updates
  showSplash();
  let opened = false;
  const openApp = () => { if (opened) return; opened = true; clearTimeout(timer); if (splash) splash.close(); createWindow(); };
  const timer = setTimeout(openApp, 10000);              // no answer in 10s: play now, update next launch

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.on("update-not-available", openApp);
  autoUpdater.on("error", () => { if (!opened) openApp(); });
  autoUpdater.on("update-available", info => { if (!opened) { clearTimeout(timer); splashText(`Downloading update ${info.version}â€¦`); } });
  autoUpdater.on("download-progress", p => { if (!opened) splashText(`Downloading updateâ€¦ ${Math.round(p.percent)}%`); });
  autoUpdater.on("update-downloaded", async info => {
    if (opened && mainWin) {
      await dialog.showMessageBox(mainWin, { type: "info", title: "Rift Roulette update", buttons: ["Restart now"],
        message: `Rift Roulette ${info.version} is ready.`, detail: "The app will restart to finish updating." });
    } else splashText(`Installing ${info.version}â€¦`);
    setImmediate(() => autoUpdater.quitAndInstall(true, true));   // silent install, then relaunch
  });
  autoUpdater.checkForUpdates().catch(() => openApp());
  setInterval(() => autoUpdater.checkForUpdates().catch(() => {}), 60 * 60 * 1000);
}

Menu.setApplicationMenu(null);
app.whenReady().then(() => {
  // Key-state check works even while League is focused; a normal hotkey is only the fallback.
  if (!watchOverlayKeys()) globalShortcut.register(OVERLAY_KEY, toggleOverlay);
  startWithUpdateCheck();
});
app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => app.quit());
