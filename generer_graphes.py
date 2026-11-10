#!/usr/bin/env python3
"""Generate graphs for PID steering and speed trials (conduite-pid).

Run from the directory containing CSVs:
    python3 generer_graphes.py

Uses the CSV column headers to identify the controller:
  - steering: temps_s, mesure_m, consigne_m, volant, p, i, d
  - speed:    temps_s, mesure_kmh, consigne_kmh, pedale, p, i, d

Outputs individual PDFs and separate combined reports for steering and speed
under ./graphiques. For each file, overlays the preceding comparable trial.
For PALIERS speed trials with an accompanying _direction.csv, creates an
additional PDF illustrating steering position and speed stages together.
"""

import csv
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path.cwd()
OUTPUT = ROOT / "graphiques"
OUTPUT.mkdir(parents=True, exist_ok=True)

KINDS = {
    "direction": {
        "required": {"temps_s", "mesure_m", "volant"},
        "measurement": "mesure_m", "setpoint": "consigne_m", "output": "volant",
        "measurement_label": "Lateral position (m)",
        "output_label": "Steering command / PID terms",
        "title": "PID steering", "setpoint_label": "Target position",
        "actual_label": "Car position", "output_name": "Steering",
    },
    "vitesse": {
        "required": {"temps_s", "mesure_kmh", "pedale"},
        "measurement": "mesure_kmh", "setpoint": "consigne_kmh", "output": "pedale",
        "measurement_label": "Speed (km/h)",
        "output_label": "Pedal command / PID terms",
        "title": "PID speed", "setpoint_label": "Target speed",
        "actual_label": "Actual speed", "output_name": "Pedal",
    },
}


def load_csv(path):
    """Identify type by columns, not filename; skip unsupported CSVs safely."""
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            headers = set(reader.fieldnames or [])
            kind = next((k for k, cfg in KINDS.items()
                         if cfg["required"].issubset(headers)), None)
            if kind is None:
                print(f"Skipping {path.name}: unrecognized CSV columns")
                return None
            rows = list(reader)
        if not rows:
            print(f"Skipping {path.name}: no measurements")
            return None
        keys = ("temps_s", KINDS[kind]["measurement"], KINDS[kind]["output"],
                KINDS[kind]["setpoint"], "p", "i", "d")
        data = {}
        for key in keys:
            if key in headers:
                data[key] = [float(row[key]) for row in rows]
        return kind, data
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Skipping {path.name}: {exc}")
        return None


def conditions(path, kind):
    """Match previous runs only when scenario and starting conditions agree."""
    name = re.sub(r"^essai\d+_", "", path.stem, flags=re.I)
    name = re.sub(r"_kp[^_]+_ki[^_]+_kd[^_]+", "", name, flags=re.I)
    name = re.sub(r"_(aucun|conditionnel|bande)(?=_|$)", "", name, flags=re.I)
    name = re.sub(r"_direction$", "", name, flags=re.I)
    return kind, name.upper()


def gains(path):
    match = re.search(r"_kp([^_]+)_ki([^_]+)_kd([^_]+)", path.stem, re.I)
    return (f"Kp={match[1]}, Ki={match[2]}, Kd={match[3]}"
            if match else path.stem)


def draw(path, data, kind, previous=None):
    cfg = KINDS[kind]
    t = data["temps_s"]
    measurement = cfg["measurement"]
    setpoint = cfg["setpoint"]
    output_key = cfg["output"]

    fig, (ax, control) = plt.subplots(
        2, 1, figsize=(10.5, 7.6), sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1]}
    )
    fig.suptitle(f'{cfg["title"]} — {path.stem}', fontsize=12, weight="bold")

    if previous is not None:
        prev_path, prev_data = previous
        ax.plot(prev_data["temps_s"], prev_data[measurement], lw=1.6,
                color="#9ca3af", linestyle="--",
                label=f"Previous: {prev_path.stem.split('_')[0]} ({gains(prev_path)})")

    ax.plot(t, data[measurement], lw=2, color="#1d4ed8",
            label=f'{cfg["actual_label"]}: {gains(path)}')
    if setpoint in data:
        ax.plot(t, data[setpoint], lw=1.8, color="#059669", linestyle=":",
                label=cfg["setpoint_label"])
    elif kind == "direction":
        ax.axhline(0, color="#059669", ls=":", label="Lane center")
    ax.set_ylabel(cfg["measurement_label"])
    ax.grid(alpha=.25)
    ax.legend(loc="best", fontsize=8)

    for key, label, color in [
        (output_key, cfg["output_name"], "#334155"),
        ("p", "P", "#d97706"),
        ("i", "I", "#059669"),
        ("d", "D", "#a855f7"),
    ]:
        if key in data:
            control.plot(t, data[key], label=label, color=color, lw=1.3)
    control.axhline(0, color="#777", lw=.7)
    control.axhline(1, color="#777", lw=.6, ls=":")
    control.axhline(-1, color="#777", lw=.6, ls=":")
    control.set_xlabel("Time (s)")
    control.set_ylabel(cfg["output_label"])
    control.grid(alpha=.25)
    control.legend(loc="best", fontsize=8, ncol=4)

    final = data[measurement][-1]
    if kind == "direction":
        detail = (f"Final position: {final:.3f} m  |  "
                  f"Max |position|: {max(map(abs, data[measurement])):.3f} m")
    else:
        detail = f"Final speed: {final:.2f} km/h"
        if setpoint in data:
            detail += f"  |  Final error: {data[setpoint][-1] - final:+.2f} km/h"
    fig.text(.09, .025,
             f'Duration: {t[-1]:.2f} s  |  {detail}.  End of CSV is not necessarily settling time.',
             fontsize=8, color="#475569")
    fig.tight_layout(rect=[0, .05, 1, .95])
    return fig


