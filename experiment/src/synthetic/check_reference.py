"""Provenance check for reference JSON files.
Flags signs that a file was written by the old generator (audit item C6),
lacks a real citation, or carries placeholder text instead of a source."""
import glob
import json
import os
import re

import numpy as np
import pandas as pd

REF_DIR = "experiment/data/reference"
COHORT = "experiment/data/raw/cohort.parquet"
SPEC_JSON = os.path.join(REF_DIR, "cdss_spec.json")
SOURCE_KEYS = {"source", "citation", "url", "reference", "doi", "table", "survey", "_source"}

# Any of these words/symbols means the citation was never filled in
PLACEHOLDER = re.compile(
    r"[<>\[\]{}]|\.\.\.|"
    r"\b(todo|tbd|tba|xxx|placeholder|paste|here|insert|fill|replace|"
    r"report title|link to|real citation|real link|example|lorem)\b",
    re.I,
)
MIN_CITATION_LEN = 15          # a real citation names a title/author/year
URL_PATTERN = re.compile(r"^https?://[^\s]+\.[^\s]+$")


def walk_numbers(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_numbers(v)


def longest_list(obj):
    if isinstance(obj, list):
        return max([len(obj)] + [longest_list(v) for v in obj])
    if isinstance(obj, dict):
        return max([0] + [longest_list(v) for v in obj.values()])
    return 0


def decimals(x):
    s = repr(float(x))
    return len(s.split(".")[1]) if "." in s else 0


def source_values(obj):
    """Yield (key, value) for every source-like key, at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in SOURCE_KEYS:
                yield k, v
            yield from source_values(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from source_values(v)


def is_real_citation(key, value):
    if not isinstance(value, str) or not value.strip():
        return False
    v = value.strip()
    if PLACEHOLDER.search(v):
        return False
    if key.lower() == "url":
        return bool(URL_PATTERN.match(v))
    return len(v) >= MIN_CITATION_LEN


cohort_q = None
if os.path.exists(COHORT):
    bmi = pd.read_parquet(COHORT, columns=["visit_number", "bmi"])
    bmi = bmi[bmi["visit_number"] == 1]["bmi"].dropna()
    cohort_q = np.percentile(bmi, [25, 50, 75])

spec_bounds = {}
if os.path.exists(SPEC_JSON):
    with open(SPEC_JSON, encoding="utf-8") as f:
        spec_bounds = json.load(f).get("feature_bounds", {})

verdicts = {}
for path in sorted(glob.glob(os.path.join(REF_DIR, "*.json"))):
    name = os.path.basename(path)
    if name == "cdss_spec.json":
        continue
    flags, info = [], []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        verdicts[name] = ("❌ UNREADABLE", [f"invalid JSON: {e}"], [])
        continue

    nums = list(walk_numbers(data))
    info.append(f"{os.path.getsize(path)} bytes, {len(nums)} numbers, top-level keys: "
                f"{list(data.keys()) if isinstance(data, dict) else type(data).__name__}")

    # Signal 1: long raw list of values (C6 wrote df['bmi'].tolist()[:100])
    ll = longest_list(data)
    if ll >= 50:
        flags.append(f"contains a list of {ll} values: looks like raw generated samples")

    # Signal 2: machine precision
    long_dec = [x for x in nums if isinstance(x, float) and decimals(x) >= 6]
    if nums and len(long_dec) / len(nums) > 0.5:
        flags.append(f"{len(long_dec)}/{len(nums)} numbers have 6+ decimals: published tables are rounded")

    # Signal 3: citation present, specific, and not a placeholder
    sources = list(source_values(data))
    real = [(k, v) for k, v in sources if is_real_citation(k, v)]
    fake = [(k, v) for k, v in sources if not is_real_citation(k, v)]
    if fake:
        flags.append(f"placeholder, empty or malformed citation: {fake}")
    if not real:
        flags.append("no real source/citation: cannot be traced to a publication")
    else:
        info.append(f"cited source: {real[0][1][:90]}")

    # Signal 4 (BMI): quartiles copied from the synthetic cohort
    if name.startswith("bmi_reference") and isinstance(data, dict):
        if all(k in data for k in ("p25", "p50", "p75")) and cohort_q is not None:
            ref_q = np.array([data["p25"], data["p50"], data["p75"]], dtype=float)
            rel = np.abs(ref_q - cohort_q) / ref_q
            info.append(f"file quartiles {ref_q.round(2).tolist()} vs cohort {cohort_q.round(2).tolist()}")
            if (rel < 0.005).all():
                flags.append("quartiles match the synthetic cohort within 0.5%: likely copied from the generator")
        elif cohort_q is not None:
            flags.append("missing p25/p50/p75 keys")

        # Signal 5 (BMI): min/max equal to CDSS clip bounds, not survey extremes
        b = spec_bounds.get("bmi")
        if b and data.get("min") == b["min"] and data.get("max") == b["max"]:
            note = str(data.get("note", "")).lower()
            if "cdss" not in note:
                flags.append(f"min/max ({data['min']}, {data['max']}) equal the CDSS clip bounds: "
                             "not survey values; add a note or remove them")
            else:
                info.append("min/max documented as CDSS bounds (note present)")

    if any("list of" in f or "match the synthetic" in f for f in flags):
        verdict = "🔴 LIKELY GENERATED"
    elif flags:
        verdict = "🟠 UNVERIFIED"
    else:
        verdict = "🟢 CITED (confirm the numbers against the cited source once)"
    verdicts[name] = (verdict, flags, info)

print("=" * 78)
print("REFERENCE JSON PROVENANCE CHECK")
print("=" * 78)
for name, (verdict, flags, info) in verdicts.items():
    used = " (used by Gate 2)" if name.startswith("bmi_reference") else " (not used by code)"
    print(f"\n{name}{used}\n  {verdict}")
    for i in info:
        print(f"  · {i}")
    for fl in flags:
        print(f"  ⚠ {fl}")

print("\n" + "=" * 78)
bmi_verdict = next((v for n, (v, _, _) in verdicts.items() if n.startswith("bmi_reference")), "missing")
if "GENERATED" in bmi_verdict:
    print("🔴 ACTION: Gate 2 compares the cohort against generated data. Replace the file or drop the NHANES claim.")
elif "UNVERIFIED" in bmi_verdict:
    print("🟠 ACTION: Find the published table, confirm the numbers, then add the REAL citation.")
elif "CITED" in bmi_verdict:
    print("🟢 BMI file carries a real citation. Confirm the numbers match it once.")
else:
    print("❌ bmi_reference_quartiles.json not found.")
print("=" * 78)
