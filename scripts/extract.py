"""Extract War Thunder propeller aircraft data from the datamine into planes.json."""
import json, os, sys, csv, re, collections

ROOT = sys.argv[1]  # path to wtdm
OUT = sys.argv[2]
J = lambda p: json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

shop = J("char.vromfs.bin_u/config/shop.blkx")
wp = J("char.vromfs.bin_u/config/wpcost.blkx")
tags = J("char.vromfs.bin_u/config/unittags.blkx")
FMDIR = os.path.join(ROOT, "aces.vromfs.bin_u/gamedata/flightmodels")
WDIR = os.path.join(ROOT, "aces.vromfs.bin_u/gamedata/weapons")

def load_lang(p):
    d = {}
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        r = csv.reader(f, delimiter=";", quotechar='"')
        for row in r:
            if len(row) > 1:
                d[row[0].lower()] = row[1]
    return d
L = load_lang("lang.vromfs.bin_u/lang/units.csv")
LW = load_lang("lang.vromfs.bin_u/lang/units_weaponry.csv")

NATION = {"country_usa": "USA", "country_germany": "Germany", "country_ussr": "USSR",
          "country_britain": "Great Britain", "country_japan": "Japan", "country_china": "China",
          "country_italy": "Italy", "country_france": "France", "country_sweden": "Sweden",
          "country_israel": "Israel"}

def br(er):
    return None if er is None else round(er / 3.0 + 1.0, 1)

def aslist(x):
    if x is None: return []
    return x if isinstance(x, list) else [x]

