"""Parse the NHSEB 2026-2027 Regional Case Set into the site's content layer.

Produces site/data/cases.json: the official case text (fixed, from NHSEB) plus an
empty scaffold for student/class content. Nothing from the teacher's private case
analysis documents is read or written here.
"""
import pypdf, re, json, unicodedata, pathlib

SRC = "/Users/sfitzpatrick/Desktop/PARA2026/Ethics Bowl Site Build/Cases/Regional+Case+Set+(2026-2027)-+SECURED.pdf"
OUT = pathlib.Path("/Users/sfitzpatrick/Desktop/PARA2026/Ethics Bowl Site Build/site/data")
LIG = {"ﬀ":"ff","ﬁ":"fi","ﬂ":"fl","ﬃ":"ffi","ﬄ":"ffl","ﬅ":"ft","ﬆ":"st"}

def clean(s):
    for k, v in LIG.items():
        s = s.replace(k, v)
    return unicodedata.normalize("NFC", s).replace(" ", " ")

def despace(t):
    """Layout extraction inserts a space before elided forms: "Timmy 's" -> "Timmy's"."""
    t = re.sub(r"(\w)\s+(['\u2019](?:s|d|ll|re|ve|t|m)\b)", r"\1\2", t)
    t = re.sub(r"\s+([,.;:?!])", r"\1", t)
    t = re.sub(r"\s+([”’])", r"\1", t)          # 'family ”' -> 'family”'
    t = re.sub(r"([“‘])\s+", r"\1", t)
    return t

reader = pypdf.PdfReader(SRC)
raw_pages = [clean(p.extract_text() or "") for p in reader.pages]                      # titles/TOC
lay_pages = [clean(p.extract_text(extraction_mode="layout") or "") for p in reader.pages]

# ---- TOC: authoritative titles + divisional-playoff flags ----
toc = {}
for m in re.finditer(r"^\s*(\d{2})\s+(.+?)(\*?)\s*$", raw_pages[1], re.M):
    n = int(m.group(1))
    if 1 <= n <= 15:
        toc[n] = {"title": m.group(2).strip(), "playoff": m.group(3) == "*"}
assert len(toc) == 15, f"TOC parsed {len(toc)} entries"

# ---- case pages only: drop front matter and the back cover ----
def is_case_page(t):
    if "#NHSEB" in t and "EAST CAMERON" in t:   # back cover
        return False
    if "FROM THE EDITORIAL BOARD" in t or "CASES FOR REGIONAL" in t:
        return False
    return bool(re.search(r"^\s*(\d{1,2}):\s+\S", t, re.M))

# link annotations per page, top-to-bottom (footnotes are often hyperlinked titles)
annot_urls = {}
for pno, page in enumerate(reader.pages):
    got = []
    for a in (page.get("/Annots") or []):
        try:
            o = a.get_object(); A = o.get("/A")
            if A and A.get("/URI"):
                got.append((float(o.get("/Rect", [0, 0, 0, 0])[1]), str(A["/URI"])))
        except Exception:
            pass
    annot_urls[pno] = [u for _, u in sorted(got, key=lambda t: -t[0])]

lines, seen_pages = [], []
for pno, t in enumerate(lay_pages):
    if not is_case_page(t):
        continue
    seen_pages.append(pno)
    for l in t.split("\n"):
        lines.append((pno, l.rstrip()))

starts, seen = [], set()
for i, (pno, ln) in enumerate(lines):
    m = re.match(r"^\s*(\d{1,2}):\s+(.+?)\s*$", ln)
    if m and 1 <= int(m.group(1)) <= 15 and int(m.group(1)) not in seen:
        seen.add(int(m.group(1)))
        starts.append((int(m.group(1)), i))
assert len(starts) == 15, f"found {len(starts)} case headings"

FOOTNOTE = re.compile(r"^(\d{1,2})\s+(\S.*)$")      # "1 Reuters, “…” (https://…)"
DQ_START = re.compile(r"^\s*(\d)\.\s+(.*)$")        # "   1.    Should residents…"

