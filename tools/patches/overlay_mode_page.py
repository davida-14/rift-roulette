"""One-off patch: compact overlay view, overlay-mode controls and cross-window sync in src/page.html."""
from pathlib import Path

p = Path("src/page.html"); s = p.read_text(encoding="utf-8")

def rep(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)

# 1. Mark the compact view before anything draws (the overlay window loads the page with ?view=overlay)
rep("  apply(saved);\n})();\n</script>",
    "  apply(saved);\n  if (new URLSearchParams(location.search).get(\"view\") === \"overlay\") document.documentElement.classList.add(\"compact\");\n})();\n</script>")

# 2. Compact layout
first_style_end = s.index("</style>")
s = s[:first_style_end] + """
/* Overlay view (desktop app): the same page squeezed into a small always-on-top panel.
   No header, item pool, augment picker, build code or footer; builds are one-line rows. */
.ov-bar { display: none; }
html.compact body { background: transparent; padding: 0; overflow-y: auto; }
html.compact .wrap { gap: 8px; max-width: none; min-height: 100vh; padding: 0 10px 10px;
  background: color-mix(in srgb, var(--void) 94%, transparent); border: 1px solid var(--gold); }
html.compact .ov-bar { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 0 -10px; padding: 6px 10px;
  background: var(--panel); border-bottom: 1px solid var(--line); cursor: move; user-select: none; touch-action: none; }
html.compact .ov-bar b { font-family: var(--display); color: var(--gold); letter-spacing: .05em; font-size: 15px; }
html.compact .ov-bar .ov-acts { display: flex; gap: 6px; }
html.compact .ov-bar .ghost { padding: 3px 9px; font-size: 12px; cursor: pointer; }
html.compact header, html.compact #augment, html.compact section[aria-label="Item pool"], html.compact footer,
html.compact .code, html.compact #overlayHint, html.compact #roleRow, html.compact .slot .detail { display: none !important; }
html.compact .tabs button { padding: 6px 10px; font-size: 13px; }
html.compact .controls { padding: 8px; gap: 8px; }
html.compact .label { display: none; }
html.compact .row { gap: 6px 8px; }
html.compact .seg { gap: 4px; }
html.compact .seg button { padding: 4px 8px; font-size: 13px; }
html.compact .toggle { font-size: 13px; gap: 5px; }
html.compact .roll { font-size: 14px; padding: 6px 14px; }
html.compact .gamba-btn { padding: 4px 8px; font-size: 12px; }
html.compact h2 { font-size: 15px; }
html.compact .total { font-size: 13px; }
html.compact .total b { font-size: 15px; }
html.compact .slots { grid-template-columns: 1fr; gap: 4px; margin-top: 6px; }
html.compact .slot { grid-template-columns: 34px 1fr; gap: 0 8px; padding: 5px 8px; align-items: center; }
html.compact .slot img { width: 34px; height: 34px; grid-row: auto; }
html.compact .slot .kind { font-size: 10px; padding-right: 60px; }
html.compact .slot .name { font-size: 13px; margin: 0; padding-right: 60px; }
html.compact .slot .gold { font-size: 12px; }
html.compact .slot .acts { top: 50%; transform: translateY(-50%); }
html.compact .icon-btn { width: 24px; height: 24px; }
html.compact .champ-card { padding: 6px 8px; gap: 8px; margin-top: 4px; }
html.compact .champ-card img { width: 36px; height: 36px; }
html.compact .cc-text b { font-size: 15px; }
html.compact .note, html.compact .gamba-note { font-size: 12px; margin: 2px 0 0; }
""" + s[first_style_end:]

# 3. Markup: overlay title bar, and the Overlay mode button in the full app's header
rep('<div class="wrap">\n  <header>', '''<div class="wrap">
  <div class="ov-bar" id="ovBar">
    <b>Rift Roulette</b>
    <span class="ov-acts"><button type="button" class="ghost" id="ovFull" title="Open the full app">Full app</button><button type="button" class="ghost" id="ovHide" title="Hide (Ctrl+Shift+B)">Hide</button></span>
  </div>
  <header>''')
rep('      <div class="theme-menu">', '      <button type="button" class="ghost theme-menu-btn" id="overlayModeBtn" hidden>Overlay mode</button>\n      <div class="theme-menu">')

# 4. Remember each mode's build (also how the two windows share it), instead of publishing to the old overlay
rep("    renderPool();\n    publishOverlay();\n  }",
    "    renderPool();\n"
    "    save(M.key + \"build\", { slots: state.slots.map(s => ({ kind: s.kind, id: s.id, locked: !!s.locked })),\n"
    "      trollNote: state.trollNote || null, gambaNote: state.gambaNote || null });\n  }")
a = s.index("  // Desktop app: hand the current build (and theme colours) to the Ctrl+Shift+B overlay window.")
b = s.index("    }).catch(() => {});\n  }\n", a) + len("    }).catch(() => {});\n  }\n")
s = s[:a] + s[b:]

