"""Add play-style labels, role, strengths/weaknesses and tips to planes.json -> planes2.json."""
import json, sys, bisect, collections

d = json.load(open(sys.argv[1]))
OV = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}

def is_bomber(r): return "bomber" in r["type_tags"] or r["unit_class"] == "bomber"
def is_attacker(r): return r["unit_class"] == "assault"
def fighter_like(r): return r["unit_class"] == "fighter"

def role(r):
    t = set(r["type_tags"])
    if is_bomber(r):
        if "torpedo" in t: return "Torpedo bomber"
        if "dive_bomber" in t: return "Dive bomber"
        if "longrange_bomber" in t: return "Heavy bomber"
        if "frontline_bomber" in t: return "Medium bomber"
        if "light_bomber" in t: return "Light bomber"
        return "Bomber"
    if is_attacker(r):
        if "torpedo" in t: return "Torpedo attacker"
        if "dive_bomber" in t: return "Dive bomber"
        return "Attacker"
    base = "Fighter"
    if "interceptor" in t: base = "Interceptor"
    elif r["engines"] >= 2: base = "Heavy fighter"
    if "hydroplane" in t: base = "Floatplane fighter"
    elif "naval_aircraft" in t: base = "Naval " + base.lower()
    return base

def climb(r):
    return r["climb_rate_ms"] or ((r["climb_alt_m"] / r["climb_time_s"]) if r["climb_time_s"] else None)

# percentiles within RB peers (+-0.7) among all prop aircraft
def pct_fn(key, higher_better=True, pool=None):
    def f(r):
        v = key(r)
        if v is None: return 0.5
        peers = [key(p) for p in (pool or d) if p["br_rb"] is not None and abs(p["br_rb"] - r["br_rb"]) <= 0.7 and key(p) is not None]
        if len(peers) < 3: return 0.5
        peers.sort()
        lo = bisect.bisect_left(peers, v); hi = bisect.bisect_right(peers, v)
        p = (lo + hi) / 2 / len(peers)
        return p if higher_better else 1 - p
    return f

# community-consensus overrides by id prefix (fighters only)
PREFIX_OV = [("fw-190a", "Boom & Zoom"), ("fw_190a", "Boom & Zoom"), ("fw-190f", "Boom & Zoom"), ("fw_190f", "Boom & Zoom"),
             ("typhoon", "Boom & Zoom"), ("tempest", "Boom & Zoom"), ("p-47", "Boom & Zoom"), ("p_47", "Boom & Zoom"),
             ("j2m", "Energy fighter"), ("xp-50", "Energy fighter / Boom & Zoom")]
fpool = [r for r in d if fighter_like(r) or is_attacker(r)]
P = {
    "speed": pct_fn(lambda r: r["top_speed_kmh"], True, fpool),
    "slspeed": pct_fn(lambda r: r["sl_speed_kmh"], True, fpool),
    "turn": pct_fn(lambda r: r["turn_time_s"], False, fpool),
    "climb": pct_fn(climb, True, fpool),
    "wl": pct_fn(lambda r: r["wing_loading"], True, fpool),
    "pwr": pct_fn(lambda r: r["pwr"], True, fpool),
    "roll": pct_fn(lambda r: r["roll_rate"], True, fpool),
    "fire": pct_fn(lambda r: r.get("burst_kg_s") or 0, True, fpool),
    "vne": pct_fn(lambda r: r["vne_kmh"], True, fpool),
}

