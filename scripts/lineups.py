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
    for r in fighters:  # top up with fighters only; bombers never fill empty fighter slots
        if len(chosen) >= 5: break
        add(r)
    for r in fighters:  # still short: allow same-stat variants (extra respawns), but never duplicates by name
        if len(chosen) >= 5: break
        if r["name"] not in names:
            chosen.append(r); names.add(r["name"]); r["_twin"] = True
    if chosen and not any(r[key] == b for r in chosen):
        top = [r for r in fighters if r[key] == b and r["name"] not in names]
        if top:
            chosen[min(len(chosen), 5) - 1 if len(chosen) >= 5 else len(chosen):] = []
            if len(chosen) >= 5: chosen.pop()
            chosen.insert(0, top[0])
    chosen.sort(key=lambda r: -sc(r))
    return chosen[:5]

STEPS = [round(i + f, 1) for i in range(0, 16) for f in (0.0, 0.3, 0.7)]
def ab_match_br(brs):
    """Air Arcade matchmaking BR from the official formula: A/2 + B/4 + C/4 over the 3 highest BRs.
    A lower plane counts as at most A-0.6; if it is 2.0+ below A it counts as A. Missing planes count as A-0.6.
    Result is rounded UP to the next BR step and is never more than one step below A."""
    top = sorted(brs, reverse=True)[:3]
    A = top[0]
    def eff(x):
        if x is None: return A - 0.6
        gap = A - x
        if gap >= 2.0 - 1e-9: return A
        if gap > 0.6 + 1e-9: return A - 0.6
        return x
    B = eff(top[1] if len(top) > 1 else None); C = eff(top[2] if len(top) > 2 else None)
    v = A / 2 + B / 4 + C / 4
    br = next(st for st in STEPS if st >= v - 1e-6)
    lower = max(st for st in STEPS if st < A - 1e-6) if A > 1.0 else A
    return max(br, lower)

rows = []
UNAVAILABLE = ("No longer obtainable", "Special account", "PlayStation only", "Xbox only", "Removed")
def can_get(r):
    return not str(r.get("visibility", "")).startswith(UNAVAILABLE)