def jload(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None

_gun_cache = {}
def gun_info(blk):
    base = os.path.basename(blk).lower().replace(".blk", "")
    if base in _gun_cache: return _gun_cache[base]
    g = jload(os.path.join(WDIR, base + ".blkx"))
    info = None
    if g and isinstance(g, dict) and "shotFreq" in g:
        b = aslist(g.get("bullet"))
        b = b[0] if b else {}
        info = {"rof": g["shotFreq"] * 60.0, "cal": round((b.get("caliber") or 0) * 1000, 1),
                "mass": b.get("mass") or 0.0, "vel": b.get("speed")}
    _gun_cache[base] = info
    return info

def wname(blk):
    base = os.path.basename(blk).replace(".blk", "")
    n = LW.get(("weapons/" + base).lower())
    if not n:
        n = base
    return n

GUN_TRIG = {"machine gun", "cannon", "additional gun", "machine gun2"}
def classify(w):
    t = (w.get("trigger") or "").lower()
    blk = w.get("blk", "").lower()
    if t.startswith("gunner"): return "defensive"
    if t in ("bombs",) or "/bombguns/" in blk: return "bomb"
    if t == "rockets" or "rocketguns" in blk: return "rocket"
    if t == "torpedoes" or "torpedo" in blk: return "torpedo"
    if t in ("mines",): return "mine"
    if t in GUN_TRIG or "gun" in t: return "gun"
    if t in ("atgm", "aam", "agm", "guided bombs", "flares", "chaffs", "countermeasures"): return "other"
    return "other"

def preset_weapons(p):
    """Return weapons list from an old-format preset file entry."""
    blk = p.get("blk")
    if not blk: return []
    d = jload(os.path.join(FMDIR, "weaponpresets", os.path.basename(blk).lower() + "x"))
    if not d: return []
    return aslist(d.get("Weapon"))

def summarize_guns(ws):
    c = collections.OrderedDict()
    for w in ws:
        key = w["blk"]
        if key not in c: c[key] = [0, 0]
        c[key][0] += 1
        c[key][1] += int(w.get("bullets") or 0)
    parts, total_ammo, burst, cals = [], 0, 0.0, []
    for blk, (n, ammo) in c.items():
        nm = wname(blk)
        gi = gun_info(blk)
        parts.append(f"{n}× {nm}" + (f" ({ammo} rds)" if ammo else ""))
        total_ammo += ammo
        if gi:
            burst += n * gi["rof"] / 60.0 * gi["mass"]
            cals.append(gi["cal"])
    return "; ".join(parts), total_ammo, burst, (max(cals) if cals else 0), sum(v[0] for v in c.values())

def ordnance_summary(loadouts):
    """loadouts: list of weapon lists (each a distinct preset/option). Return max count per munition name by category."""
    best = {}
    for ws in loadouts:
        cnt = collections.Counter()
        for w in ws:
            cat = classify(w)
            if cat in ("bomb", "rocket", "torpedo", "mine"):
                cnt[(cat, wname(w["blk"]))] += max(1, int(w.get("bullets") or 1)) if cat != "rocket" else int(w.get("bullets") or 1)
        for k, v in cnt.items():
            best[k] = max(best.get(k, 0), v)
    out = collections.defaultdict(list)
    for (cat, nm), v in best.items():
        out[cat].append(f"{v}× {nm}")
    return {k: "; ".join(v) for k, v in out.items()}

def weapons_for(unit):
    u = jload(os.path.join(FMDIR, unit + ".blkx"))
    if not u: return None, None
    base = []
    for w in aslist((u.get("commonWeapons") or {}).get("Weapon")):
        if "blk" in w: base.append(w)
    loadouts = []
    gunpods = []
    if "WeaponSlots" in u:
        slots = aslist(u["WeaponSlots"].get("WeaponSlot"))
        # per-slot options; approximate combined loadouts by summing max per slot
        combined = collections.defaultdict(list)
        for s in slots:
            presets = aslist(s.get("WeaponPreset"))
            if "tier" not in s and presets and not presets[0].get("reqModification"):
                for w in aslist(presets[0].get("Weapon")):
                    if "blk" in w: base.append(w)
                if len(presets) == 1:
                    continue
                presets = presets[1:]
            for p in presets:
                ws = [w for w in aslist(p.get("Weapon")) if "blk" in w]
                loadouts.append(ws)
                for w in ws:
                    if classify(w) == "gun":
                        gunpods.append(wname(w["blk"]))
        # ordnance max per slot summed across slots
        totals = collections.Counter()
        for s in slots:
            presets = aslist(s.get("WeaponPreset"))
            if len(presets) == 1 and "tier" not in s and not presets[0].get("reqModification"):
                continue
            slotmax = collections.Counter()
            for p in presets:
                c = collections.Counter()
                for w in aslist(p.get("Weapon")):
                    if "blk" not in w: continue
                    cat = classify(w)
                    if cat in ("bomb", "rocket", "torpedo", "mine"):
                        c[(cat, wname(w["blk"]))] += int(w.get("bullets") or 1)
                for k, v in c.items():
                    slotmax[k] = max(slotmax[k], v)
            totals.update(slotmax)
        ords = collections.defaultdict(list)
        for (cat, nm), v in totals.items():
            ords[cat].append(f"up to {v}× {nm}")
        ord_sum = {k: "; ".join(v) for k, v in ords.items()}
    else:
        presets = aslist((u.get("weapon_presets") or {}).get("preset"))
        default_ws = preset_weapons(presets[0]) if presets else []
        base += [w for w in default_ws if classify(w) in ("gun", "defensive")]
        for p in presets:
            ws = preset_weapons(p)
            loadouts.append(ws)
            for w in ws:
                if classify(w) == "gun" and w["blk"] not in {b["blk"] for b in base}:
                    gunpods.append(wname(w["blk"]))
        o = ordnance_summary(loadouts)
        ord_sum = {k: "; ".join("up to " + x for x in v.split("; ")) for k, v in o.items()}
    off = [w for w in base if classify(w) == "gun"]
    dfn = [w for w in base if classify(w) == "defensive"]
    o_txt, o_ammo, o_burst, o_cal, o_n = summarize_guns(off)
    d_txt, d_ammo, _, _, d_n = summarize_guns(dfn)
    res = {"guns": o_txt, "gun_ammo": o_ammo, "burst_kg_s": round(o_burst, 2), "max_cal_mm": o_cal,
           "gun_count": o_n, "def_guns": d_txt, "def_ammo": d_ammo, "def_count": d_n,
           "bombs": ord_sum.get("bomb", ""), "rockets": ord_sum.get("rocket", ""),
           "torpedoes": ord_sum.get("torpedo", ""),
           "gun_pods": "; ".join(sorted(set(gunpods)))}
    return res, u.get("fmFile")

def fm_for(fmfile, unit):
    cands = []
    if fmfile:
        cands.append(os.path.join(FMDIR, "fm", os.path.basename(fmfile).lower() + "x"))
    cands.append(os.path.join(FMDIR, "fm", unit + ".blkx"))
    for c in cands:
        d = jload(c)
        if d: return d
    return None

# Walk tree
rows = []
for cty, cdata in shop.items():
    for col_i, col in enumerate(cdata["aviation"]["range"]):
        order = [0]
        def walk(d, folder):
            for k, v in d.items():
                if not isinstance(v, dict): continue
                if "rank" in v:
                    order[0] += 1
                    rows.append((cty, col_i + 1, order[0], folder, k, v))
                elif any(isinstance(x, dict) and "rank" in x for x in v.values()):
                    walk(v, k)
        walk(col, "")

out = []
skipped = collections.Counter()
for cty, col, order, folder, unit, sv in rows:
    w = wp.get(unit, {})
    t = tags.get(unit, {})
    tg = [k[5:] for k in t.get("tags", {}) if k.startswith("type_")]
    weapons, fmfile = weapons_for(unit)
    fm = fm_for(fmfile, unit)
    if fm is None:
        skipped["nofm"] += 1; continue
    engines = []
    i = 0
    while f"Engine{i}" in fm or f"EngineType{i}" in fm:
        e = fm.get(f"Engine{i}") or {}
        ty = (e.get("Main") or {}).get("Type")
        if not isinstance(ty, str):
            et = fm.get(f"EngineType{min(i, 9)}") or fm.get(f"EngineType{e.get('Type', 0)}") or fm.get("EngineType0") or {}
            ty = (et.get("Main") or {}).get("Type")
        engines.append(ty if isinstance(ty, str) else None)
        i += 1
    eng_set = set(e for e in engines if e)
    if not (eng_set & {"Inline", "Radial"}):
        skipped["jet/other:" + ",".join(sorted(eng_set))] += 1
        continue
    shp = t.get("Shop", {})
    perf = jload(os.path.join(FMDIR, "performance", unit + ".blkx")) or {}
    alts = perf.get("altSpecs", {})
    sl = (alts.get("altSpecs0") or {}).get("maxSpeed")
    mass = fm.get("Mass", {})
    em = (fm.get("EngineType0") or {}).get("Main", {})
    acq = "Tech tree"
    if sv.get("isClanVehicle"): acq = "Squadron"
    elif sv.get("event") or sv.get("marketplaceItemdefId"): acq = "Event / Marketplace"
    elif w.get("costGold") or sv.get("gift"): acq = "Premium"
    if sv.get("showOnlyWhenBought") and acq != "Tech tree": acq += " (no longer sold)"
    if acq == "Tech tree" and (w.get("costGold") or 0) > 0: acq = "Premium"
    name = L.get(unit + "_shop") or L.get(unit + "_0") or unit
    clean = lambda s: re.sub(r"[ -⯿-]", "", s).strip()
    name = clean(name)
    L[unit + "_0"] = clean(L.get(unit + "_0", name))
    rec = {
        "id": unit, "nation": NATION[cty], "rank": sv["rank"], "column": col, "order": order,
        "folder": L.get(folder + "_shop", folder.replace("_group", "").upper()) if folder else "",
        "name": name, "full_name": L.get(unit + "_0", name), "obtain": acq,
        "unit_class": (w.get("unitClass") or "").replace("exp_", ""), "type_tags": tg,
        "br_ab": br(w.get("economicRankArcade")), "br_rb": br(w.get("economicRankHistorical")),
        "br_sb": br(w.get("economicRankSimulation")),
        "research_rp": w.get("reqExp"), "cost_sl": w.get("value"), "cost_ge": w.get("costGold"),
        "crew": w.get("crewTotalCount"),
        "engines": len(engines), "engine_type": "/".join(sorted(eng_set)),
        "engine_model": " ".join(x for x in [(t.get("info", {}).get("engine1_dm") or {}).get("manufacturer", ""), (t.get("info", {}).get("engine1_dm") or {}).get("model", "")] if x).title(),
        "top_speed_kmh": round(shp["maxSpeed"] * 3.6) if shp.get("maxSpeed") else None,
        "top_speed_alt_m": round(shp["maxSpeedAlt"]) if shp.get("maxSpeedAlt") is not None else None,
        "sl_speed_kmh": round(sl * 3.6) if sl else None,
        "ceiling_m": shp.get("maxAltitude"), "turn_time_s": shp.get("turnTime"),
        "roll_rate": shp.get("rollRate"), "climb_rate_ms": shp.get("climbSpeed"),
        "climb_time_s": shp.get("climbTime"), "climb_alt_m": shp.get("climbAlt"),
        "wing_loading": shp.get("wingLoading"), "pwr": shp.get("powerToWeightRatio"),
        "takeoff_run_m": round(shp["airfieldLen"]) if shp.get("airfieldLen") else None,
        "vne_kmh": fm.get("Vne"), "vne_mach": fm.get("VneMach"),
        "empty_mass_kg": mass.get("EmptyMass"), "takeoff_mass_kg": mass.get("Takeoff"),
        "fuel_kg": mass.get("MaxFuelMass0"), "wingspan_m": fm.get("Wingspan"), "length_m": fm.get("Length"),
        "flight_time_min": w.get("maxFlightTimeMinutes"),
        "repair_ab": w.get("repairCostArcade"), "repair_rb": w.get("repairCostHistorical"),
        "rp_mult": w.get("expMul"), "sl_mult_rb": w.get("rewardMulHistorical"),
    }
    # flap rip speeds
    fl = []
    for k in ("FlapsDestructionIndSpeedP1", "FlapsDestructionIndSpeedP2", "FlapsDestructionIndSpeedP3"):
        v = mass.get(k)
        if isinstance(v, list) and len(v) > 1 and isinstance(v[1], (int, float)): fl.append(int(v[1]))
    rec["flap_limits_kmh"] = "/".join(map(str, fl))
    if weapons: rec.update(weapons)
    out.append(rec)

json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
print(len(out), "prop planes;", dict(skipped))
print(collections.Counter(r["nation"] for r in out))
