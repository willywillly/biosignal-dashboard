import xml.etree.ElementTree as ET
import json
import os
from collections import defaultdict

SOURCE = os.path.expanduser("~/Downloads/apple_health_export/export.xml")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

TARGETS = {
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv.json",
    "HKQuantityTypeIdentifierRestingHeartRate":         "resting_hr.json",
    "HKCategoryTypeIdentifierSleepAnalysis":            "sleep.json",
    "HKQuantityTypeIdentifierHeartRate":                "heart_rate.json",
    "HKQuantityTypeIdentifierActiveEnergyBurned":       "active_energy.json",
}

WORKOUT_TAG = "Workout"

buckets = defaultdict(list)
workout_bucket = []
counts = defaultdict(int)
total = 0

print("Parsing... (progress every 100k records)")

for event, elem in ET.iterparse(SOURCE, events=("end",)):
    tag = elem.tag

    if tag == "Record":
        rtype = elem.get("type", "")
        total += 1
        if total % 100_000 == 0:
            print(f"  {total:,} records processed...")

        if rtype in TARGETS:
            rec = {
                "startDate":  elem.get("startDate"),
                "endDate":    elem.get("endDate"),
                "value":      elem.get("value"),
                "unit":       elem.get("unit"),
                "sourceName": elem.get("sourceName"),
            }
            buckets[rtype].append(rec)
            counts[rtype] += 1

        elem.clear()

    elif tag == WORKOUT_TAG:
        total += 1
        rec = {
            "startDate":        elem.get("startDate"),
            "endDate":          elem.get("endDate"),
            "workoutActivityType": elem.get("workoutActivityType"),
            "duration":         elem.get("duration"),
            "durationUnit":     elem.get("durationUnit"),
            "totalEnergyBurned":     elem.get("totalEnergyBurned"),
            "totalEnergyBurnedUnit": elem.get("totalEnergyBurnedUnit"),
            "totalDistance":         elem.get("totalDistance"),
            "totalDistanceUnit":     elem.get("totalDistanceUnit"),
            "sourceName":       elem.get("sourceName"),
        }
        workout_bucket.append(rec)
        counts["HKWorkoutActivityType"] += 1
        elem.clear()

print(f"\nDone. Total elements processed: {total:,}\n")

# Write JSON files
os.makedirs(DATA_DIR, exist_ok=True)

for rtype, filename in TARGETS.items():
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(buckets[rtype], f)
    print(f"  Wrote {len(buckets[rtype]):>7,} records → data/{filename}")

workout_path = os.path.join(DATA_DIR, "workouts.json")
with open(workout_path, "w") as f:
    json.dump(workout_bucket, f)
print(f"  Wrote {len(workout_bucket):>7,} records → data/workouts.json")

print("\n--- Summary ---")
label_map = {
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "HRV (SDNN)",
    "HKQuantityTypeIdentifierRestingHeartRate":         "Resting Heart Rate",
    "HKCategoryTypeIdentifierSleepAnalysis":            "Sleep Analysis",
    "HKQuantityTypeIdentifierHeartRate":                "Heart Rate",
    "HKQuantityTypeIdentifierActiveEnergyBurned":       "Active Energy Burned",
    "HKWorkoutActivityType":                            "Workouts",
}
for key, label in label_map.items():
    print(f"  {label:<30} {counts[key]:>8,} records")

# ── Compute per-night stats and write data/nights.json ─────────────────────
print("\nComputing nightly sleep sessions...")
from datetime import datetime
import statistics

sleep_records = buckets["HKCategoryTypeIdentifierSleepAnalysis"]
rhr_records   = buckets["HKQuantityTypeIdentifierRestingHeartRate"]

# Build RHR lookup: min RHR per local date
rhr_by_date = {}
for r in rhr_records:
    d = r["startDate"][:10]
    v = float(r["value"])
    if d not in rhr_by_date or v < rhr_by_date[d]:
        rhr_by_date[d] = v

