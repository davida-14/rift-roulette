// What the page can ask the desktop side for: which champion League says you're on, a diagnostic
// save of Riot's in-game data, and overlay controls (enter/leave overlay mode, hide, drag, resize).
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("riftDesktop", {
  detectChampion: () => ipcRenderer.invoke("detect-champion"),
  dumpLiveData: () => ipcRenderer.invoke("dump-live-data"),
  overlayShortcut: () => ipcRenderer.invoke("overlay-shortcut"),
  setOverlayMode: on => ipcRenderer.send("overlay-mode", !!on),
  hideOverlay: () => ipcRenderer.send("overlay-hide"),
  overlayDrag: (dx, dy) => ipcRenderer.send("overlay-drag", { dx, dy }),
  overlayDragEnd: () => ipcRenderer.send("overlay-drag-end"),
  overlaySize: kind => ipcRenderer.send("overlay-size", kind),
});
