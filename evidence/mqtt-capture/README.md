# MQTT captures — vendor Control Center ↔ GCUService (issue #4)

Non-invasive loopback captures of the local MQTT broker (`GCUBridge.exe`,
TCP 13688). Protocol reference and topic map: `windows/mqtt-protocol.md`.
Battery-specific conclusion: `docs/findings.md` §4h.

## Files

- **`2026-09-18-profile-and-connect.pcapng`** — raw `dumpcap` capture on
  Npcap's loopback adapter, filtered to `tcp port 13688`, 150 s. Recorded
  on Control Center 3.1.39.0 while cycling the three battery modes and
  restarting the UWP UI (so the CONNECT handshake is captured too).
- **`2026-09-18-profile-and-connect.jsonl`** — one JSON object per MQTT
  PUBLISH/CONNECT, payloads decoded from hex to their plaintext JSON.
  Produced by `windows/tools/mqtt_decode.py` from the `.pcapng`; regenerate
  with:

      python windows/tools/mqtt_decode.py \
        evidence/mqtt-capture/2026-09-18-profile-and-connect.pcapng \
        --out evidence/mqtt-capture/2026-09-18-profile-and-connect.jsonl

The `.pcapng` is the ground truth; the `.jsonl` is derived and committed
for readability and grep-ability.
