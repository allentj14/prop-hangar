"""Build recommended 5-plane lineups per nation, BR and mode."""
import json, sys

d = json.load(open(sys.argv[1]))
NATIONS = ["USA", "Germany", "USSR", "Great Britain", "Japan", "China", "Italy", "France", "Sweden", "Israel"]

def short(st):
    return (st.replace("Boom & Zoom", "BnZ").replace("Energy fighter", "Energy").replace("Turn fighter", "Turn")
              .replace("Attacker / ", "Atk/"))

def is_fighterish(r):
    return r["unit_class"] == "fighter" or r["style"].startswith("Attacker /")

def is_strike(r):
    return r["unit_class"] in ("assault", "bomber") and (r.get("bombs") or r.get("rockets") or r.get("torpedoes"))

def pick(cands, b, mode, techonly):
    key = "br_ab" if mode == "AB" else "br_rb"
    pool = [r for r in cands if (not techonly or r["obtain"] == "Tech tree")]
    def sc(r):
        s = r["perf_score"] - 0.10 * (b - r[key]) / 0.33
        if mode == "AB": s += 0.05 * r["_pct"]["fire"]
        return s
    fighters = sorted([r for r in pool if is_fighterish(r)], key=sc, reverse=True)
    strikes = sorted([r for r in pool if is_strike(r) and not is_fighterish(r)],
                     key=lambda r: sc(r) + 0.3 * r["_pct"]["speed"], reverse=True)
    chosen, names, sigs = [], set(), set()
    sig = lambda r: (r.get("guns"), r["top_speed_kmh"], r["turn_time_s"], r["climb_rate_ms"])
    # prefer tech-tree copy when a premium/event plane is a stat-identical twin
    tech_sigs = {sig(r) for r in pool if r["obtain"] == "Tech tree"}
    fighters = [r for r in fighters if r["obtain"] == "Tech tree" or sig(r) not in tech_sigs]
    strikes = [r for r in strikes if r["obtain"] == "Tech tree" or sig(r) not in tech_sigs]
    def add(r):
        if r["name"] in names or sig(r) in sigs: return False
        chosen.append(r); names.add(r["name"]); sigs.add(sig(r)); return True
    nf = 4 if mode == "AB" else 5
    for r in fighters:
        if len(chosen) >= nf: break
        add(r)
    if mode == "AB":
        for r in strikes:
            if add(r): break
    for r in fighters + strikes:  # top up
        if len(chosen) >= 5: break
        add(r)
    if chosen and not any(r[key] == b for r in chosen):
        top = [r for r in fighters + strikes if r[key] == b and r["name"] not in names]
        if top:
            chosen[min(len(chosen), 5) - 1 if len(chosen) >= 5 else len(chosen):] = []
            if len(chosen) >= 5: chosen.pop()
            chosen.insert(0, top[0])
    chosen.sort(key=lambda r: -sc(r))
    return chosen[:5]

rows = []
for n in NATIONS:
    for mode, key in (("RB", "br_rb"), ("AB", "br_ab")):
        planes = [r for r in d if r["nation"] == n and r[key] is not None]
        brs = sorted({r[key] for r in planes if is_fighterish(r) or is_strike(r)})
        for b in brs:
            cands = [r for r in planes if b - 1.0 <= r[key] <= b + 1e-9]
            best = pick(cands, b, mode, False)
            tech = pick(cands, b, mode, True)
            if len(best) < 2: continue
            styles = {}
            for skey, term in (("bnz", "Boom & Zoom"), ("nrg", "Energy fighter"), ("trn", "Turn fighter")):
                pool = [r for r in cands if term in r["style"] and is_fighterish(r)]
                styles[skey] = pick(pool, b, mode, False)[:5] if pool else []
            fmt = lambda r: {"name": r["name"], "br": r[key], "style": short(r["style"]), "obtain": r["obtain"], "id": r["id"]}
            rows.append({"nation": n, "mode": mode, "br": b, "best": [fmt(r) for r in best], "tech": [fmt(r) for r in tech],
                         "same": [r["id"] for r in best] == [r["id"] for r in tech],
                         "styles": {k: [fmt(r) for r in v] for k, v in styles.items()}})
json.dump(rows, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
print(len(rows), "lineups")
for r in rows:
    if r["nation"] == "Germany" and r["mode"] == "RB" and r["br"] in (2.0, 4.0):
        print(r["br"], [(x["name"], x["br"], x["style"], x["obtain"][:4]) for x in r["best"]])
        print("   tech:", [(x["name"], x["br"]) for x in r["tech"]])
