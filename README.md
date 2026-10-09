# Hackley Ethics Bowl Team — 2026–2027

Static site for the Hackley Ethics Bowl team. No build step, no backend.
GitHub → Netlify.

```
public/              ← everything Netlify serves
  index.html         ← the whole site (one file: markup, styles, behaviour)
  data/cases.json    ← the 15 cases + the student/class work layer
  data/logistics.json← calendar, contacts, match rules, scoring, frameworks, team
  docs/*.pdf         ← NHSEB documents linked from Resources
  robots.txt         ← asks search engines not to index
tools/
  parse_caseset.py   ← regenerates cases.json from the NHSEB case set PDF
  serve.py           ← local preview server
netlify.toml         ← publish directory + headers
```

## Deploying

Netlify watches the repo. Push to `main` and it redeploys.

```bash
git add -A && git commit -m "Update case 3 after class discussion" && git push
```

First-time Netlify setup: **Add new site → Import an existing project → GitHub**, pick this
repo. The settings come from `netlify.toml` — publish directory `public`, no build command.

## Previewing locally

`index.html` fetches its data, so opening it straight from Finder will not work — browsers
block those requests. Run:

```bash
python3 tools/serve.py
```

Then open <http://127.0.0.1:8777>. If you ever see "Could not load the case data", that is
what happened.

## Updating content

All content is in the two JSON files. Nothing else needs touching.

**Adding student work to a case** — edit `public/data/cases.json`, find the case, fill in the
section. Every entry takes a `who` and `when` so the page can attribute it:

```json
"coreEthicalDilemmas": [
  { "text": "…", "who": "Maya", "when": "Oct 22" }
],
"stakeholders": [
  { "who": "Residents who want to stay", "wants": "…", "power": "…", "vulnerability": "…" }
],
"frameworks": {
  "consequentialist": [ { "text": "…", "who": "Class discussion", "when": "Nov 4" } ],
  "deontological": [], "virtue": [], "justice": []
}
```

Set `"expert": "Maya"` on the case and the page switches from "No student assigned yet" to
her name, and empty sections read "Awaiting Maya's submission".

**The team roster** — `logistics.json` → `team.members`:
`[{ "name": "Maya", "cases": ["01", "07"] }]`. First names only.

**Presentation length** — `logistics.json` → `matchFormat`. Regionals run 5 minutes but the
organizer may extend to 6; Divisionals and Nationals are always 6. Once Connor confirms, set
`presentationMinutes` and flip `presentationMinutesConfirmed` to `true` to drop the warning.

## Ground rules

- **The teacher's case analysis documents never go in this repo.** The site fills from student
  submissions and class discussion. Those docs live outside the repo on purpose.
- **No case-specific examples on the Frameworks page.** It teaches the lenses; the case pages
  apply them.
- **Site copy stays plain.** If it is unclear what a line should say, leave it blank.
- Source material (emails, registration records, the analysis docs) is deliberately *not* in
  this repository. Keep it that way.

## Attribution and licensing

Cases are © 2026 UNC Parr Center for Ethics, licensed CC BY-NC-ND 4.0, reproduced here for
Hackley School classroom use with attribution, and `robots.txt` asks search engines not to
index the site. Netlify sites are public to anyone with the URL — if you want it actually
closed, Netlify's password protection (paid plans) or Netlify Identity would do it.

## Regenerating cases.json

Only needed if NHSEB revises the case set.

```bash
python3 tools/parse_caseset.py
```

Edit the `SRC` path at the top first — it points at the original PDF outside this repo. The
parser handles the ligature, footnote, superscript, and page-number quirks in the source PDF;
check its summary table afterwards (15 cases, 73 paragraphs, 41 questions, 20 sources).
