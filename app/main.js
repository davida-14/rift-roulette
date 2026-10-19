const { app, BrowserWindow, Menu, shell, dialog } = require("electron");
const { autoUpdater } = require("electron-updater");
const path = require("path");

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
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false },
  });
  // Any web link opens in the user's browser, never inside the app.
  mainWin.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  mainWin.webContents.on("will-navigate", (e, url) => { if (!url.startsWith("file://")) { e.preventDefault(); shell.openExternal(url); } });
  mainWin.loadFile(path.join(__dirname, "src", "index.html"), { query: { v: app.getVersion() } });
  mainWin.on("closed", () => { mainWin = null; });
}

// ---------- Forced updates (GitHub Releases) ----------
// On launch: check, and if a newer version exists, download it, install it and restart before the
// app opens. Offline or slow? The app opens anyway after a short wait. While running, it checks
// hourly and restarts into any new version it finds.
const SPLASH_HTML = `<!doctype html><meta charset="utf-8"><body style="margin:0;height:100vh;display:grid;place-items:center;
  background:#0b1118;color:#e7e2d4;font:15px 'Segoe UI',sans-serif;border:1px solid #c8a65a;box-sizing:border-box">
  <div style="text-align:center"><div style="font:700 22px Georgia,serif;color:#c8a65a;letter-spacing:.06em;margin-bottom:10px">RIFT ROULETTE</div>
  <div id="msg">Checking for updates…</div></div></body>`;

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
  autoUpdater.on("update-available", info => { if (!opened) { clearTimeout(timer); splashText(`Downloading update ${info.version}…`); } });
  autoUpdater.on("download-progress", p => { if (!opened) splashText(`Downloading update… ${Math.round(p.percent)}%`); });
  autoUpdater.on("update-downloaded", async info => {
    if (opened && mainWin) {
      await dialog.showMessageBox(mainWin, { type: "info", title: "Rift Roulette update", buttons: ["Restart now"],
        message: `Rift Roulette ${info.version} is ready.`, detail: "The app will restart to finish updating." });
    } else splashText(`Installing ${info.version}…`);
    setImmediate(() => autoUpdater.quitAndInstall(true, true));   // silent install, then relaunch
  });
  autoUpdater.checkForUpdates().catch(() => openApp());
  setInterval(() => autoUpdater.checkForUpdates().catch(() => {}), 60 * 60 * 1000);
}

Menu.setApplicationMenu(null);
app.whenReady().then(startWithUpdateCheck);
app.on("window-all-closed", () => app.quit());
