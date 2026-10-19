"""One-off patch: add the champion case opening to src/page.html (Summoner's Rift tab)."""
from pathlib import Path

p = Path("src/page.html"); s = p.read_text(encoding="utf-8")

def rep(a, b):
    global s
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)

# ---------- data placeholder ----------
rep("<script>\n/*ITEM_DATA*/\n</script>", "<script>\n/*ITEM_DATA*/\n/*CHAMP_DATA*/\n</script>")

# ---------- CSS ----------
rep(".gamba-btn:not([hidden]) + .roll { margin-left: 0; }", """.gamba-btn:not([hidden]) ~ .roll { margin-left: 0; }
.gamba-btn:not([hidden]) ~ .gamba-btn { margin-left: 0; }
/* Champion case: CS-style reel. Rarity colours are the familiar case-opening tiers, the same in every theme. */
.case-panel { width: min(100%, 780px); }
.case-window { position: relative; height: 156px; overflow: hidden; border: 1px solid var(--line); background: var(--void);
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent); mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent); }
.case-strip { position: absolute; top: 10px; left: 0; display: flex; will-change: transform; }
.case-card { flex: none; width: 112px; height: 134px; margin-right: 8px; display: grid; grid-template-rows: 96px 1fr; justify-items: center; align-items: center;
  background: linear-gradient(180deg, color-mix(in srgb, var(--rar) 22%, var(--panel)), var(--panel)); border-bottom: 4px solid var(--rar); }
.case-card img { width: 88px; height: 88px; margin-top: 6px; }
.case-card span { font-size: 12px; font-weight: 600; max-width: 104px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.case-card.won { box-shadow: 0 0 0 2px var(--rar), 0 0 28px var(--rar); }
.case-marker { position: absolute; top: 0; bottom: 0; left: 50%; width: 2px; margin-left: -1px; background: var(--gold); box-shadow: 0 0 8px var(--gold); }
.case-marker::before, .case-marker::after { content: ""; position: absolute; left: -7px; border: 8px solid transparent; }
.case-marker::before { top: 0; border-top-color: var(--gold); }
.case-marker::after { bottom: 0; border-bottom-color: var(--gold); }
.case-result { display: flex; gap: 14px; align-items: center; min-height: 64px; }
.case-result img { width: 64px; height: 64px; border: 2px solid var(--rar); }
.case-result b { font-family: var(--display); font-size: 22px; color: var(--rar); letter-spacing: .03em; }
.case-result small { display: block; color: var(--muted); font-size: 13px; }
.case-tier { font-family: var(--cond); text-transform: uppercase; letter-spacing: .1em; font-size: 12px; color: var(--rar); }
@media (prefers-reduced-motion: reduce) { .case-card.won { box-shadow: 0 0 0 2px var(--rar); } }""")

# ---------- HTML ----------
rep('      <button class="ghost gamba-btn" id="gambaBtn" type="button" hidden>Gamba</button>',
    '      <button class="ghost gamba-btn" id="caseBtn" type="button" hidden>Open case</button>\n'
    '      <button class="ghost gamba-btn" id="gambaBtn" type="button" hidden>Gamba</button>')
rep('    <p class="gamba-note" id="gambaNote" hidden></p>',
    '    <p class="gamba-note" id="gambaNote" hidden></p>\n    <p class="gamba-note" id="champNote" hidden></p>')
rep('  <div class="gb-overlay" id="gamba" hidden>', '''  <div class="gb-overlay" id="caseModal" hidden>
    <div class="gb-panel case-panel" role="dialog" aria-modal="true" aria-labelledby="caseTitle">
      <div class="gb-head">
        <div>
          <h2 id="caseTitle">Champion case</h2>
          <p id="caseSub">Open the case for a random champion.</p>
        </div>
        <button type="button" class="icon-btn" id="caseClose" aria-label="Close champion case" title="Close (Esc)"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
      </div>
      <div class="case-window" id="caseWindow"><div class="case-strip" id="caseStrip"></div><div class="case-marker"></div></div>
      <div class="case-result" id="caseResult" role="status"></div>
      <div class="gb-actions" id="caseActions"></div>
    </div>
  </div>

  <div class="gb-overlay" id="gamba" hidden>''')

