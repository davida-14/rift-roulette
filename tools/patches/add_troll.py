"""One-off patch: add the Full Troll build style and share the case champion across both tabs."""
from pathlib import Path

p = Path("src/page.html"); s = p.read_text(encoding="utf-8")

def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)

# ---------- styles ----------
rep('styles: ["Chaos", "AD", "AP", "Bruiser", "Tank", "Support"],', 'styles: ["Chaos", "AD", "AP", "Bruiser", "Tank", "Support", "Full Troll"],')
rep('styles: ["Chaos", "AD", "AP", "Health", "Resistances", "Support"],', 'styles: ["Chaos", "AD", "AP", "Health", "Resistances", "Support", "Full Troll"],')

# ---------- one champion for both tabs ----------
rep("    MODES.sr.state.champ = c; save(\"rr.champ\", c.id);", "    currentChamp = c; save(\"rr.champ\", c.id);")
rep('  $("ccClear").onclick = () => { MODES.sr.state.champ = null;', '  $("ccClear").onclick = () => { currentChamp = null;')
rep('{ const saved = load("rr.champ", null); MODES.sr.state.champ = CH.champs.find(c => c.id === saved) || null; }',
    '{ const saved = load("rr.champ", null); currentChamp = CH.champs.find(c => c.id === saved) || null; }')
rep("    const ch = state.champ;", "    const ch = currentChamp;")
rep('    $("caseBtn").hidden = id !== "sr";', '    $("caseBtn").hidden = false;')

# ---------- Full Troll pools ----------
rep("""  function starterPool() {
    let ids;""", """  function starterPool() {
    if (state.style === TROLL) return trollStarterPool();
    let ids;""")
rep("  const bootsPool = () => D.boots.map(b => b.id).filter(i => !state.bans.has(i));",
    "  const bootsPool = () => state.style === TROLL ? trollBootsPool() : D.boots.map(b => b.id).filter(i => !state.bans.has(i));")
rep("""  function legendaryPool() {
    return D.legendary""", """  function legendaryPool() {
    if (state.style === TROLL) return trollLegendaryPool();
    return D.legendary""")

rep("  function layout() {", r"""  // ---------- Full Troll: the most anti-synergy build we can find ----------
  // With a champion: every item is scored against what that champion needs (damage type, resource,
  // range, role) and the build is drawn from the worst dozen. Without one: pure items from clashing camps.
  const TROLL = "Full Troll";
  let currentChamp = null, trollAnyway = false, pendingTroll = false;
  function feats(it) {
    const has = re => it.stats.some(x => re.test(x));
    return { ad: has(/^\d+ Attack Damage$/), ap: has(/^\d+ Ability Power$/), as: has(/Attack Speed$/), crit: has(/Critical Strike Chance$/),
      leth: has(/Lethality$/), mpen: has(/Magic Penetration$/), hp: has(/^\d+ Health$/), armor: has(/^\d+ Armor$/), mr: has(/^\d+ Magic Resist$/),
      mana: has(/^\d+ Mana$/), hsp: has(/Heal and Shield Power$/), mregen: has(/Base Mana Regen$/) };
  }
  const profile = c => ({ ap: c.magic > c.attack, tank: c.tags.includes("Tank"), supp: c.tags.includes("Support"),
    marks: c.tags.includes("Marksman"), ranged: c.range > 300, manaless: c.partype !== "Mana" });
  function trollScore(it, c) {
    const f = feats(it), pr = profile(c), why = []; let sc = 0;
    if (pr.ap) { if (f.ad || f.crit || f.as || f.leth) { sc += 3; why.push("AD and crit on an AP champion"); } if (f.ap) sc -= 6; }
    else { if (f.ap || f.mpen) { sc += 3; why.push("AP on an AD champion"); } if (f.ad || f.crit) sc -= 6; }
    if (pr.tank) { if (f.crit || f.leth) { sc += 2; why.push("glass-cannon stats on a tank"); } if (f.hp || f.armor || f.mr) sc -= 3; }
    if (pr.manaless && f.mana) { sc += 3; why.push(`mana on a champion who uses ${c.partype && c.partype !== "None" ? c.partype.toLowerCase() : "no resource"}`); }
    if (!pr.supp && (f.hsp || f.mregen)) { sc += 2; why.push("support stats on a carry"); }
    if (pr.ranged && /Hydra/.test(it.name)) { sc += 3; why.push("a melee Hydra on a ranged champion"); }
    if (!pr.ranged && it.name === "Runaan's Hurricane") { sc += 4; why.push("Runaan's on a melee champion (it only works at range)"); }
    return { sc, why };
  }
  function trollLegendaryPool() {
    const items = D.legendary.filter(i => !state.bans.has(i.id));
    if (!currentChamp) {
      return items.filter(i => { const f = feats(i);
        return [f.ad || f.crit, f.ap, (f.hp || f.armor || f.mr) && !f.ad && !f.ap, f.hsp || f.mregen].filter(Boolean).length === 1; }).map(i => i.id);
    }
    return items.map(i => ({ id: i.id, sc: trollScore(i, currentChamp).sc + Math.random() * 1.5 }))
      .sort((a, b) => b.sc - a.sc).slice(0, 12).map(x => x.id);
  }
  function trollBootsPool() {
    const c = currentChamp, pr = c && profile(c);
    // Attack-speed boots on mages, magic-pen boots on attackers, no defensive boots for tanks.
    const ids = !c ? ["3006", "3020"] : pr.ap ? ["3006"] : pr.tank ? ["3006", "3020"] : ["3020"];
    const ok = ids.filter(i => !state.bans.has(i) && D.boots.some(b => b.id === i));
    return ok.length ? ok : D.boots.map(b => b.id).filter(i => !state.bans.has(i));
  }
  function trollStarterPool() {
    const c = currentChamp, ap = c && profile(c).ap;
    let ids;
    if (!M.roles) ids = !c ? D.starter.map(x => x.id) : ap ? ["3177", "3184"] : ["3112"];        // ARAM: wrong Guardian's item
    else if (state.role === "Jungle") ids = !c ? ["1055", "1056"] : ap ? ["1055"] : ["1056"];   // jungler with a lane item
    else ids = D.starter.filter(x => x.role === "jungle").map(x => x.id);                        // laner with a jungle pet
    const ok = ids.filter(i => !state.bans.has(i));
    return ok.length ? ok : D.starter.map(x => x.id).filter(i => !state.bans.has(i));
  }
  function trollSummary() {
    if (!currentChamp) return "Full Troll with no target: clashing AD, AP, tank and support items all in one build.";
    const why = [];
    state.slots.forEach(sl => { const it = byId[sl.id]; if (it && sl.kind === "legendary") trollScore(it, currentChamp).why.forEach(w => { if (!why.includes(w)) why.push(w); }); });
    const boots = state.slots.find(sl => sl.kind === "boots" && sl.id);
    if (boots) why.push(`${byId[boots.id].name} for boots`);
    return `Full Troll vs ${currentChamp.name}: ${why.join(", ") || "nothing it wants"}.`;
  }
  function openTrollPrompt() {
    $("trollPrompt").hidden = false; document.body.classList.add("gb-open");
    $("tpCase").focus();
  }
  function closeTrollPrompt() { $("trollPrompt").hidden = true; document.body.classList.remove("gb-open"); }

  function layout() {""")

