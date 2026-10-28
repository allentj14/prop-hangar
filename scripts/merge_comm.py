"""Merge community findings (community.json) into planes2.json -> planes3.json."""
import json, re, sys, collections

d = json.load(open(sys.argv[1]))
comm = json.load(open(sys.argv[2]))
fams = json.load(open(sys.argv[3]))
id2fam = {i: k for k, v in fams.items() for i in v}

def nm(r):
    n = r['name'].replace('\xa0', ' ')
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r"^[A-Za-z.]+'s ", '', n)
    n = re.sub(r'^"[^"]+"\s*', '', n)
    return n.strip()

regex = [(k[3:], v) for k, v in comm.items() if k.startswith('re:')]
regex.sort(key=lambda x: -len(x[0]))  # most specific first

def find(r):
    n = nm(r)
    for pat, e in regex:
        if re.search(pat, n):
            return e
    return comm.get(id2fam.get(r['id']))

def verdict_adj(v):
    v = (v or '').lower()
    if any(w in v for w in ('weak', 'second-rate', 'not durable', 'below average', 'mid at best')):
        return -0.05 if 'weak for its br' in v or 'below average' in v else -0.03
    if v.startswith('strong') or 'very strong' in v or 'overpowered' in v:
        return 0.05 if ('very strong' in v or 'overpowered' in v) else 0.04
    if any(w in v for w in ('exceptional', 'among the best', 'among the strongest', 'one of the strongest', 'strong for', 'strong;', 'very strong', 'outspeeds', 'far faster', 'outruns', 'out-maneuvers most', 'one of the fastest')):
        return 0.04
    if 'weak for its br' in v or 'considered weak' in v or 'struggles' in v:
        return -0.04
    return 0.0

hit = collections.Counter()
for r in d:
    e = find(r)
    r['stat_style'] = r['style']
    r['comm_style'] = r['comm_pros'] = r['comm_cons'] = r['comm_tip'] = r['comm_verdict'] = r['comm_src'] = ''
    r['perf_adj'] = 0.0
    if not e:
        hit['none'] += 1
        continue
    hit['matched'] += 1
    r['comm_style'] = e.get('style', '')
    r['comm_pros'] = e.get('pros', '')
    r['comm_cons'] = e.get('cons', '')
    r['comm_tip'] = e.get('tip', '')
    r['comm_verdict'] = e.get('verdict', '')
    r['comm_src'] = e.get('src', '')
    cs = r['comm_style']
    is_bomber = r['unit_class'] == 'bomber'
    if cs and not (is_bomber and not any(x in cs for x in ('Attacker', 'bomber'))):
        r['style'] = cs
    if r['comm_tip']:
        r['tips'] = r['comm_tip']
    r['perf_adj'] = verdict_adj(r['comm_verdict'])
    r['perf_score'] = round(r['perf_score'] + r['perf_adj'], 3)

# ---- community verification layer (verify.json next to this script) ----
import os
vpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'verify.json')
ver = json.load(open(vpath)) if os.path.exists(vpath) else {}
vregex = sorted([(k[3:], v) for k, v in ver.items() if k.startswith('re:')], key=lambda x: -len(x[0]))
def vfind(r):
    n = nm(r)
    for pat, e in vregex:
        if re.search(pat, n):
            return e
    return ver.get(id2fam.get(r['id']))
vc = collections.Counter()
for r in d:
    e = vfind(r)
    if e:
        r['verify_status'] = {'confirmed': 'Confirmed', 'adjusted': 'Adjusted', 'mixed': 'Mixed opinions'}.get(e.get('status'), e.get('status', ''))
        r['verify_note'] = e.get('note', '')
        r['verify_src'] = e.get('src', '')
        st = e.get('style')
        if st and not (r['unit_class'] == 'bomber' and not any(x in st for x in ('Attacker', 'bomber'))):
            r['style'] = st
        if e.get('verdict'):
            r['comm_verdict'] = e['verdict']
            adj = verdict_adj(e['verdict'])
            r['perf_score'] = round(r['perf_score'] - r.get('perf_adj', 0.0) + adj, 3)
            r['perf_adj'] = adj
    elif r['comm_src']:
        same = r['comm_style'] and r['comm_style'].split(' / ')[0] == r['stat_style'].split(' / ')[0]
        r['verify_status'] = 'Wiki + stats agree' if same else ('Wiki only' if r['unit_class'] != 'bomber' else 'Wiki notes')
        r['verify_note'] = '' ; r['verify_src'] = ''
    else:
        r['verify_status'] = 'Game data only' ; r['verify_note'] = '' ; r['verify_src'] = ''
    vc[r['verify_status']] += 1
print('verification:', dict(vc))

json.dump(d, open(sys.argv[4], 'w'), indent=1, ensure_ascii=False)
nb = [r for r in d if r['unit_class'] != 'bomber']
print(dict(hit), 'non-bomber matched:', sum(1 for r in nb if r['comm_src']), '/', len(nb))
chg = sum(1 for r in d if r['comm_style'] and r['style'] != r['stat_style'])
print('style changed by community:', chg)
print('unmatched non-bomber sample:', [r['name'].replace('\xa0', ' ') for r in nb if not r['comm_src']][:80])
