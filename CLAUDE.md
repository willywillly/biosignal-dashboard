# Cadence — Claude Code Memory

## PROJECT
A circadian rhythm biosignal dashboard that helps users understand and optimize their sleep/wake patterns using Apple Health data.

---

## FRONTEND
- **URL:** https://cadencedashboard.vercel.app
- **Stack:** Vanilla JS + Chart.js, static HTML
- **Repo:** `biosignal-dashboard` (public GitHub — willywillly)
- **Key file:** `index.html` (~2500 lines, all-in-one)
- **Auth:** `X-Cadence-Key: cad-f7x2-9kqm-3wpl` header on API calls

## BACKEND
- **URL:** https://cadence-backend-production-f1eb.up.railway.app
- **Stack:** FastAPI Python
- **Repo:** `cadence-backend` (private GitHub)
- **Key file:** `main.py`

---

## ARCHITECTURE
```
User uploads Apple Health XML
  → Parsed entirely in-browser (JS string scanner, fast)
  → Computed stats (meta + nights array) sent to Railway
  → FastAPI calls Claude API server-side
  → Narration / Cadence AI text returned
  → Rendered in dashboard
```
Raw health data never leaves the browser. Only derived stats hit the network.

---

## DESIGN TOKENS
```css
--bg:      #F7F5F1   /* warm off-white, body background */
--surface: #FFFFFF   /* card surfaces */
--lime:    #8CC63F   /* primary CTA, active nav, action bar */
--purple:  #7252D8   /* Cadence AI accent, brand */
--text:    #1A1917   /* primary text */
--muted:   #9B9791   /* secondary text */
--border:  #E8E4DE   /* dividers, card borders */
--green:   #3DBF7A   /* positive metrics */
--amber:   #F5A623   /* fair metrics */
--red:     #E85C5C   /* low/alert metrics */
```
Font: **Inter** (Google Fonts)
Primary viewport: **390px** (iPhone 15)
Paper grain texture: SVG feTurbulence fractalNoise on `body::before` at `opacity: 0.03`

---

## SCREEN FLOW
```
boot()
  ├── Branch A: onboarded + localStorage cache fresh (<24h)  → screen-dash (instant)
  ├── Branch B: onboarded + cache missing/expired            → screen-landing (instant, no animation)
  └── Branch C: new user                                     → screen-landing (full typewriter animation)

screen-landing → [upload Apple Health XML] → screen-analysis → screen-dash
```
**screen-import is removed from the nav flow.** Do not reintroduce it.

## localStorage KEYS
| Key | Purpose |
|-----|---------|
| `cadence_onboarded` | Set after first successful analysis |
| `cadence_name` | User's first name |
| `cadence_profile` | Onboarding survey answers |
| `cadence_checkin_date` | Last daily check-in date (YYYY-MM-DD) |
| `cadence_context_log` | Rolling Cadence AI context history |
| `cadence_dash_cache` | `{ meta, nights, workoutRaw, cachedAt }` — 24h TTL |

## BOTTOM NAV
Fixed 64px, 4 items: JOURNAL / PATTERNS / TRAINING / HISTORY
- Hidden by default (`display:none`)
- Shown only on dashboard via `nav.classList.add('visible')` in `showDashboard()`
- Removed via `nav.classList.remove('visible')` in `clearAllUserData()`

---

## KEY DATA STRUCTURES

### `window._dashData`
```js
{ meta, nights, rhrRaw, workoutRaw }
```

### `nights[]` (per night object)
Each night has a `rhr` property = mean HR in 90-min window after wake time (true resting HR, 40–80 bpm range). Used for the RHR chart instead of raw readings.

### Score grading (`rhythmMeta()`)
| Score | Label | Color |
|-------|-------|-------|
| ≥75 | EXCEPTIONAL | green |
| ≥60 | GOOD | green |
| ≥50 | FAIR | amber |
| ≥35 | DEVELOPING | amber |
| <35 | LOW | red |

---

## CURRENT STATE (last updated: 2026-03-31)

### Working
- Full mobile-first UI (v2 redesign): 96px breathing score, lime action bar, bottom nav, accordion
- Header: hamburger left + CADENCE centered + profile button right
- Cadence AI card: white surface, purple dot, 52px tonight time, hairline divider
- Paper grain texture on body
- Apple Health XML parser (fast string-scanner, InBed fallback, 4h gap grouping)
- Per-night RHR from morning HR window (correct 40–80 bpm range)
- Session cache: localStorage with 24h TTL (survives iOS Safari page reloads)
- Three-branch boot(): instant restore / instant landing / full animation
- Bottom nav only visible on dashboard screen
- Analysis screen: score revealed last (after facts), no flash bug
- `clearAllUserData()` clears all 6 localStorage keys including cache

### Known gaps / not yet built
- Cadence AI "Load failed" retry shows soft error (works), but no offline fallback content
- Wake time widget shows "Not enough data" if <3 nights — acceptable for now
- Settings panel: import new data clears cache and triggers file picker (working)

---

## NEXT TASK
TBD — populate at start of next session.

---

## RULES FOR ALL SESSIONS
- **Never push directly to main** — always commit with a message, push to main only (no branches needed for this solo project, but never force-push)
- **Never change data parsing logic** (`_iterElems`, `_getAttr`, gap grouping, InBed fallback) without explicitly saying so
- **Never change design tokens** without user approval
- **Privacy first** — raw health data (XML, rhrRaw array) never leaves the browser
- **Mobile first** — 390px primary target, test tap targets ≥44px
- **No screen-import in flow** — this screen is deprecated, do not re-add to navigation
- **Cache key is `cadence_dash_cache`** — use `KEY_CACHE` constant, never hardcode the string in new code
- **rhrRaw is NOT cached** — too large (50k+ entries); use `nights[].rhr` for charts instead

---

## SESSION LOG

### 2026-03-31
- Completed full mobile-first UI revamp (P0–P6): skeleton screens, RHR fix, hero redesign, bottom nav, accordion, paper grain
- Installed frontend-design skill at `.claude/skills/frontend-design/SKILL.md`
- V2 visual redesign from screenshot reference: 96px score, breathing animation, new header, Cadence AI card, lime action bar, bottom nav, accordion headers
- Fixed screen flow bugs: bottom nav bleeding, analysis score flash, three-branch boot()
- Fixed iOS Safari session persistence: sessionStorage → localStorage with 24h TTL
- Removed fast animation mode and screen-import from returning-user flow
- Branch B (returning user, no cache): instant landing screen, no animation