for n in NATIONS:
    for mode, key in (("RB", "br_rb"), ("AB", "br_ab")):
        planes = [r for r in d if r["nation"] == n and r[key] is not None and can_get(r)]
        d_n_all = planes
        brs = sorted({r[key] for r in planes if is_fighterish(r) or is_strike(r)})
        for b in brs:
            cands = [r for r in planes if b - 1.0 <= r[key] <= b + 1e-9]
            best = pick(cands, b, mode, False)
            tech = pick(cands, b, mode, True)
            if not any(is_fighterish(r) for r in best): continue
            styles = {}
            for skey, term in (("bnz", "Boom & Zoom"), ("nrg", "Energy fighter"), ("trn", "Turn fighter")):
                pool = [r for r in cands if term in r["style"] and is_fighterish(r)]
                styles[skey] = pick(pool, b, mode, False)[:5] if pool else []
            fmt = lambda r: {"name": r["name"], "br": r[key], "style": short(r["style"]), "obtain": r["obtain"], "id": r["id"], "rk": r["rank"],
                             "strike": not is_fighterish(r)}
            ok = "over_" + mode.lower(); pk = "plays_like_" + mode.lower()
            fmt2 = lambda r: dict(fmt(r), pl=r.get(pk), ov=r.get(ok), n=r["nation"])
            # Step up: planes up to +1.0 BR that play above their BR and beat the weakest pick
            floor_pl = min((r.get(pk) or r[key]) for r in best) if best else 0
            best_ids = {r["id"] for r in best}
            above = [r for r in planes if b + 1e-9 < r[key] <= b + 1.0 + 1e-9 and is_fighterish(r)
                     and (r.get(ok) or 0) >= 0.3 and (r.get(pk) or 0) > floor_pl and r["id"] not in best_ids]
            seen, step = set(), []
            for r in sorted(above, key=lambda r: (-(r.get(pk) or 0) + 0.3 * (r[key] - b), -(r.get(ok) or 0))):
                sg = (r.get("guns"), r["top_speed_kmh"], r["turn_time_s"])
                if sg in seen: continue
                seen.add(sg); step.append(r)
                if len(step) >= 4: break
            # Undertiered: 5 planes rated AT OR BELOW this BR that play the most above their rating
            # (one plane must sit at exactly this BR so the lineup really is this BR)
            ucands = [r for r in planes if b - 1.0 - 1e-9 <= r[key] <= b + 1e-9 and is_fighterish(r)
                      and r.get(pk) is not None]
            usort = sorted(ucands, key=lambda r: (-(r.get(pk) or 0), -(r.get(ok) or 0)))
            seen, under = set(), []
            for r in usort:
                sg = (r.get("guns"), r["top_speed_kmh"], r["turn_time_s"])
                if sg in seen: continue
                seen.add(sg); under.append(r)
                if len(under) >= 5: break
            if under and not any(abs(r[key] - b) < 1e-9 for r in under):
                top = next((r for r in usort if abs(r[key] - b) < 1e-9), None)
                if top: under = [top] + under[:4]
            under.sort(key=lambda r: -(r.get(pk) or 0))
            # Carry lineup (Arcade only): one plane one step ABOVE this BR + lower planes so the
            # official average formula brings the match back down to this BR
            carry = []; carry_br = None
            if mode == "AB":
                up = [st for st in STEPS if st > b + 1e-6]
                A_br = up[0] if up else None
                tops = sorted([r for r in d_n_all if abs(r[key] - (A_br or -9)) < 1e-6 and is_fighterish(r)],
                              key=lambda r: -((r.get(pk) or r[key]) + 0.02 * (r.get(ok) or 0)))
                lows = sorted([r for r in planes if is_fighterish(r) and A_br and 0.7 - 1e-6 <= A_br - r[key] <= 1.7 + 1e-6],
                              key=lambda r: -((r.get(pk) or r[key]) + 0.3 * r["perf_score"]))
                if tops and len(lows) >= 2:
                    A = tops[0]; seen = {A["name"]}; chosen_c = [A]
                    for r in lows:
                        if r["name"] in seen: continue
                        chosen_c.append(r); seen.add(r["name"])
                        if len(chosen_c) == 3: break
                    floor_c = min(r[key] for r in chosen_c[1:])
                    fill = sorted([r for r in planes if is_fighterish(r) and r[key] <= floor_c + 1e-6 and r["name"] not in seen],
                                  key=lambda r: -((r.get(pk) or r[key]) + 0.3 * r["perf_score"]))
                    for r in fill:
                        if len(chosen_c) >= 5: break
                        chosen_c.append(r); seen.add(r["name"])
                    mb = ab_match_br([r[key] for r in chosen_c])
                    if abs(mb - b) < 1e-6:
                        carry = chosen_c; carry_br = mb
            # Watch out for: enemy planes from ANY nation you can meet (up to +1.0) that play well above their BR
            threats = [r for r in d if r.get(key) is not None and b - 0.3 - 1e-9 <= r[key] <= b + 1.0 + 1e-9 and is_fighterish(r)
                       and (r.get(ok) or 0) >= 0.6 and (r.get(pk) or 0) >= b + 0.7]
            seen, watch = set(), []
            for r in sorted(threats, key=lambda r: -((r.get(pk) or 0) - b)):
                sg = (r.get("guns"), r["top_speed_kmh"], r["turn_time_s"])
                if sg in seen: continue
                seen.add(sg); watch.append(r)
                if len(watch) >= 8: break
            rows.append({"nation": n, "mode": mode, "br": b, "best": [fmt(r) for r in best], "tech": [fmt(r) for r in tech],
                         "same": [r["id"] for r in best] == [r["id"] for r in tech],
                         "styles": {k: [fmt(r) for r in v] for k, v in styles.items()},
                         "step": [dict(fmt2(r), to=r[key]) for r in step],
                         "watch": [fmt2(r) for r in watch],
                         "under": [fmt2(r) for r in under],
                         "carry": [dict(fmt2(r), counts=(i < 3)) for i, r in enumerate(carry)], "carry_br": carry_br})
json.dump(rows, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
print(len(rows), "lineups")
for r in rows:
    if r["nation"] == "Germany" and r["mode"] == "RB" and r["br"] in (2.0, 4.0):
        print(r["br"], [(x["name"], x["br"], x["style"], x["obtain"][:4]) for x in r["best"]])
        print("   tech:", [(x["name"], x["br"]) for x in r["tech"]])

# self-check of the formula against the wiki's rule and the user's example
assert ab_match_br([3.0, 2.3, 2.3]) == 2.7
assert ab_match_br([3.0, 1.0, 1.0]) == 3.0      # planes 2.0+ below count as the top plane
assert ab_match_br([3.0, 1.7, 1.0]) == 3.0
assert ab_match_br([2.7, 2.0, 1.7]) == 2.7      # X.7 tops can't drop: 2.4 rounds back up to 2.7
assert ab_match_br([3.3, 2.7, 2.7]) == 3.0
assert ab_match_br([5.0, 3.0, 3.0]) == 5.0
assert ab_match_br([5.0, 4.0, 4.0]) == 4.7
print("formula checks ok")
