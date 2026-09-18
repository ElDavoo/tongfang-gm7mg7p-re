#!/usr/bin/env python3
r"""Subscribe to the vendor stack's local MQTT broker and log every message.

Issue #4 proposes capturing this traffic with Wireshark over an Npcap loopback
adapter. That needs a driver install. It is not necessary: the broker is a
broker, it accepts connections, and an ordinary MQTT client subscribed to `#`
sees the same traffic with nothing installed at all.

`GCUBridge.exe` listens on TCP 13688 (`Get-NetTCPConnection -State Listen`).
`GamingCenter3_Cross` (the UWP UI) ships `M2Mqtt.Net.dll` and its assembly
carries topic strings like `BatteryProtection/Control`, `System/Control` and
`Setting/Control`, so that port is where the UI and `GCUService` talk.

This tool only ever subscribes. It never publishes: a publish on these topics
is a command to the laptop's hardware, and observing IPC is not the same thing
as driving it.

Speaks just enough MQTT 3.1.1 by hand (CONNECT / SUBSCRIBE / PUBLISH /
PINGREQ) to avoid adding a dependency to this repo's tooling.

Usage:
  mqtt_sniff.py                          # subscribe to '#', print to stdout
  mqtt_sniff.py --seconds 120 --out evidence/mqtt-capture/session.jsonl
  mqtt_sniff.py --host 127.0.0.1 --port 13688
"""
import argparse
import datetime
import json
import socket
import sys
import time

CONNECT, CONNACK = 0x10, 0x20
PUBLISH, SUBSCRIBE, SUBACK = 0x30, 0x82, 0x90
PINGREQ, PINGRESP = 0xC0, 0xD0

CONNACK_ERRORS = {
    0: "accepted",
    1: "refused: unacceptable protocol version",
    2: "refused: identifier rejected",
    3: "refused: server unavailable",
    4: "refused: bad user name or password",
    5: "refused: not authorized",
}


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def encode_len(n):
    """MQTT's variable-length integer."""
    out = bytearray()
    while True:
        b = n % 128
        n //= 128
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def encode_str(s):
    b = s.encode("utf-8")
    return len(b).to_bytes(2, "big") + b


class Mqtt:
    def __init__(self, host, port, client_id, timeout=1.0,
                 username=None, password=None):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(timeout)
        self.buf = b""
        self._connect(client_id, username, password)

    def _send(self, packet_type, payload, flags=0):
        self.sock.sendall(bytes([packet_type | flags]) + encode_len(len(payload))
                          + payload)

    def _connect(self, client_id, username=None, password=None):
        # This broker (GCUBridge) requires a credential triplet: the client-id
        # must be <Family>_<N> for N in a bounded low range, with a matching
        # <Family>_User_<N> username and <Family>_Pwd888881772688_<N> password.
        # A wrong password gives CONNACK code 4; a missing/mismatched user or an
        # out-of-range N gives code 2. See windows/mqtt-protocol.md.
        connect_flags = 0x02                      # clean session
        if username is not None:
            connect_flags |= 0x80
        if password is not None:
            connect_flags |= 0x40
        payload = (encode_str("MQTT") + bytes([4])   # protocol level 3.1.1
                   + bytes([connect_flags])
                   + (60).to_bytes(2, "big")         # keepalive
                   + encode_str(client_id))
        if username is not None:
            payload += encode_str(username)
        if password is not None:
            payload += encode_str(password)
        self._send(CONNECT, payload)
        hdr, body = self._read_packet(blocking=True)
        if hdr is None or (hdr & 0xF0) != CONNACK:
            raise RuntimeError(f"no CONNACK (got {hdr})")
        code = body[1] if len(body) > 1 else 255
        if code != 0:
            raise RuntimeError(f"broker rejected the connection -- "
                               f"{CONNACK_ERRORS.get(code, f'code {code}')}")

    def subscribe(self, topic, packet_id=1):
        payload = packet_id.to_bytes(2, "big") + encode_str(topic) + bytes([0])
        self._send(SUBSCRIBE, payload, flags=0x02)

    def ping(self):
        self._send(PINGREQ, b"")

    def _fill(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("broker closed the connection")
            self.buf += chunk

    def _read_packet(self, blocking=False):
        """Return (header_byte, body) or (None, None) if nothing is waiting."""
        try:
            self._fill(1)
        except socket.timeout:
            if blocking:
                raise
            return None, None
        hdr = self.buf[0]
        mult, value, i = 1, 0, 1
        while True:
            self._fill(i + 1)
            b = self.buf[i]
            value += (b & 0x7F) * mult
            i += 1
            if not b & 0x80:
                break
            mult *= 128
        self._fill(i + value)
        body = self.buf[i:i + value]
        self.buf = self.buf[i + value:]
        return hdr, body


def decode_publish(hdr, body):
    qos = (hdr & 0x06) >> 1
    tlen = int.from_bytes(body[:2], "big")
    topic = body[2:2 + tlen].decode("utf-8", "replace")
    rest = body[2 + tlen:]
    if qos > 0:
        rest = rest[2:]            # skip packet identifier
    return topic, rest


def render(raw):
    """Prefer JSON, then text, then hex -- the payload format is what we're after."""
    try:
        return "json", json.loads(raw.decode("utf-8"))
    except Exception:
        pass
    try:
        s = raw.decode("utf-8")
        if s.isprintable() or s.strip():
            return "text", s
    except Exception:
        pass
    return "hex", raw.hex()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=13688)
    ap.add_argument("--topic", default="#")
    ap.add_argument("--seconds", type=float, default=0)
    ap.add_argument("--out", help="append each message as one JSON object per line")
    ap.add_argument("--client-id", default="ec-re-observer")
    ap.add_argument("--username", help="broker username (this broker needs one; "
                    "see windows/mqtt-protocol.md)")
    ap.add_argument("--password", help="broker password")
    args = ap.parse_args(argv)

    try:
        m = Mqtt(args.host, args.port, args.client_id,
                 username=args.username, password=args.password)
    except Exception as e:
        print(f"could not attach to the broker at {args.host}:{args.port}: {e}",
              file=sys.stderr)
        return 1

    m.subscribe(args.topic)
    print(f"{now()}  subscribed to '{args.topic}' on {args.host}:{args.port}",
          flush=True)

    out = open(args.out, "a", encoding="utf-8") if args.out else None
    t0 = last_ping = time.time()
    count = 0
    try:
        while True:
            try:
                hdr, body = m._read_packet()
            except socket.timeout:
                hdr = None
            if hdr is not None and (hdr & 0xF0) == PUBLISH:
                topic, raw = decode_publish(hdr, body)
                kind, value = render(raw)
                count += 1
                rec = {"ts": now(), "topic": topic, "format": kind,
                       "payload": value, "bytes": len(raw)}
                print(f"{rec['ts']}  {topic}  [{kind}, {len(raw)}B]  "
                      f"{json.dumps(value) if kind == 'json' else value}",
                      flush=True)
                if out:
                    out.write(json.dumps(rec) + "\n")
                    out.flush()
            if time.time() - last_ping > 30:
                m.ping()
                last_ping = time.time()
            if args.seconds and time.time() - t0 >= args.seconds:
                break
    except KeyboardInterrupt:
        pass
    except ConnectionError as e:
        print(f"connection lost: {e}", file=sys.stderr)
    finally:
        if out:
            out.close()
        m.sock.close()
    print(f"\n{count} messages in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
