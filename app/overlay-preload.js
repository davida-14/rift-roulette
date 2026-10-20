// The overlay window only ever receives builds from the app; it can't send anything back.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("overlayApi", {
  onBuild: cb => ipcRenderer.on("build", (_e, build) => cb(build)),
});
