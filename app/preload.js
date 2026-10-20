// The only thing the page can ask the desktop side for: which champion League says you're on.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("riftDesktop", {
  detectChampion: () => ipcRenderer.invoke("detect-champion"),
});