# roll(): ask for a champion first; write the troll summary after rolling
rep("""  function roll() {
    const kinds = layout();""", """  function roll() {
    if (state.style === TROLL && !currentChamp && !trollAnyway) { openTrollPrompt(); return; }
    const kinds = layout();""")
rep("""    state.rolled = true;
    render(notes);""", """    state.rolled = true;
    state.trollNote = state.style === TROLL ? trollSummary() : null;
    render(notes);""")
rep('    $("gambaNote").hidden = !state.gambaNote; $("gambaNote").textContent = state.gambaNote || "";',
    '    $("gambaNote").hidden = !state.gambaNote; $("gambaNote").textContent = state.gambaNote || "";\n'
    '    $("trollNote").hidden = !state.trollNote; $("trollNote").textContent = state.trollNote || "";')

# after the case closes on a troll request, roll the troll build for the new champion
rep("""    $("caseModal").hidden = true; document.body.classList.remove("gb-open");
    if (caseOpener && caseOpener.focus) caseOpener.focus();
  }""", """    $("caseModal").hidden = true; document.body.classList.remove("gb-open");
    if (caseOpener && caseOpener.focus) caseOpener.focus();
    if (pendingTroll && currentChamp) { pendingTroll = false; roll(); }
  }""")
rep('  $("caseBtn").onclick = openCase;', '''  $("caseBtn").onclick = openCase;
  $("tpCase").onclick = () => { closeTrollPrompt(); pendingTroll = true; openCase(); };
  $("tpAnyway").onclick = () => { closeTrollPrompt(); trollAnyway = true; roll(); };
  $("tpClose").onclick = closeTrollPrompt;
  $("trollPrompt").addEventListener("click", e => { if (e.target === $("trollPrompt")) closeTrollPrompt(); });
  document.addEventListener("keydown", e => { if (!$("trollPrompt").hidden && e.key === "Escape") closeTrollPrompt(); });''')
rep("  window.RR_CASE = {", "  window.RR_TROLL = { score: (id, champId) => trollScore(byId[id], CH.champs.find(c => c.id === champId)), feats: id => feats(byId[id]) };\n  window.RR_CASE = {")

# ---------- markup ----------
rep('    <p class="gamba-note" id="gambaNote" hidden></p>',
    '    <p class="gamba-note" id="gambaNote" hidden></p>\n    <p class="gamba-note troll-note" id="trollNote" hidden></p>')
rep('  <div class="gb-overlay" id="caseModal" hidden>', '''  <div class="gb-overlay" id="trollPrompt" hidden>
    <div class="gb-panel troll-panel" role="dialog" aria-modal="true" aria-labelledby="tpTitle">
      <div class="gb-head">
        <div>
          <h2 id="tpTitle">Pick a victim</h2>
          <p>Full Troll works best against a specific champion. Open the case to get one, and the build is rolled to ruin them.</p>
        </div>
        <button type="button" class="icon-btn" id="tpClose" aria-label="Close" title="Close (Esc)"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
      </div>
      <div class="gb-actions">
        <button type="button" class="roll small" id="tpCase">Open the case</button>
        <button type="button" class="ghost" id="tpAnyway">Troll without a champion</button>
      </div>
    </div>
  </div>

  <div class="gb-overlay" id="caseModal" hidden>''')
rep(".case-panel { width: min(100%, 780px); }", ".case-panel { width: min(100%, 780px); }\n.troll-panel { width: min(100%, 480px); }\n.troll-note { color: var(--ban); }")
p.write_text(s, encoding="utf-8")
print("ok")
