"""Add helpful tags for bombers and attackers (non-fighters). In-place on a planes JSON file."""
import json, re, sys, bisect

path = sys.argv[1]
d = json.load(open(path))

def mass_kg(name):
    m = re.search(r"([\d][\d,.]*)\s?(kg|lb)\b", name)
    if not m: return None
    v = float(m.group(1).replace(",", ""))
    return v * 0.4536 if m.group(2) == "lb" else v

def max_load(txt):
    """Best single option: max of N × mass across listed options."""
    best = 0.0
    for part in (txt or "").split("; "):
        m = re.match(r"(?:up to )?(\d+)× (.*)", part)
        if not m: continue
        mk = mass_kg(m.group(2))
        if mk: best = max(best, int(m.group(1)) * mk)
    return best

def max_count(txt):
    return max([int(x) for x in re.findall(r"(\d+)×", txt or "")] or [0])

def is_nonfighter(r):
    return r["unit_class"] in ("bomber", "assault")

pool = [r for r in d if is_nonfighter(r) and r["br_rb"] is not None]
def pct(r, key):
    v = key(r)
    if v is None: return None
    peers = sorted(key(p) for p in pool if abs(p["br_rb"] - r["br_rb"]) <= 0.7 and key(p) is not None)
    if len(peers) < 4: return None
    lo, hi = bisect.bisect_left(peers, v), bisect.bisect_right(peers, v)
    return (lo + hi) / 2 / len(peers)

for r in d:
    r["bomb_load_kg"] = round(max_load(r.get("bombs"))) or None
    tags = []
    if not is_nonfighter(r):
        r["tags"] = []
        continue
    load = r["bomb_load_kg"] or 0
    if load >= 4000: tags.append(f"Huge bomb load (~{load:,} kg)")
    elif load >= 1500: tags.append(f"Heavy bomb load (~{load:,} kg)")
    elif load >= 500: tags.append(f"Medium bomb load (~{load:,} kg)")
    elif load > 0: tags.append(f"Light bombs (~{load:,} kg)")
    if r.get("torpedoes"): tags.append(f"Torpedo ×{max_count(r['torpedoes'])} (naval)")
    if r.get("rockets"): tags.append(f"Rockets ×{max_count(r['rockets'])}")
    cal = r.get("max_cal_mm") or 0
    if cal >= 37: tags.append(f"Tank buster ({int(cal)} mm gun)")
    elif cal >= 20 and (r.get("burst_kg_s") or 0) >= 3: tags.append("Heavy forward guns")
    elif not r.get("guns") and not r.get("def_count"): tags.append("No guns at all")
    dn = r.get("def_count") or 0
    if dn >= 8: tags.append(f"Well defended ({dn} turret guns)")
    elif dn >= 3: tags.append(f"Some defence ({dn} turret guns)")
    elif dn == 0: tags.append("No rear gunner")
    sp = pct(r, lambda x: x["top_speed_kmh"])
    if sp is not None:
        if sp >= 0.75: tags.append("Fast for a bomber/attacker")
        elif sp <= 0.25: tags.append("Slow – needs escort")
    if (r.get("ceiling_m") or 0) >= 10000: tags.append("High-altitude capable")
    cl = pct(r, lambda x: x["climb_rate_ms"])
    if cl is not None and cl >= 0.8: tags.append("Climbs well for its type")
    if (r.get("crew") or 1) >= 6: tags.append(f"Big crew ({r['crew']}) – survives hits")
    if "hydroplane" in r["type_tags"]: tags.append("Floatplane – slow, long takeoff")
    if r["style"] and any(s in r["style"] for s in ("Boom & Zoom", "Energy fighter", "Turn fighter")):
        tags.append("Can dogfight")
    if r["role"] == "Dive bomber": tags.append("Precise dive bombing")
    r["tags"] = tags

json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
nf = [r for r in d if is_nonfighter(r)]
print(f"tagged {sum(1 for r in nf if r['tags'])}/{len(nf)} non-fighters")
for n in ("B-17E", "IL-2 (1942)", "Ju 87 D-3", "Lancaster B Mk I", "TBF-1C", "Hs 129 B-2", "Pe-2-31"):
    for r in d:
        if r["name"].replace("\xa0", " ") == n: print(n, "→", r["tags"]); break
