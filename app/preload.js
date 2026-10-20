// What the page can ask the desktop side for: which champion League says you're on, and a
// diagnostic save of Riot's in-game data.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("riftDesktop", {
  detectChampion: () => ipcRenderer.invoke("detect-champion"),
  dumpLiveData: () => ipcRenderer.invoke("dump-live-data"),
  publishBuild: build => ipcRenderer.send("build", build),           // feeds the Ctrl+Shift+B overlay
  overlayShortcut: () => ipcRenderer.invoke("overlay-shortcut"),
});
