#!/usr/bin/env python3
"""Assemble per-platform screenshots into one labeled contact sheet via ImageMagick.

PIL isn't installed on the bento box, but `montage` is — so we shell out to it. Given
two prefixes (the two states) it builds a grid with one row per platform and two
columns (the two states), each cell labeled "<platform> · <state>". The result is a
single PNG the user can open to eyeball the visual diff across every platform at once.

Usage:
  contact_sheet.py STATE_A STATE_B [--labels "before,after"]
                   [--platforms web,ios,android] [--dir DIR] [-o OUT]

Expects DIR/STATE-<platform>.png to exist for each state/platform (as produced by
capture.py). Missing cells are reported and skipped rather than aborting the sheet.
"""
import argparse, os, subprocess, sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("state_a")
    p.add_argument("state_b")
    p.add_argument("--labels", default=None, help='comma-separated column labels, defaults to the prefixes')
    p.add_argument("--platforms", default="web,ios,android")
    p.add_argument("--dir", default="/home/bento/snap/chromium/common/screenshots")
    p.add_argument("--cell-width", type=int, default=500, help="max px width per cell (shrinks, never enlarges)")
    p.add_argument("-o", "--out", default="/home/bento/snap/chromium/common/screenshots/contact-sheet.png")
    args = p.parse_args()

    platforms = [x.strip() for x in args.platforms.split(",") if x.strip()]
    states = [args.state_a, args.state_b]
    if args.labels:
        labels = [x.strip() for x in args.labels.split(",")]
    else:
        labels = states
    if len(labels) != 2:
        print("--labels must have exactly two comma-separated values"); sys.exit(1)

    cmd = ["montage"]
    missing = []
    for plat in platforms:                       # one row per platform
        for state, label in zip(states, labels):  # two columns: state A | state B
            path = os.path.join(args.dir, f"{state}-{plat}.png")
            if not os.path.exists(path):
                missing.append(path)
                continue
            cmd += ["-label", f"{plat} · {label}", path]

    if missing:
        print("WARNING: missing cells (skipped):")
        for m in missing:
            print(f"  {m}")
    if len(cmd) == 1:
        print("No input images found — nothing to assemble."); sys.exit(1)

    cmd += [
        "-tile", f"2x{len(platforms)}",
        "-geometry", f"{args.cell_width}x+8+8",
        "-background", "white", "-fill", "black",
        "-title", f"{labels[0]}  vs  {labels[1]}",
        args.out,
    ]
    print("Running:", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode == 0:
        print(f"\nContact sheet: {args.out}")
    else:
        print(f"montage failed (exit {r.returncode})"); sys.exit(r.returncode)


if __name__ == "__main__":
    main()