# Group WHOOP sleep segments into nightly sessions (gap > 90 min = new session)
whoop = sorted([r for r in sleep_records if r["sourceName"] == "WHOOP"],
               key=lambda r: r["startDate"])

raw_sessions = []
if whoop:
    session = [whoop[0]]
    for r in whoop[1:]:
        gap = (datetime.fromisoformat(r["startDate"]) -
               datetime.fromisoformat(session[-1]["endDate"])).total_seconds() / 60
        if gap < 90:
            session.append(r)
        else:
            raw_sessions.append(session)
            session = [r]
    raw_sessions.append(session)

def build_night(s):
    onset_dt = datetime.fromisoformat(s[0]["startDate"])
    wake_dt  = datetime.fromisoformat(s[-1]["endDate"])
    sleep_hrs = sum(
        (datetime.fromisoformat(r["endDate"]) - datetime.fromisoformat(r["startDate"])).total_seconds() / 3600
        for r in s if r["value"] == "HKCategoryValueSleepAnalysisAsleepUnspecified"
    )
    onset_h = onset_dt.hour + onset_dt.minute / 60
    wake_h  = wake_dt.hour  + wake_dt.minute  / 60
    # normalize: pre-midnight onsets (< 12) → 24+ so all nights sort contiguously
    onset_norm = onset_h + 24 if onset_h < 12 else onset_h
    return {
        "onsetStr":   s[0]["startDate"],
        "wakeStr":    s[-1]["endDate"],
        "wakeDate":   s[-1]["endDate"][:10],
        "onsetHour":  round(onset_h, 4),
        "wakeHour":   round(wake_h, 4),
        "onsetNorm":  round(onset_norm, 4),
        "sleepHrs":   round(sleep_hrs, 3),
        "dayOfWeek":  wake_dt.weekday(),   # 0=Mon … 6=Sun
    }

nights = [build_night(s) for s in raw_sessions]
nights = [n for n in nights if n["sleepHrs"] > 1]

# Compute median onset and per-night deviation
onset_norms  = [n["onsetNorm"] for n in nights]
median_onset = statistics.median(onset_norms)
wake_hours   = [n["wakeHour"] for n in nights]
onset_sd_min = statistics.stdev(onset_norms) * 60
wake_sd_min  = statistics.stdev(wake_hours)  * 60

for n in nights:
    n["deviationMin"] = round(abs(n["onsetNorm"] - median_onset) * 60, 2)
    n["rhr"]          = rhr_by_date.get(n["wakeDate"])

# Correlation groups
best  = [n for n in nights if n["deviationMin"] <= 30 and 7 <= n["sleepHrs"] <= 9 and n["rhr"]]
rough = [n for n in nights if (n["deviationMin"] > 60 or n["sleepHrs"] < 6) and n["rhr"]]
best_rhr  = round(sum(n["rhr"] for n in best)  / len(best),  2) if best  else None
rough_rhr = round(sum(n["rhr"] for n in rough) / len(rough), 2) if rough else None

# Social jetlag: weekend (wake Sat/Sun) vs weekday onset median
wd = [n["onsetNorm"] for n in nights if n["dayOfWeek"] < 5]
we = [n["onsetNorm"] for n in nights if n["dayOfWeek"] >= 5]
jetlag_min = round(abs(statistics.median(we) - statistics.median(wd)) * 60, 1) if wd and we else None

# ── Workout timing analysis ────────────────────────────────────────────────
from datetime import timedelta

sleep_by_date = {n["wakeDate"]: n["sleepHrs"] for n in nights}

