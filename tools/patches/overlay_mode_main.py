"""One-off patch: replace the read-only build overlay in app/main.js with Overlay mode."""
from pathlib import Path

p = Path("app/main.js"); s = p.read_text(encoding="utf-8")

def rep(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)

rep('const { app, BrowserWindow, Menu, shell, dialog, ipcMain, globalShortcut, screen } = require("electron");',
    'const { app, BrowserWindow, Menu, Tray, shell, dialog, ipcMain, globalShortcut, screen } = require("electron");')
rep('    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, "preload.js") },\n  });\n  // Any web link opens',
    '    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, "preload.js"), backgroundThrottling: false },\n  });\n  // Any web link opens')

a = s.index("// ---------- Build overlay ----------")
b = s.index('ipcMain.handle("overlay-shortcut"', a); b = s.index("\n", b) + 1
s = s[:a] + r'''// ---------- Overlay ----------
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
    frame: false, transparent: true, resizable: false, movable: false, focusable: false,
    skipTaskbar: true, alwaysOnTop: true, hasShadow: false, show: false, backgroundColor: "#00000000",
    icon: path.join(__dirname, "build", "icon.png"),
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, "preload.js"), backgroundThrottling: false },
  });
  overlay.setAlwaysOnTop(true, "screen-saver");
  overlay.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  overlay.loadFile(path.join(__dirname, "src", "index.html"), { query: { v: app.getVersion(), view: "overlay" } });
  overlay.on("closed", () => { overlay = null; overlaySize = "compact"; });
}
function showOverlay() { if (!overlay) createOverlay(); if (!overlay.isVisible()) overlay.showInactive(); }
function toggleOverlay() {
  if (overlay && overlay.isVisible()) overlay.hide(); else showOverlay();
}

// Gamba, the case and the FF15 prompt need more room than the compact panel: grow while one is
// open (kept on screen), then shrink back to where the panel was.
function setOverlaySize(kind) {
  if (!overlay || !SIZES[kind] || kind === overlaySize) return;
  const [x, y] = overlay.getPosition();
  if (overlaySize === "compact") compactPos = { x, y };
  overlaySize = kind;
  const { w, h } = SIZES[kind];
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
  showOverlay();
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
});
ipcMain.on("overlay-drag-end", e => { if (fromOverlay(e)) saveOverlayPosition(); });
ipcMain.on("overlay-size", (e, kind) => { if (fromOverlay(e)) setOverlaySize(kind); });
ipcMain.on("overlay-hide", e => { if (fromOverlay(e)) overlay.hide(); });
ipcMain.on("overlay-mode", (_e, on) => (on ? enterOverlayMode() : exitOverlayMode()));
global.riftToggleOverlay = toggleOverlay;        // reachable from a debugger for testing; not exposed to any page
global.riftEnterOverlayMode = enterOverlayMode;
global.riftExitOverlayMode = exitOverlayMode;

// League switches off Windows hotkeys while the game has focus, so instead of registering one we
// read the keyboard's up/down state (GetAsyncKeyState) about 25 times a second and toggle when
// Ctrl+Shift+B goes down. Read-only: nothing is intercepted, blocked or recorded.
let keyWatch = null;
function watchOverlayKeys() {
  let keyState;
  try {
    const koffi = require("koffi");
    keyState = koffi.load("user32.dll").func("short __stdcall GetAsyncKeyState(int vKey)");
  } catch { return false; }
  const down = vk => (keyState(vk) & 0x8000) !== 0;
  let wasB = false;
  keyWatch = setInterval(() => {
    const b = down(0x11) && down(0x10) && down(0x42);       // Ctrl + Shift + B
    if (b && !wasB) toggleOverlay();
    wasB = b;
  }, 40);
  return true;
}
ipcMain.handle("overlay-shortcut", () => (keyWatch || globalShortcut.isRegistered(OVERLAY_KEY) ? "Ctrl+Shift+B" : null));
''' + s[b:]

rep("  if (!watchOverlayKeys()) { globalShortcut.register(OVERLAY_KEY, toggleOverlay); globalShortcut.register(MOVE_KEY, toggleMoveMode); }",
    "  if (!watchOverlayKeys()) globalShortcut.register(OVERLAY_KEY, toggleOverlay);")
p.write_text(s, encoding="utf-8")
print("ok")
