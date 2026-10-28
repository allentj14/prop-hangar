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

json.dump(d, open(sys.argv[4], 'w'), indent=1, ensure_ascii=False)
nb = [r for r in d if r['unit_class'] != 'bomber']
print(dict(hit), 'non-bomber matched:', sum(1 for r in nb if r['comm_src']), '/', len(nb))
chg = sum(1 for r in d if r['comm_style'] and r['style'] != r['stat_style'])
print('style changed by community:', chg)
print('unmatched non-bomber sample:', [r['name'].replace('\xa0', ' ') for r in nb if not r['comm_src']][:80])
