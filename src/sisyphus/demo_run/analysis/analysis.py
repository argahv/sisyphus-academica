#!/usr/bin/env python3
"""Demo analysis: Type I error of Student's and Welch's t-tests when the
smaller group has the larger variance. Writes statistics.json next to this file.

Run: python3 analysis.py   (stdlib only; uses the p-value code in sisyphus.tools)
"""

import json
import math
import random
import statistics
from pathlib import Path

from sisyphus.tools.stats_audit import p_value

SEED = 2026
REPS = 4000
N_SMALL, SD_SMALL = 10, 3.0
N_LARGE, SD_LARGE = 40, 1.0
ALPHA = 0.05


def student(a, b):
    na, nb = len(a), len(b)
    sp2 = ((na - 1) * statistics.variance(a) + (nb - 1) * statistics.variance(b)) / (na + nb - 2)
    t = (statistics.mean(a) - statistics.mean(b)) / math.sqrt(sp2 * (1 / na + 1 / nb))
    return p_value("t", t, na + nb - 2)


def welch(a, b):
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    t = (statistics.mean(a) - statistics.mean(b)) / math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1))
    return p_value("t", t, df)


def wilson(k, n, z=1.959964):
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def main():
    rng = random.Random(SEED)
    s_rej = w_rej = only_s = only_w = 0
    for _ in range(REPS):
        a = [rng.gauss(0, SD_SMALL) for _ in range(N_SMALL)]
        b = [rng.gauss(0, SD_LARGE) for _ in range(N_LARGE)]
        s, w = student(a, b) < ALPHA, welch(a, b) < ALPHA
        s_rej += s
        w_rej += w
        only_s += s and not w
        only_w += w and not s
    chi2 = (only_s - only_w) ** 2 / (only_s + only_w)
    z = (w_rej / REPS - ALPHA) / math.sqrt(ALPHA * (1 - ALPHA) / REPS)
    out = {
        "data_source": f"Monte Carlo simulation in analysis.py (seed {SEED}, {REPS} replications)",
        "design": {
            "n_small": N_SMALL,
            "sd_small": SD_SMALL,
            "n_large": N_LARGE,
            "sd_large": SD_LARGE,
            "alpha": ALPHA,
            "true_difference": 0,
        },
        "rates": {
            "student": {
                "rejections": s_rej,
                "rate": round(s_rej / REPS, 4),
                "wilson_95": [round(x, 4) for x in wilson(s_rej, REPS)],
            },
            "welch": {
                "rejections": w_rej,
                "rate": round(w_rej / REPS, 4),
                "wilson_95": [round(x, 4) for x in wilson(w_rej, REPS)],
            },
        },
        "tests": [
            {
                "name": "McNemar test, Student vs Welch rejections",
                "statistic": round(chi2, 2),
                "df": [1],
                "p_value": p_value("chi2", chi2, 1),
                "discordant": [only_s, only_w],
            },
            {
                "name": "z test, Welch rejection rate vs nominal 0.05",
                "statistic": round(z, 2),
                "p_value": p_value("z", z),
            },
        ],
    }
    Path(__file__).with_name("statistics.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