workout_tagged = []
for w in workout_bucket:
    try:
        start_dt = datetime.fromisoformat(w["startDate"])
    except Exception:
        continue
    hour      = start_dt.hour + start_dt.minute / 60
    next_date = (start_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    rhr_next  = rhr_by_date.get(next_date)
    sleep_nxt = sleep_by_date.get(next_date)
    if rhr_next:
        workout_tagged.append({
            "hour":      round(hour, 3),
            "type":      w["workoutActivityType"].replace("HKWorkoutActivityType", ""),
            "dur":       round(float(w["duration"]), 1) if w["duration"] else None,
            "rhrNext":   rhr_next,
            "sleepHrs":  sleep_nxt,
            "date":      start_dt.strftime("%Y-%m-%d"),
        })

# Time buckets: controlled for ≥7h sleep to reduce intensity confound
WBUCKETS = [
    ("Morning",   8,  11),
    ("Midday",   11,  14),
    ("Afternoon", 14, 17),
    ("Evening",  17,  20),
]

workout_windows = []
for label, s, e in WBUCKETS:
    raw   = [t for t in workout_tagged if s <= t["hour"] < e]
    ctrl  = [t for t in raw if t["sleepHrs"] and t["sleepHrs"] >= 7]
    if len(raw) < 3:
        continue
    entry = {
        "label":      label,
        "startHour":  s,
        "endHour":    e,
        "n":          len(raw),
        "nControlled": len(ctrl),
        "avgRhr":     round(statistics.mean(t["rhrNext"] for t in raw), 2),
        "avgRhrControlled": round(statistics.mean(t["rhrNext"] for t in ctrl), 2) if ctrl else None,
    }
    workout_windows.append(entry)

# Tag best / worst based on sleep-controlled RHR (fall back to raw if too few)
def window_score(w):
    return w["avgRhrControlled"] if w["avgRhrControlled"] else w["avgRhr"]

workout_windows.sort(key=window_score)
for i, w in enumerate(workout_windows):
    w["rank"] = i  # 0 = best (lowest RHR)

print("\n  Workout timing vs next-day RHR (sleep-controlled):")
for w in workout_windows:
    tag = " ← best" if w["rank"] == 0 else (" ← avoid" if w["rank"] == len(workout_windows)-1 else "")
    print(f"    {w['label']:10} {w['startHour']:02d}–{w['endHour']:02d}h  "
          f"n={w['n']:>3}  RHR={w['avgRhr']:.2f}  ctrl={w['avgRhrControlled']}{tag}")

meta = {
    "totalNights":    len(nights),
    "medianOnset":    round(median_onset, 4),
    "avgSleepHrs":    round(sum(n["sleepHrs"] for n in nights) / len(nights), 2),
    "onsetSdMin":     round(onset_sd_min, 1),
    "wakeSdMin":      round(wake_sd_min, 1),
    "avgWakeHour":    round(statistics.median(wake_hours), 4),
    "jetlagMin":      jetlag_min,
    "bestRhr":        best_rhr,
    "roughRhr":       rough_rhr,
    "bestN":          len(best),
    "roughN":         len(rough),
    "deltaRhr":       round(rough_rhr - best_rhr, 2) if best_rhr and rough_rhr else None,
    "workoutWindows": workout_windows,
    "workoutTagged":  workout_tagged,
}

output = {"meta": meta, "nights": nights}
nights_path = os.path.join(DATA_DIR, "nights.json")
with open(nights_path, "w") as f:
    json.dump(output, f)
print(f"  Wrote {len(nights):>7,} nights    → data/nights.json")
print(f"\n  Median bedtime:  {int(median_onset%24):02d}:{int((median_onset%1)*60):02d}")
print(f"  Avg sleep:       {meta['avgSleepHrs']:.1f} hrs")
print(f"  Bedtime SD:      {meta['onsetSdMin']:.0f} min")
print(f"  Social jetlag:   {jetlag_min} min")
if best_rhr and rough_rhr:
    print(f"  Best nights RHR: {best_rhr} bpm (n={len(best)})")
    print(f"  Rough nights RHR:{rough_rhr} bpm (n={len(rough)})")
    print(f"  Delta:           +{meta['deltaRhr']} bpm")