# ---------- JS ----------
rep("  // ---------- Augment picker (ARAM) ----------", r"""  // ---------- Champion case (Summoner's Rift) ----------
  // Every champion has the same chance; the rarity stripe is cosmetic, taken from Riot's difficulty rating.
  const CH = window.CHAMP_DATA;
  const TIERS = [
    { max: 3, name: "Mil-Spec", color: "#4b69ff" }, { max: 5, name: "Restricted", color: "#8847ff" },
    { max: 7, name: "Classified", color: "#d32ce6" }, { max: 9, name: "Covert", color: "#eb4b4b" },
    { max: 10, name: "Extraordinary", color: "#e4ae39" },
  ];
  const tierOf = c => TIERS.find(t => c.difficulty <= t.max);
  const CARD_W = 120, STRIP_LEN = 64, WIN_AT = 56;
  let caseSpinning = false, caseRaf = 0, caseAudio = null, caseOpener = null;
  const caseLast = { champ: null };

  function caseSound(kind) {
    try {
      caseAudio = caseAudio || new (window.AudioContext || window.webkitAudioContext)();
      const ctx = caseAudio, t = ctx.currentTime, g = ctx.createGain(); g.connect(ctx.destination);
      if (kind === "tick") {
        const o = ctx.createOscillator(); o.type = "square"; o.frequency.value = 1700;
        g.gain.setValueAtTime(0.035, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.03);
        o.connect(g); o.start(t); o.stop(t + 0.035);
      } else {
        [659, 988].forEach((f, i) => {
          const o = ctx.createOscillator(), gg = ctx.createGain(); o.type = "triangle"; o.frequency.value = f;
          gg.gain.setValueAtTime(0.0001, t + i * 0.09); gg.gain.exponentialRampToValueAtTime(0.12, t + i * 0.09 + 0.02);
          gg.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.09 + 0.5);
          o.connect(gg); gg.connect(ctx.destination); o.start(t + i * 0.09); o.stop(t + i * 0.09 + 0.55);
        });
      }
    } catch {}
  }

  const cardHTMLc = c => `<div class="case-card" style="--rar:${tierOf(c).color}"><img src="${CH.icons[c.id]}" alt=""><span>${esc(c.name)}</span></div>`;
  function buildStrip(winner) {
    const items = Array.from({ length: STRIP_LEN }, () => pick(CH.champs));
    items[WIN_AT] = winner;
    $("caseStrip").innerHTML = items.map(cardHTMLc).join("");
    $("caseStrip").style.transform = "translateX(0px)";
  }

  function spinCase(forcedId) {
    if (caseSpinning) return;
    const winner = (forcedId && CH.champs.find(c => c.id === forcedId)) || pick(CH.champs);
    buildStrip(winner);
    caseSpinning = true;
    $("caseResult").innerHTML = ""; $("caseResult").style.removeProperty("--rar");
    $("caseActions").innerHTML = `<button type="button" class="ghost" disabled>Opening…</button>`;
    const win = $("caseWindow").clientWidth;
    const jitter = (Math.random() - 0.5) * (CARD_W - 30);           // don't always stop dead centre
    const target = WIN_AT * CARD_W + 56 - win / 2 + jitter;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dur = reduced ? 900 : 6200, t0 = performance.now();
    const ease = x => 1 - Math.pow(1 - x, 4);                       // fast start, long slow finish
    let lastIdx = -1;
    const frame = now => {
      const k = Math.min(1, (now - t0) / dur), x = target * ease(k);
      $("caseStrip").style.transform = `translateX(${-x}px)`;
      const idx = Math.floor((x + win / 2) / CARD_W);
      if (idx !== lastIdx) { if (lastIdx >= 0 && !reduced) caseSound("tick"); lastIdx = idx; }
      if (k < 1) { caseRaf = requestAnimationFrame(frame); return; }
      caseSpinning = false; caseRaf = 0;
      revealCase(winner);
    };
    caseRaf = requestAnimationFrame(frame);
  }

  function revealCase(c) {
    const tier = tierOf(c);
    $("caseStrip").children[WIN_AT].classList.add("won");
    caseSound("reveal");
    caseLast.champ = c;
    MODES.sr.state.champ = c;
    $("caseResult").style.setProperty("--rar", tier.color);
    $("caseResult").innerHTML = `<img src="${CH.icons[c.id]}" alt=""><div><span class="case-tier">${tier.name}</span><b>${esc(c.name)}</b><small>${esc(c.title)} · ${c.tags.map(esc).join(" / ")}</small></div>`;
    $("caseActions").innerHTML = `<button type="button" class="roll small" data-c="again">Open another</button><button type="button" class="ghost" data-c="keep">Play ${esc(c.name)}</button>`;
    $("caseActions").querySelector("button").focus();
    render();
  }

  function openCase() {
    caseOpener = document.activeElement;
    $("caseModal").hidden = false; document.body.classList.add("gb-open");
    $("caseSub").textContent = `Open the case for a random champion. All ${CH.champs.length} champions from patch ${CH.patch} have the same chance.`;
    spinCase();
  }
  function closeCase() {
    if (caseRaf) cancelAnimationFrame(caseRaf);            // closing mid-spin abandons that opening
    caseSpinning = false; caseRaf = 0;
    $("caseModal").hidden = true; document.body.classList.remove("gb-open");
    if (caseOpener && caseOpener.focus) caseOpener.focus();
  }
  $("caseBtn").onclick = openCase;
  $("caseClose").onclick = closeCase;
  $("caseModal").addEventListener("click", e => {
    if (e.target === $("caseModal")) { closeCase(); return; }
    const b = e.target.closest("[data-c]"); if (!b) return;
    if (b.dataset.c === "again") spinCase(); else closeCase();
  });
  document.addEventListener("keydown", e => { if (!$("caseModal").hidden && e.key === "Escape") closeCase(); });
  window.RR_CASE = { spin: spinCase, open: openCase, close: closeCase, last: caseLast, tierOf, get spinning() { return caseSpinning; } };

  // ---------- Augment picker (ARAM) ----------""")

# show champion note on SR, show/hide button per mode
rep('    $("gambaNote").hidden = !state.gambaNote; $("gambaNote").textContent = state.gambaNote || "";',
    '    $("gambaNote").hidden = !state.gambaNote; $("gambaNote").textContent = state.gambaNote || "";\n'
    '    $("champNote").hidden = !state.champ;\n'
    '    if (state.champ) $("champNote").textContent = `Champion from the case: ${state.champ.name}, ${state.champ.title}.`;')
rep('    $("gambaBtn").hidden = id !== "aram";', '    $("gambaBtn").hidden = id !== "aram";\n    $("caseBtn").hidden = id !== "sr";')
p.write_text(s, encoding="utf-8")
print("ok")