for r in d:
    pc = {k: f(r) for k, f in P.items()}
    r["_pct"] = pc
    r["role"] = role(r)
    turn_s = 0.65 * pc["turn"] + 0.35 * (1 - pc["wl"])
    bnz_s = 0.4 * pc["speed"] + 0.25 * pc["wl"] + 0.2 * (pc["vne"] if r["vne_kmh"] else pc["speed"]) + 0.15 * pc["fire"] - 0.15 * pc["turn"]
    en_s = 0.45 * pc["climb"] + 0.3 * pc["pwr"] + 0.15 * pc["turn"] + 0.1 * pc["speed"]
    scores = {"Turn fighter": turn_s, "Boom & Zoom": bnz_s, "Energy fighter": en_s}
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    style = ranked[0][0]
    if ranked[1][1] > ranked[0][1] - 0.04:
        style = f"{ranked[0][0]} / {ranked[1][0]}"
    fighter_capable = (r.get("gun_count") or 0) > 0 and (r.get("burst_kg_s") or 0) >= 1.0 and pc["speed"] >= 0.45
    if is_bomber(r):
        style = r["role"] + (f" (can {ranked[0][0].replace(' fighter','').lower()} as fighter)" if fighter_capable and r["engines"] <= 2 and pc["turn"] > 0.3 else "")
        if not fighter_capable or "(" not in style:
            style = r["role"]
    elif is_attacker(r):
        if fighter_capable and pc["turn"] >= 0.5:
            style = f"Attacker / {ranked[0][0]}"
        elif fighter_capable and (pc["fire"] >= 0.5 or pc["speed"] >= 0.7):
            style = "Attacker / Boom & Zoom"
        else:
            style = r["role"]
    for pre, st in PREFIX_OV:
        if r["id"].lower().startswith(pre) and fighter_like(r):
            style = st
    r["style"] = OV.get(r["id"], {}).get("style", style)
    r["perf_score"] = round((pc["speed"] + pc["climb"] + pc["turn"] + 0.6 * pc["fire"] + 0.4 * pc["roll"]) / 4.0, 3)

    # strengths / weaknesses
    S, W = [], []
    def lab(k, good, bad, hi=0.75, lo=0.25):
        if pc[k] >= hi: S.append(good)
        elif pc[k] <= lo: W.append(bad)
    lab("speed", "Fast for its BR", "Slow for its BR")
    lab("climb", "Strong climb", "Weak climb")
    lab("turn", "Turns very well", "Poor turn")
    lab("roll", "Fast roll", "Slow roll", 0.8, 0.2)
    if r.get("gun_count"):
        lab("fire", "Heavy forward firepower", "Light forward firepower")
    if r["vne_kmh"] and pc["vne"] >= 0.8: S.append(f"Dives well (rips ~{int(r['vne_kmh'])} km/h)")
    elif r["vne_kmh"] and pc["vne"] <= 0.2: W.append(f"Low dive limit (rips ~{int(r['vne_kmh'])} km/h)")
    if (r.get("def_count") or 0) >= 3: S.append(f"{r['def_count']} defensive guns")
    if (r.get("max_cal_mm") or 0) >= 30: S.append(f"{int(r['max_cal_mm'])} mm cannon")
    if r.get("bombs") or r.get("rockets") or r.get("torpedoes"):
        if not is_bomber(r): S.append("Can carry ground-attack ordnance")
    if (r.get("gun_ammo") or 0) and r.get("gun_count") and r["gun_ammo"] / max(1, r["gun_count"]) < 150 and not is_bomber(r):
        W.append("Low ammo per gun")
    r["strengths"] = "; ".join(S)
    r["weaknesses"] = "; ".join(W)

    st = r["style"]
    if st.startswith("Boom & Zoom"):
        tip = "Climb to an altitude advantage, dive on targets, fire, then extend and zoom back up. Don't turn with nimble fighters."
    elif st.startswith("Energy fighter"):
        tip = "Use climb and power to stay above or equal to enemies. Trade speed and height carefully, fight in the vertical, and avoid long flat turns."
    elif st.startswith("Turn fighter"):
        tip = "Bait faster enemies into turning fights at low-medium speed. Use flaps, keep corner speed, and avoid head-ons and long dives."
    elif "bomber" in st.lower():
        tip = "Climb on the edge of the map or take the bomber spawn, hit bases/airfields, and let gunners cover your tail. Avoid fighter-heavy areas."
    elif st.startswith("Attacker"):
        tip = "Fly low to ground targets with fighter cover in mind. Use guns/rockets on soft targets and bombs on bases; leave before fighters arrive."
    else:
        tip = ""
    if is_bomber(r) and "(can" in st:
        tip += " Its forward guns are good enough to hunt bombers or ground targets in a pinch."
    r["tips"] = OV.get(r["id"], {}).get("tips", tip)
    if OV.get(r["id"], {}).get("note"):
        r["tips"] += " " + OV[r["id"]]["note"]

json.dump(d, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
c = collections.Counter(r["style"].split(" (")[0] for r in d)
print(c.most_common(30))
