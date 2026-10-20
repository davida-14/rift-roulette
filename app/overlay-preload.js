// The overlay receives builds and move-mode changes; the only things it can send back are
// drag steps and "done moving".
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("overlayApi", {
  onBuild: cb => ipcRenderer.on("build", (_e, build) => cb(build)),
  onMoveMode: cb => ipcRenderer.on("move-mode", (_e, on) => cb(on)),
  drag: (dx, dy) => ipcRenderer.send("overlay-drag", { dx, dy }),
  done: () => ipcRenderer.send("overlay-done"),
});
