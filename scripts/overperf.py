"""Find planes that punch above their BR. In-place on planes JSON.

For each mode, build an absolute performance index from raw stats (not BR-relative),
fit index vs BR across fighters, and convert each plane's index into the BR it
"plays like". Overperformance = plays-like BR minus real BR.
"""
import json, sys, statistics as stt

path = sys.argv[1]
d = json.load(open(path))

def fighterish(r):
    return r["unit_class"] == "fighter" or str(r.get("style", "")).startswith("Attacker /")

def climb(r):
    return r.get("climb_rate_ms") or ((r["climb_alt_m"] / r["climb_time_s"]) if r.get("climb_time_s") else None)

FEATS = {
    "speed": (lambda r: r.get("top_speed_kmh"), 1),
    "sl": (lambda r: r.get("sl_speed_kmh"), 1),
    "climb": (climb, 1),
    "turn": (lambda r: r.get("turn_time_s"), -1),
    "roll": (lambda r: r.get("roll_rate"), 1),
    "fire": (lambda r: (r.get("burst_kg_s") or 0) ** 0.5, 1),   # sqrt: diminishing returns
}
# Arcade rewards firepower and turning more; realistic rewards speed/climb (energy) more
W = {
    "RB": {"speed": 0.24, "sl": 0.10, "climb": 0.24, "turn": 0.16, "roll": 0.08, "fire": 0.18},
    "AB": {"speed": 0.18, "sl": 0.10, "climb": 0.16, "turn": 0.22, "roll": 0.08, "fire": 0.26},
}

DRONE = ("recon", "mq-1", "wing loong", "ucav")
pool = [r for r in d if fighterish(r) and r.get("top_speed_kmh") and climb(r) and r.get("turn_time_s")
        and not any(x in r["name"].lower() for x in DRONE) and "strike_ucav" not in r["type_tags"]]
stats = {}
for k, (f, sgn) in FEATS.items():
    vals = [f(r) for r in pool if f(r) is not None]
    stats[k] = (stt.mean(vals), stt.pstdev(vals) or 1.0)

def index(r, mode):
    s = 0.0
    for k, (f, sgn) in FEATS.items():
        v = f(r)
        if v is None:
            continue
        m, sd = stats[k]
        s += W[mode][k] * sgn * (v - m) / sd
    return s

for mode, key in (("RB", "br_rb"), ("AB", "br_ab")):
    pts = [(r[key], index(r, mode)) for r in pool if r.get(key) is not None]
    # least squares: idx = a + b*BR
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    mx, my = stt.mean(xs), stt.mean(ys)
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    for r in d:
        if r not in pool or r.get(key) is None:
            r[f"plays_like_{mode.lower()}"] = None
            r[f"over_{mode.lower()}"] = None
            continue
        raw = (index(r, mode) - a) / b
        pl = r[key] + 0.55 * (raw - r[key])
        # blend in community verdicts: strong +0.3 BR, very strong +0.5, weak -0.3
        v = (r.get("comm_verdict") or "").lower()
        if any(w in v for w in ("very strong", "overpowered", "exceptional", "beast")): pl += 0.5
        elif v.startswith("strong") or "strong for" in v or "out-maneuvers most" in v or "outspeeds" in v: pl += 0.3
        elif "weak" in v or "below average" in v or "second-rate" in v: pl -= 0.3
        # Arcade: one-hit-kill cannons (30 mm+) are deadlier with arcade aim assist
        if mode == "AB" and (r.get("max_cal_mm") or 0) >= 30 and (r.get("gun_count") or 0) > 0:
            pl += 0.3
        pl = min(pl, r[key] + 1.3)  # cap: stat cards can't justify more than this
        pl = round(pl * 3) / 3  # snap to BR steps of 0.33
        r[f"plays_like_{mode.lower()}"] = round(pl, 1)
        r[f"over_{mode.lower()}"] = round(pl - r[key], 1)
    print(mode, f"slope {b:.3f}/BR", "top overperformers:")
    top = sorted([r for r in pool if r.get(f"over_{mode.lower()}") is not None], key=lambda r: -r[f"over_{mode.lower()}"])[:25]
    for r in top:
        print(f"  {r['nation'][:7]:7} {r['name'].replace(chr(160),' '):24} BR {r[key]:<4} plays like {r[f'plays_like_{mode.lower()}']:<4} (+{r[f'over_{mode.lower()}']})")

for r in d:
    t = r.setdefault("tags", [])
    t[:] = [x for x in t if not x.startswith(("Punches above", "Overtiered"))]
    o = r.get("over_rb"); oa = r.get("over_ab")
    if o is not None and o >= 0.7:
        t.insert(0, f"Punches above its BR (plays like ~{r['plays_like_rb']:.1f} RB)")
    elif oa is not None and oa >= 0.7:
        t.insert(0, f"Punches above its BR in Arcade (~{r['plays_like_ab']:.1f} AB)")
    elif o is not None and o <= -0.7:
        t.append(f"Struggles at its BR (plays like ~{r['plays_like_rb']:.1f} RB)")

json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
