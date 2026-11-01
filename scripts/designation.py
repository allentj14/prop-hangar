"""Work out an aircraft's base designation so notes are only shared between true variants."""
import re, urllib.parse

# Named aircraft (British style names and export names) -> canonical family
NAMED = [
    ("sea hurricane", "HURRICANE"), ("hurricane", "HURRICANE"),
    ("seafire", "SPITFIRE"), ("spitfire", "SPITFIRE"),
    ("sea gladiator", "GLADIATOR"), ("gladiator", "GLADIATOR"),
    ("sea fury", "SEAFURY"), ("fury", "FURY"), ("nimrod", "NIMROD"),
    ("typhoon", "TYPHOON"), ("tempest", "TEMPEST"), ("mosquito", "MOSQUITO"),
    ("beaufighter", "BEAUFIGHTER"), ("whirlwind", "WHIRLWIND"), ("hornet", "HORNET"),
    ("firefly", "FIREFLY"), ("firebrand", "FIREBRAND"), ("firecrest", "FIRECREST"),
    ("boomerang", "BOOMERANG"), ("wirraway", "WIRRAWAY"), ("welkin", "WELKIN"),
    ("swordfish", "SWORDFISH"), ("wellington", "WELLINGTON"), ("lancaster", "LANCASTER"),
    ("mustang", "P51"), ("thunderbolt", "P47"), ("corsair", "F4U"), ("hellcat", "F6F"),
    ("martlet", "F4F"), ("kittyhawk", "P40"), ("tomahawk", "P40"), ("avenger", "TBF"),
    ("kingcobra", "P63"), ("catalina", "PBY"), ("mörkö-morane", "MS406"), ("morko-morane", "MS406"),
    ("hawk iii", "HAWKIII"), ("hawk h-75", "P36"),
]
# Different designations that are the same airframe family (exports, rebuilds, navy/army names)
SAME = {
    "H75": "P36", "H81": "P40", "F47": "P47", "F6C": "P51", "F51": "P51", "B239": "F2A",
    "A21": "J21", "AU": "F4U", "F2G": "F4U", "A1": "AD", "AD": "AD", "AM": "AM",
    "MS405": "MS406", "F6": "P51", "MS410": "MS406", "D501": "D500", "D510": "D500",
    "LA11": "LA9", "PO2M": "PO2", "SB2U": "SB2U", "P400": "P39",
    "ME210": "ME410",   # Me 410 was developed from the Me 210
    "G56": "G55", "AU1": "F4U", "D521": "D520", "KI108": "KI102", "MB175": "MB174",
    "POTEZ630": "POTEZ631", "MB151": "MB152", "PBJ": "B25", "B34": "B34",
}

def _norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())

def base(name):
    n = urllib.parse.unquote(name).replace(" ", " ").replace("_", " ").strip()
    n = re.sub(r"^unit/", "", n)
    n = re.sub(r"^(douglas|grumman|curtiss|lockheed|north american|republic|vought|bell)[ -]", "", n, flags=re.I)
    n = re.sub(r"^[A-Za-zÀ-ÿ.]+'s?\s+", "", n)          # owner names: "Thach's F2A-1", "Plagis' ..."
    n = re.sub(r"\s*\(.*?\)\s*", " ", n).strip()
    low = n.lower()
    for k, v in NAMED:
        if low.startswith(k):
            return v
    # Japanese navy style: B5N2, A6M5, J2M3, N1K2, D4Y1, G4M1, H8K2, E13A1
    m = re.match(r"^([A-Z]\d{1,2}[A-Z])\d", n)
    if m and not re.match(r"^[A-Z]\d{1,2}[A-Z]-", n):
        return SAME.get(_norm(m.group(1)), _norm(m.group(1)))
    n = re.sub(r"^[XY](?=P-|A-|F\d|B-)", "", n)   # prototype prefixes: XP-38, YP-38, XA-38, XF5F
    if re.match(r"^(AD|A)-\d", n) and n[:2] in ("AD", "A-") and (n.startswith("AD") or n.startswith("A-1")):
        return "AD"
    if re.match(r"^ad[\s\-]?\d", n, re.I):
        return "AD"
    if n.startswith("AM-"):
        return "AM"
    # US navy style: F4U, F6F, SB2C, TBF, SBD, OS2U, PBY, PBM, BTD, F5F, F2A, F8F, BF2C, SOC, O3U
    m = re.match(r"^([A-Z]{1,3}\d?[A-Z]{1,2})(?=[-\d\s]|$)", n)
    if m and (re.search(r"\d", m.group(1)) or len(m.group(1)) == 3):
        b = _norm(m.group(1))
        return SAME.get(b, b)
    # Hyphen/space/dot + number designations: P-38G, Ki-27, Bf 109, Do 217, D.520, M.S.406, G.55, C. 202,
    # Re.2005, IL-2, La-5FN, Yak-9T, I-16, B-17, Me 410, He 112, Ta 152, Pe-2, Su-6, Tu-2, CR.42
    m = re.match(r"^([A-Za-z][A-Za-z.]*?)[\s.\-]*(\d+)", n)
    if m:
        b = _norm(m.group(1) + m.group(2))
        return SAME.get(b, b)
    return _norm(n.split()[0]) if n else ""

def same_family(a, b):
    return bool(a) and a == b

if __name__ == "__main__":
    tests = ["P-38G-1", "XP-38G", "Ki-27 Otsu", "Ki-43-II", "B5N2", "B6N1 Model 11", "Do 217 J-1", "Ju 88 C-6",
             "Sea Hurricane Mk IB", "Spitfire Mk Vb", "Seafire LF Mk.III", "Thach's F2A-1", "B-239", "IL-10", "IL-2 (1942)",
             "douglas_ad_4", "A-1H", "AD-2", "fw-190a-1", "Fw 190 A-5", "Me 210 A-1", "Me_410_A-1/U4", "D.371", "D.500",
             "Mörkö-Morane", "M.S.406C1", "C. 202", "Re.2005 serie 0", "La-11", "La-9", "Hawk H-75A-2", "H-75A-1",
             "P-51_(Family)", "Mustang Mk IA", "F-6C-10-NA", "A21A-3", "J21A-1", "TBD-1", "TBF-1C", "Avenger Mk II",
             "SBD-3", "SB2U-2", "G5N1", "G4M1", "H6K4", "H8K2", "Ki-94-II", "Ki-87", "Ki-109", "Ki-45_tei", "I-180S",
             "I-185_(M-71)", "Yak-7B", "Yak-1B", "P-43A-1", "P-40E-1", "BF2C-1", "F3F-2", "Plagis' Spitfire LF Mk IXc",
             "G.55S", "G.56", "Po-2M", "Po-2", "Kingcobra", "P-63A-10", "F-47N-25-RE", "P-47N-15", "Corsair F Mk II", "F4U-1A"]
    for t in tests:
        print(f"{t:28} -> {base(t)}")
