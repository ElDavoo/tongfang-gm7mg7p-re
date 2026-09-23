#!/usr/bin/env python3
r"""Replay an ec_watch capture of the fan-table window (0x0F00-0x0F5F) and
check every table state it passed through against what the vendor service
says it wrote.

The vendor service publishes each table it applies on the MQTT topic
`Fan/Table`, as the JSON `FanTable1p5` object (`Name`, `CPU[16]`, `GPU[16]`,
each entry `UpT`/`DownT`/`Duty`). It writes that object to the EC with
`FanTable_Manager1p5.SetEcFanTable`
(windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan.FanTable/
FanTable_Manager1p5.cs:556), whose layout `ec_image()` below copies:

    0x0F00 + i   CPU entry[i+1].UpT        (i = 15: 0xFF)
    0x0F11 + i   CPU entry[i].DownT        (i < 15; 0x0F10 is never written)
    0x0F20 + i   CPU entry[i].Duty * 2     (duty in %, stored as 0-200)
    0x0F30...    the same three rows for the GPU

ec_watch only logs changes, so the replay needs one absolute anchor: a dump of
the window taken after the capture (`ecrw.py dump 0x0F00 0x60`). Walking the
logged changes backwards from it gives the table after each write burst. A
burst is a run of changes with no gap over --gap seconds.

This reads committed files only; it touches no hardware.

Usage:
  fan_table_replay.py --csv evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-0f5f.csv \
      --final evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt \
      --mqtt evidence/mqtt-capture/2026-09-23-power-mode-cycle.jsonl
"""
import argparse
import csv
import datetime
import json
import sys


def ec_image(table):
    """EC bytes FanTable_Manager1p5.SetEcFanTable writes for one table."""
    img = {}
    for side, base in (("CPU", 0x0F00), ("GPU", 0x0F30)):
        e = table[side]
        for i in range(16):
            img[base + i] = e[i + 1]["UpT"] if i < 15 else 0xFF
            if i < 15:
                img[base + 0x11 + i] = e[i]["DownT"]
            img[base + 0x20 + i] = (e[i]["Duty"] * 2) & 0xFF
    return img


def load_final(path):
    mem = {}
    for line in open(path):
        if ":" not in line or line.startswith("#"):
            continue
        a, b = line.split(":", 1)
        for k, v in enumerate(b.split()):
            mem[int(a, 16) + k] = int(v, 16)
    return mem


def load_bursts(path, gap):
    bursts, cur, last = [], [], None
    for r in csv.DictReader(open(path)):
        t = datetime.datetime.fromisoformat(r["ts"])
        if last is not None and (t - last).total_seconds() > gap:
            bursts.append(cur)
            cur = []
        cur.append(r)
        last = t
    if cur:
        bursts.append(cur)
    return bursts


def load_published(path):
    """Fan/Table publishes in order, de-duplicated (the broker echoes each)."""
    out, seen = [], set()
    for line in open(path):
        o = json.loads(line)
        if o.get("type") != "PUBLISH" or o.get("topic") != "Fan/Table":
            continue
        key = (round(o["epoch"], 1), o["payload"]["Name"])
        if key not in seen:
            seen.add(key)
            out.append((o["epoch"], o["payload"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="ec_watch CSV of 0x0F00-0x0F5F")
    ap.add_argument("--final", required=True, help="ecrw.py dump taken after the capture")
    ap.add_argument("--mqtt", required=True, help="decoded MQTT JSONL with Fan/Table")
    ap.add_argument("--gap", type=float, default=1.0)
    args = ap.parse_args(argv)

    bursts = load_bursts(args.csv, args.gap)
    published = load_published(args.mqtt)
    tables = {p["Name"]: p for _, p in published}

    # states[k] = the window after burst k-1; states[0] = before the first burst.
    state = load_final(args.final)
    states = [dict(state)]
    for b in reversed(bursts):
        for r in reversed(b):
            a = int(r["addr"], 16)
            if state[a] != int(r["new"], 16):
                sys.exit(f"replay broke at {r}: anchor/log disagree")
            state[a] = int(r["old"], 16)
        states.append(dict(state))
    states.reverse()

    def which(st):
        hits = [n for n, t in tables.items()
                if all(st[a] == v for a, v in ec_image(t).items())]
        return ", ".join(sorted(hits)) or "no published table"

    print(f"{len(bursts)} write bursts, {len(published)} Fan/Table publishes")
    print(f"  before first burst: {which(states[0])}")
    ok = True
    for k, b in enumerate(bursts):
        t0 = b[0]["ts"][11:23]
        t1 = b[-1]["ts"][11:23]
        after = datetime.datetime.fromisoformat(b[-1]["ts"]).timestamp()
        # the table the service announced most recently before the burst ended
        named = [p["Name"] for e, p in published if e <= after + 1.0]
        want = named[-1] if named else None
        got = which(states[k + 1])
        match = want is not None and want in got.split(", ")
        ok &= match
        print(f"  burst {k + 1} {t0}-{t1} ({len(b)} bytes): EC = {got}; "
              f"last announced {want}: {'MATCH' if match else 'MISMATCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
