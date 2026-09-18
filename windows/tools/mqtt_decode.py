#!/usr/bin/env python3
r"""Decode a loopback MQTT capture of the vendor stack into readable JSONL.

Issue #4 wanted the wire protocol between `GamingCenter3_Cross` (the UWP UI) and
`GCUService`, captured non-invasively. `dumpcap` on Npcap's loopback adapter,
filtered to the broker port, produces a `.pcapng`; this turns that into one JSON
object per MQTT control message, with the payloads decoded from hex to the
plaintext JSON they turn out to be.

    # capture (elevated, Npcap loopback adapter installed):
    dumpcap -i \Device\NPF_Loopback -f "tcp port 13688" -a duration:150 -w cap.pcapng
    # decode:
    python windows\tools\mqtt_decode.py cap.pcapng --out evidence/mqtt-capture/session.jsonl

Reads the capture through `tshark`, so Wireshark must be installed and on PATH
(or pass --tshark). Only reads; captures and drives nothing.
"""
import argparse
import json
import shutil
import subprocess
import sys

# MQTT control-packet type nibbles, for the summary.
MSGTYPE = {1: "CONNECT", 2: "CONNACK", 3: "PUBLISH", 4: "PUBACK",
           8: "SUBSCRIBE", 9: "SUBACK", 12: "PINGREQ", 13: "PINGRESP",
           14: "DISCONNECT"}


def find_tshark(explicit):
    if explicit:
        return explicit
    for c in ("tshark", r"C:\Program Files\Wireshark\tshark.exe"):
        if shutil.which(c) or (c.endswith(".exe") and __import__("os").path.exists(c)):
            return c
    sys.exit("tshark not found; install Wireshark or pass --tshark")


def hex_to_payload(h):
    """Vendor payloads are plaintext JSON; fall back to text, then hex."""
    if not h:
        return None, None
    raw = bytes.fromhex(h.replace(":", ""))
    try:
        return "json", json.loads(raw.decode("utf-8"))
    except Exception:
        pass
    try:
        s = raw.decode("utf-8")
        return "text", s
    except Exception:
        return "hex", raw.hex()


def run(tshark, pcap):
    fields = ["frame.number", "frame.time_epoch", "tcp.srcport", "tcp.dstport",
              "mqtt.msgtype", "mqtt.topic", "mqtt.msg",
              "mqtt.clientid", "mqtt.username", "mqtt.passwd"]
    cmd = [tshark, "-r", pcap, "-d", "tcp.port==13688,mqtt", "-Y", "mqtt",
           "-T", "fields", "-E", "separator=\t"]
    for f in fields:
        cmd += ["-e", f]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < len(fields):
            parts += [""] * (len(fields) - len(parts))
        (num, epoch, sp, dp, mtype, topic, msg, cid, user, pw) = parts[:len(fields)]
        # A frame can hold several MQTT messages; tshark comma-joins repeats.
        yield {
            "frame": num, "epoch": epoch, "srcport": sp, "dstport": dp,
            "msgtype": mtype, "topic": topic, "msg": msg,
            "clientid": cid, "username": user, "passwd": pw,
        }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pcap")
    ap.add_argument("--out", help="write JSONL here (default: stdout)")
    ap.add_argument("--tshark")
    ap.add_argument("--topic", help="only this topic substring")
    args = ap.parse_args(argv)

    tshark = find_tshark(args.tshark)
    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout

    n_pub = n_conn = 0
    seen_topics = {}
    for rec in run(tshark, args.pcap):
        # Split the comma-joined repeats a multi-message frame produces.
        topics = rec["topic"].split(",") if rec["topic"] else [""]
        msgs = rec["msg"].split(",") if rec["msg"] else [""]
        types = rec["msgtype"].split(",") if rec["msgtype"] else [""]
        for i, mt in enumerate(types):
            topic = topics[i] if i < len(topics) else ""
            msg = msgs[i] if i < len(msgs) else ""
            if args.topic and args.topic not in topic:
                continue
            fmt, payload = hex_to_payload(msg)
            row = {
                "epoch": float(rec["epoch"]) if rec["epoch"] else None,
                "type": MSGTYPE.get(int(mt) if mt.isdigit() else -1, mt),
                "topic": topic or None,
                "format": fmt,
                "payload": payload,
            }
            if mt == "1":       # CONNECT: keep the credentials
                n_conn += 1
                row["clientid"] = rec["clientid"] or None
                row["username"] = rec["username"] or None
                # passwd is captured as hex bytes by tshark
                pw = rec["passwd"]
                if pw:
                    try:
                        row["password"] = bytes.fromhex(pw.replace(":", "")).decode(
                            "utf-8", "replace")
                    except Exception:
                        row["password"] = pw
            if row["type"] == "PUBLISH":
                n_pub += 1
                seen_topics[topic] = seen_topics.get(topic, 0) + 1
            if row["type"] in ("PUBLISH", "CONNECT"):
                out.write(json.dumps(row, ensure_ascii=False) + "\n")

    if args.out:
        out.close()
        print(f"{n_pub} PUBLISH, {n_conn} CONNECT written to {args.out}")
        print("topics seen:")
        for t, c in sorted(seen_topics.items()):
            print(f"  {c:4}  {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
