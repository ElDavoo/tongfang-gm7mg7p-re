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

- **`2026-09-23-power-mode-cycle.pcapng`**: `dumpcap` on Npcap's loopback
  adapter, `tcp port 13688`, 2026-09-23 17:57-18:00. It covers an AC
  plug-in, a battery-protection change (`HEALTHYMODE`, then
  `PERFORMANCEDMODE`) and six Fn-key power-mode switches. There are no
  `Fan/Control` mode commands in it, because the hotkey path never goes
  through the UI. It does carry `Tray/Status`, `Fan/Status` and
  `Fan/Table` for each switch. Recorded alongside the `ec-watch` files of
  the same date (issue #92; `windows/vendor-ec-map.md` "Power modes").
- **`2026-09-23-power-mode-cycle.jsonl`**: derived from it the same way.

The `.pcapng` is the ground truth; the `.jsonl` is derived and committed
for readability and grep-ability.
