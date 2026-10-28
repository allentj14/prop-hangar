import json,re,collections,sys
d=json.load(open(sys.argv[1]))
def nm(r):
    n=r['name'].replace('\xa0',' '); n=re.sub(r'\(.*?\)','',n); n=re.sub(r"^[A-Za-z.]+'s ",'',n); n=re.sub(r'^"[^"]+"\s*','',n)
    return n.strip()
def famkey(n):
    n=n.replace('/trop','').replace('/','-')
    t=n.split()
    if len(t)>=3 and t[0] in ('Bf','Fw','Me','Ju','Do','He','Ta','Hs','Ar','BV','Mk','Ki'): base=' '.join(t[:3]) ; base=re.sub(r'(\d)[\-.].*$',r'\1',base); return re.sub(r'(\w)-\d+$',r'\1',base)
    if t[0].startswith('Spitfire') or t[0] in('Seafire','Hurricane','Sea','Typhoon','Tempest','Firefly','Beaufighter','Mosquito','Whirlwind','Hornet','Fury','Defiant','Gladiator','Nimrod','Fulmar','Martlet','Corsair','Hellcat','Wyvern','Firebrand','Barracuda','Swordfish','Wirraway','Boomerang','Mustang','Kittyhawk','Tomahawk'):
        return ' '.join(t[:3]) if len(t)>2 and t[1] in('Mk','F','LF','FR','HF','FB','NF','Hurricane','Fury','Hornet') else ' '.join(t[:2])
    k=t[0]
    k=re.sub(r'^([A-Za-z]+-?\d+[A-Za-z]?)[-_].*$',r'\1',k)
    if len(t)>1 and re.match(r'^(type|M-|mod|serie|AS|Hei|Ko|Otsu|Tei|II|III|I|IV|V)',t[1]) and not k.startswith(('Ki','A6M')):
        k+=' '+t[1]
    if k.startswith('Ki-') and len(t)>1: k+=' '+t[1].split('-')[0] if t[1] in ('II','I','III','IV') else ''
    return k
fams=collections.OrderedDict()
for r in d:
    fams.setdefault(famkey(nm(r)),[]).append(r['id'])
if __name__=='__main__':
    print(len(fams))
    for k,v in fams.items(): print(k,'|',len(v))
json.dump({k:v for k,v in fams.items()},open(sys.argv[2],'w'),indent=0)