rep("    if (state.rolled) render(); else roll(true);\n  }",
    """    if (!state.rolled) {                                       // reopen this mode's last build if there is one
      const saved = load(M.key + "build", null);
      if (saved && Array.isArray(saved.slots) && saved.slots.length) {
        state.slots = saved.slots.filter(x => !x.id || byId[x.id]).map(x => ({ kind: x.kind, id: x.id, locked: !!x.locked }));
        state.trollNote = saved.trollNote || null; state.gambaNote = saved.gambaNote || null; state.rolled = true;
      }
    }
    if (state.rolled) render(); else roll(true);
  }""")

# 5. ARAM detected champion is remembered too (so the overlay and the app agree)
rep("      aramChamp = c;\n", "      aramChamp = c; save(\"rr.aramChamp\", c.id);\n")
rep("else { aramChamp = null; state.detectNote = null; render(); } };",
    "else { aramChamp = null; try { localStorage.removeItem(\"rr.aramChamp\"); } catch {} state.detectNote = null; render(); } };")

# 6. Desktop wiring + cross-window sync, just before the first setMode
rep('  setMode(M === MODES.aram ? "aram" : "sr");\n  if (currentChamp) scheduleChampClear();', r'''  { const saved = load("rr.aramChamp", null); aramChamp = CH.champs.find(c => c.id === saved) || null; }

  // ---------- Desktop app: overlay mode ----------
  const IS_OVERLAY = document.documentElement.classList.contains("compact");
  const desk = window.riftDesktop;
  if (desk && !IS_OVERLAY) {
    $("overlayModeBtn").hidden = false;
    $("overlayModeBtn").onclick = () => desk.setOverlayMode(true);
    desk.overlayShortcut().then(key => {
      $("overlayHint").hidden = false;
      $("overlayHint").textContent = "Overlay mode tucks Rift Roulette into the tray and gives you a small panel over League"
        + (key ? `. Press ${key} anywhere, even in game, to show or hide it.` : ".");
    }).catch(() => {});
  }
  if (desk && IS_OVERLAY) {
    $("ovFull").onclick = () => desk.setOverlayMode(false);
    $("ovHide").onclick = () => desk.hideOverlay();
    let drag = null;                                             // drag the panel by its title bar
    $("ovBar").addEventListener("pointerdown", e => {
      if (e.target.closest && e.target.closest("button")) return;
      drag = { x: e.screenX, y: e.screenY };
      try { $("ovBar").setPointerCapture(e.pointerId); } catch {}
    });
    $("ovBar").addEventListener("pointermove", e => {
      if (!drag) return;
      const dx = e.screenX - drag.x, dy = e.screenY - drag.y;
      if (!dx && !dy) return;
      drag = { x: e.screenX, y: e.screenY };
      desk.overlayDrag(dx, dy);
    });
    const endDrag = () => { if (drag) { drag = null; desk.overlayDragEnd(); } };
    $("ovBar").addEventListener("pointerup", endDrag);
    $("ovBar").addEventListener("pointercancel", endDrag);
    const dialogs = ["gamba", "caseModal", "trollPrompt"].map($);  // grow the panel while one of these is open
    const fit = () => desk.overlaySize(dialogs.some(d => !d.hidden) ? "modal" : "compact");
    dialogs.forEach(d => new MutationObserver(fit).observe(d, { attributes: true, attributeFilter: ["hidden"] }));
  }

  // The full app and the overlay are two copies of this page; they keep each other up to date
  // through saved settings (a "storage" event fires in the other window whenever one saves).
  addEventListener("storage", e => {
    if (!e.key || !e.key.startsWith("rr.")) return;
    let val = null; try { val = JSON.parse(e.newValue); } catch {}
    const modeId = () => (M === MODES.aram ? "aram" : "sr");
    if (e.key === "rr.theme") { TH.apply(val || "hextech"); renderThemeMenu(); return; }
    if (e.key === "rr.mode") { if (MODES[val] && MODES[val] !== M) setMode(val); return; }
    if (e.key === "rr.champ" || e.key === "rr.champAt") {
      const c = CH.champs.find(x => x.id === load("rr.champ", null)), at = load("rr.champAt", 0);
      if (c && at && Date.now() - at < CHAMP_TTL) { currentChamp = c; champAt = at; scheduleChampClear(); }
      else { currentChamp = null; clearTimeout(champTimer); clearInterval(champTick); }
      render(); return;
    }
    if (e.key === "rr.aramChamp") { aramChamp = CH.champs.find(c => c.id === val) || null; render(); return; }
    const m = e.key.startsWith("rr.aram.") ? MODES.aram : MODES.sr, name = e.key.slice(m.key.length);
    if (["style", "boots", "starter", "role"].includes(name)) { if (val !== null) m.state[name] = val; if (m === M) setMode(modeId()); return; }
    if (name === "bans") { m.state.bans = new Set(val || []); if (m === M) renderPool(); return; }
    if (name === "build" && val && Array.isArray(val.slots)) {
      m.state.slots = val.slots.filter(x => !x.id || m.byId[x.id]).map(x => ({ kind: x.kind, id: x.id, locked: !!x.locked }));
      m.state.trollNote = val.trollNote || null; m.state.gambaNote = val.gambaNote || null;
      m.state.rolled = true; m.state.fresh = new Set();
      if (m === M) render();
    }
  });

  setMode(M === MODES.aram ? "aram" : "sr");
  if (currentChamp) scheduleChampClear();''')
p.write_text(s, encoding="utf-8")
print("ok")
