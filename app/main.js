const { app, BrowserWindow, Menu, shell, dialog, ipcMain } = require("electron");
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
  mainWin.on("closed", () => { mainWin = null; });
}

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

// Diagnostic: save everything Riot's in-game API reports, to see what it exposes (e.g. augments).
ipcMain.handle("dump-live-data", async () => {
  let data;
  try { data = await localJSON("https://127.0.0.1:2999/liveclientdata/allgamedata"); }
  catch { return { error: "No game found. Riot's in-game data only answers while you're in a game." }; }
  const dir = path.join(app.getPath("documents"), "Rift Roulette diagnostics");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `live-game-${new Date().toISOString().replace(/[:.]/g, "-")}.json`);
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
  return { file };
});

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