def draw_paliers_comparison(speed_path, speed_data, direction_path, direction_data):
    """Add a steering-vs-speed plot aligned by time for PALIERS experiments."""
    fig, (ax, speed_ax) = plt.subplots(2, 1, figsize=(10.5, 7.6), sharex=True)
    fig.suptitle(f"PALIERS: steering at different speeds — {speed_path.stem}",
                 fontsize=12, weight="bold")
    ax.plot(direction_data["temps_s"], direction_data["mesure_m"],
            color="#1d4ed8", lw=1.8, label="Car lateral position")
    if "consigne_m" in direction_data:
        ax.plot(direction_data["temps_s"], direction_data["consigne_m"],
                color="#059669", ls=":", lw=1.5, label="Target lane position")
    ax.set_ylabel("Lateral position (m)")
    ax.grid(alpha=.25)
    ax.legend(fontsize=9)

    speed_ax.plot(speed_data["temps_s"], speed_data["mesure_kmh"],
                  color="#1d4ed8", lw=1.7, label="Actual speed")
    if "consigne_kmh" in speed_data:
        speed_ax.plot(speed_data["temps_s"], speed_data["consigne_kmh"],
                      color="#059669", lw=1.5, ls=":", label="Target speed")
    speed_ax.set_ylabel("Speed (km/h)")
    speed_ax.set_xlabel("Time (s)")
    speed_ax.grid(alpha=.25)
    speed_ax.legend(fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, .95])
    return fig


def main():
    trials = {"direction": [], "vitesse": []}
    by_path = {}
    for path in sorted(ROOT.glob("*.csv")):
        parsed = load_csv(path)
        if parsed is None:
            continue
        kind, data = parsed
        trials[kind].append((path, data))
        by_path[path] = (kind, data)

    if not any(trials.values()):
        print("No compatible steering or speed CSV files found in:", ROOT)
        return

    for kind, entries in trials.items():
        if not entries:
            continue
        last_by_conditions = {}
        merged = OUTPUT / f"tous_les_essais_{kind}.pdf"
        with PdfPages(merged) as combined:
            for path, data in entries:
                group = conditions(path, kind)
                fig = draw(path, data, kind, last_by_conditions.get(group))
                individual = OUTPUT / f"{path.stem}.pdf"
                fig.savefig(individual)
                combined.savefig(fig)
                plt.close(fig)
                last_by_conditions[group] = (path, data)
                print("Created:", individual.name)
        print("Combined report:", merged.name)

    # PALIERS exports a main speed CSV and a companion *_direction.csv.
    # Create an aligned comparison only when both files are actually present.
    for speed_path, speed_data in trials["vitesse"]:
        if "PALIERS" not in speed_path.stem.upper():
            continue
        direction_path = speed_path.with_name(speed_path.stem + "_direction.csv")
        linked = by_path.get(direction_path)
        if linked is None or linked[0] != "direction":
            continue
        fig = draw_paliers_comparison(speed_path, speed_data, direction_path, linked[1])
        out = OUTPUT / f"{speed_path.stem}_comparaison_direction_vitesse.pdf"
        fig.savefig(out)
        plt.close(fig)
        print("Created:", out.name)

    print("Done! Graphs saved in:", OUTPUT)


if __name__ == "__main__":
    main()
