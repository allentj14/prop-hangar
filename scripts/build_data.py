import json, sys
import os, datetime
d=json.load(open(sys.argv[1])); lu=json.load(open(sys.argv[2])); OUTDIR=sys.argv[3]; VER=sys.argv[4] if len(sys.argv)>4 else 'unknown'
N=["USA","Germany","USSR","Great Britain","Japan","China","Italy","France","Sweden","Israel"]
nb=lambda s:(s or "").replace("\xa0"," ")
d.sort(key=lambda r:(N.index(r["nation"]),r["rank"],r["column"],r["order"]))
def em(s):
    s=(s or "").replace("_"," "); p=s.split(" ",1)
    return p[1] if len(p)==2 and p[1].lower().startswith(p[0].lower()) else s
def rn(v,p=1):
    return None if v is None else (round(v,p) if p else int(round(v)))
out=[]
for r in d:
    out.append({"id":r["id"],"n":r["nation"],"rk":r["rank"],"c":r["column"],"o":r["order"],"f":nb(r["folder"]),"nm":nb(r["name"]),"fn":nb(r["full_name"]),
      "ob":r["obtain"],"role":r["role"],"s":r["style"],"ab":r["br_ab"],"rb":r["br_rb"],"sb":r["br_sb"],
      "spd":r["top_speed_kmh"],"spa":r["top_speed_alt_m"],"sls":r["sl_speed_kmh"],"clb":rn(r["climb_rate_ms"]),"clt":rn(r["climb_time_s"],0),"cla":rn(r["climb_alt_m"],0),
      "trn":rn(r["turn_time_s"]),"rol":rn(r["roll_rate"],0),"ceil":rn(r["ceiling_m"],0),"wl":rn(r["wing_loading"],0),"pw":rn(r["pwr"],2),
      "vne":rn(r["vne_kmh"],0),"flp":r["flap_limits_kmh"] or None,"g":nb(r.get("guns")),"ga":r.get("gun_ammo") or None,"bk":r.get("burst_kg_s") or None,
      "dg":nb(r.get("def_guns")),"bo":nb(r.get("bombs")),"ro":nb(r.get("rockets")),"to":nb(r.get("torpedoes")),"gp":nb(r.get("gun_pods")),
      "eng":em(r["engine_model"]),"ne":r["engines"],"cr":r["crew"],"tom":rn(r["takeoff_mass_kg"],0),"fu":rn(r["fuel_kg"],0),"ft":r["flight_time_min"],
      "rp":r["research_rp"],"sl":r["cost_sl"] or None,"ge":r["cost_ge"],"rr":r["repair_rb"] or None,"rpm":r["rp_mult"],
      "str":r["strengths"],"tg":r.get("tags",[]),"vs":r.get("verify_status",""),"vn":r.get("verify_note",""),"vsrc":r.get("verify_src",""),"bl":r.get("bomb_load_kg"),"cp":r.get("comm_pros",""),"cc":r.get("comm_cons",""),"cv":r.get("comm_verdict",""),"ss":r.get("stat_style",""),"src":r.get("comm_src",""),"wk":r["weaknesses"],"tip":r["tips"]})
for x in lu:
    for L in [x["best"],x["tech"],x.get("step",[])]+list(x.get("styles",{}).values()):
        for p in L: p["name"]=nb(p["name"])
j=lambda o:json.dumps(o,ensure_ascii=False,separators=(",",":"))
os.makedirs(OUTDIR, exist_ok=True)
open(os.path.join(OUTDIR,"planes.json"),"w").write(j(out))
open(os.path.join(OUTDIR,"lineups.json"),"w").write(j(lu))
meta={"game_version":VER,"built":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),"planes":len(out)}
open(os.path.join(OUTDIR,"meta.json"),"w").write(json.dumps(meta))
print("ok")