cases = []
for idx, (num, start_i) in enumerate(starts):
    end_i = starts[idx + 1][1] if idx + 1 < len(starts) else len(lines)
    body_pp = lines[start_i + 1:end_i]
    # a line holding nothing but 1-2 digits is the page-number footer, never content
    body_pp = [(pno, ln) for pno, ln in body_pp if not re.fullmatch(r"\s*\d{1,2}\s*", ln)]
    body = [ln for _, ln in body_pp]
    case_pages = sorted({pno for pno, _ in body_pp})

    # locate the discussion-question header and the footnote block
    try:
        dq_at = next(i for i, l in enumerate(body) if "DISCUSSION QUESTIONS" in l)
    except StopIteration:
        dq_at = len(body)

    fn_at = len(body)
    for i in range(dq_at, len(body)):
        m = FOOTNOTE.match(body[i])
        if not (m and m.group(1) == "1"):
            continue
        # confirm: the numbered lines from here on ascend 1,2,3,…
        nums = [int(mm.group(1)) for mm in
                (FOOTNOTE.match(l) for l in body[i:]) if mm]
        if nums == list(range(1, len(nums) + 1)) and nums:
            fn_at = i
            break

    narr_lines = body[:dq_at]
    dq_lines   = body[dq_at + 1:fn_at]
    fn_lines   = body[fn_at:]

    # ---- footnotes: a numbered line, with continuation lines appended ----
    sources, cur = [], None
    for l in fn_lines:
        if not l.strip():
            continue
        m = FOOTNOTE.match(l)
        if m:
            if cur:
                sources.append(cur)
            cur = {"n": int(m.group(1)), "text": m.group(2).strip()}
        elif cur:
            cur["text"] = (cur["text"].rstrip() + l.strip())   # wrapped URLs split mid-token
    if cur:
        sources.append(cur)

    pagenums = {str(num), f"{num:02d}"}
    def unglue(t):
        """The page-number footer can glue onto the end of a footnote."""
        for pn in sorted(pagenums, key=len, reverse=True):
            if t.endswith(pn) and len(t) > len(pn):
                return t[:-len(pn)]
        return t

    for s in sources:
        txt = unglue(s["text"].rstrip())
        u = re.search(r"\((https?://[^)]+)\)|(https?://\S+)", txt)
        s["url"] = unglue((u.group(1) or u.group(2)).rstrip(").,")) if u else None
        t = re.sub(r"\s*\((?:https?://[^)]*)\)?\s*$", "", txt).strip().rstrip(",.")
        s["title"] = None if (not t or t == s["url"] or t.startswith("http")) else t
        del s["text"]

    # "Ibid" inherits the previous source; a repeated title reuses its first URL
    by_title = {}
    for i, s in enumerate(sources):
        if s["title"] and s["url"]:
            by_title.setdefault(s["title"], s["url"])
    for i, s in enumerate(sources):
        if s["url"]:
            continue
        if s["title"] and s["title"].lower().startswith("ibid") and i > 0:
            s["url"], s["title"] = sources[i - 1]["url"], sources[i - 1]["title"]
        elif s["title"] in by_title:
            s["url"] = by_title[s["title"]]
    if sources and not any(s["url"] for s in sources):
        pool = [u for pno in case_pages for u in annot_urls.get(pno, [])]
        if len(pool) == len(sources):
            for s, u in zip(sources, pool):
                s["url"] = u
    fn_nums = {s["n"] for s in sources}

    # ---- strip inline superscript markers ("Nucleus Genomics.1" -> "Nucleus Genomics.") ----
    def strip_super(t):
        def f(m):
            return m.group(1) if int(m.group(2)) in fn_nums else m.group(0)
        return re.sub(r'([A-Za-z”’"\)\].,;:])(?<!\d)(\d{1,2})(?!\d)(?=[\s,.;:?!)”’]|$)', f, t)

    # ---- paragraphs: blank lines are real breaks in layout mode ----
    paras, buf = [], []
    for l in narr_lines:
        if l.strip():
            buf.append(l.strip())
        elif buf:
            p = re.sub(r"\s+", " ", " ".join(buf)).strip()
            if len(p) > 40:
                paras.append(despace(strip_super(p)))
            buf = []
    if buf:
        p = re.sub(r"\s+", " ", " ".join(buf)).strip()
        if len(p) > 40:
            paras.append(despace(strip_super(p)))

    # a "paragraph" opening in lower case is a continuation the extractor split
    merged = []
    for para in paras:
        if merged and para[:1].islower():
            merged[-1] = merged[-1].rstrip() + " " + para
        else:
            merged.append(para)
    paras = merged

    # ---- discussion questions ----
    questions, cur_q = [], None
    for l in dq_lines:
        if not l.strip():
            continue
        m = DQ_START.match(l)
        if m:
            if cur_q:
                questions.append(cur_q)
            cur_q = m.group(2).strip()
        elif cur_q is not None:
            cur_q += " " + l.strip()
    if cur_q:
        questions.append(cur_q)
    questions = [despace(strip_super(re.sub(r"\s+", " ", q).strip())) for q in questions]
    questions = [q for q in questions if len(q) > 20]

    meta = toc[num]
    cases.append({
        "number": num,
        "slug": f"{num:02d}",
        "title": meta["title"],
        "playoffCandidate": meta["playoff"],
        "narrative": paras,
        "discussionQuestions": questions,
        "sources": sources,
        # ---- student / class content layer: deliberately empty ----
        "expert": None,
        "status": "unassigned",            # unassigned | assigned | submitted | discussed
        "sections": {
            "coreEthicalDilemmas": [],
            "stakeholders": [],
            "frameworks": {"consequentialist": [], "deontological": [], "virtue": [], "justice": []},
            "practicePresentation": [],
            "looseEnds": []
        }
    })

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "cases.json").write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n")

print(f"pages used: {seen_pages}")
print(f"{'#':>3}  {'title':34s} {'★':1s} {'¶':>3} {'DQ':>3} {'src':>4} {'words':>6}")
for c in cases:
    print(f"{c['number']:>3}  {c['title']:34s} {'★' if c['playoffCandidate'] else ' ':1s} "
          f"{len(c['narrative']):>3} {len(c['discussionQuestions']):>3} {len(c['sources']):>4} "
          f"{sum(len(p.split()) for p in c['narrative']):>6}")
