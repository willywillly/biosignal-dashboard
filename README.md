# Biosignal Dashboard

A circadian rhythm intelligence dashboard built on Apple Health export data. Parses your personal health data locally, finds patterns in sleep timing and workout consistency, and presents insights in plain language.

**Live demo →** [biosignal-dashboard.vercel.app](https://biosignal-dashboard.vercel.app)

---

## What it does

- Reads your Apple Health export (the zip file from the Health app)
- Detects your natural sleep window and consistency over time
- Correlates workout timing with next-morning resting heart rate
- Computes a **Rhythm Score** based on your sleep timing variance
- Shows a **dual circadian clock** — your actual pattern vs. your data-derived blueprint
- Gives a plain-language tonight's target: when to wind down, when to sleep

All processing is local. No data leaves your device.

---

## Stack

- Vanilla JS + HTML/CSS (no framework)
- Chart.js for time-series charts
- Python parser for pre-processing Apple Health XML → JSON
- Vercel for static hosting

---

## Run locally

**1. Export your Apple Health data**
Open the Health app → profile icon → Export All Health Data → save the zip

**2. Parse the export**
```bash
# unzip your export and point parse_health.py at it
python3 parse_health.py
```
This writes pre-computed JSON files to `data/`

**3. Serve the dashboard**
```bash
python3 -m http.server 3000
# open http://localhost:3000
```

---

## Demo mode

The repo includes pre-computed `data/nights.json` so the dashboard works immediately without uploading anything. Drop your own Apple Health export zip on the import screen to see your personal data.

---

## Data files

| File | Description | Used in demo |
|------|-------------|-------------|
| `data/nights.json` | Per-night stats + metadata (main file) | ✓ |
| `data/sleep.json` | Raw WHOOP sleep segments | ✓ |
| `data/resting_hr.json` | Daily resting HR readings | ✓ |
| `data/workouts.json` | Workout sessions with timing | ✓ |
| `data/heart_rate.json` | All HR readings (large) | not committed |
| `data/active_energy.json` | Active energy burn (large) | not committed |

---

## Roadmap

- [ ] Browser-side XML parsing (no Python needed)
- [ ] Claude API narration — personalized insight copy
- [ ] Multi-device support (Garmin, Oura, Fitbit via HealthKit)
- [ ] Return-visit experience with weekly deltas
- [ ] Native iOS app with HealthKit live access

---

Built by Willy Tran
