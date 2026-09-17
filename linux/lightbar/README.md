# GM7MG7P 048d:6005 lightbar: first working Linux control

Issue #5. On 2026-09-17, `probe-6005.py` sent the static-colour sequence from
`ite_8291_lb`'s **6010** branch to the physical **6005** device. The user saw
rainbow → red → dark, with no keyboard change. See
[human observation](../../evidence/hid/2026-09-17-6005-observation.md) and the
raw `../../evidence/hid/2026-09-17-6005-6010-static.jsonl` transfer log.
This is a userspace protocol test, not a loaded kernel-driver test.

## Reproduce deliberately, with someone watching

From the repository root, dry-run discovery/validation (no HID writes):

```sh
python3 linux/lightbar/probe-6005.py
```

For the bounded live test, as root, choose a **new** log filename and record
what the lightbar is actually doing before the run:

```sh
python3 linux/lightbar/probe-6005.py --execute \
  --log /tmp/lightbar-new-run.jsonl --baseline 'describe current effect here'
```

It checks x86_64, board `GM7MG7P`, exactly one `048d:6005` HID, and the exact
committed FF03 descriptor. It discovers the hidraw node instead of hardcoding
`hidraw1`, and verifies VID/PID and descriptor again on the opened descriptor.
It does not touch the `048d:ce00` keyboard, the EC, or driver bindings.

The test requests static red at 20/100 brightness, holds for 10 seconds, then
attempts static black at zero brightness. **This turns the lightbar off; it
is not restoration of the previous effect.** There is no verified effect
readback/restore implemented here. `finally` attempts off even after a transfer
error or SIGINT/SIGTERM, but SIGKILL, power loss, a blocked ioctl, or failed
transfers can prevent cleanup. Observe the result rather than trusting a
successful return code. Run only with informed agreement to the final dark
state; do not run automatically on boot.

## Exact tested requests and framing

Source: [tuxedo-drivers at 2c6bf54075fb38a7fdbefc560734281984bf65bc](https://github.com/tuxedocomputers/tuxedo-drivers/blob/2c6bf54075fb38a7fdbefc560734281984bf65bc/src/ite_8291_lb/ite_8291_lb.c),
`ite8291_write_lightbar_mono()` lines 195–225, 6010 case at 206–209;
`ite8291_write_control()` lines 135–151. Source SHA-256:
`de9839b61d0bf01f53e9be1a2b8399521e51292562a42287793b880a393379a0`.
The Python byte constants preserve those upstream arrays; no upstream C source
or compiled module is vendored here.

| Phase | 8-byte buffer | Intended meaning |
|---|---|---|
| red | `14 00 01 ff 00 00 00 00` | colour entry 1 = red |
| red | `08 02 01 01 14 08 00 00` | static, brightness 20/100 |
| off attempt | `14 00 01 00 00 00 00 00` | colour entry 1 = black |
| off attempt | `08 02 01 01 00 08 00 00` | static, brightness zero |

These are **HIDIOCSFEATURE**, not output writes. To reproduce upstream's
`hid_hw_raw_request(hdev, buf[0], buf, 8, HID_FEATURE_REPORT, HID_REQ_SET_REPORT)`,
the probe passes the 8-byte buffer directly, using opcode `0x14`/`0x08` as the
report number. It does **not** prepend a zero report-number placeholder.
The device descriptor declares unnumbered 8-byte feature reports, but this
particular upstream raw request uses nonzero command/report numbers anyway.
The log's `usb_wValue` is the expected SET_REPORT value (`0x0314`/`0x0308`),
not a USB capture. Adding a leading zero would change the transaction being
tested; conventional unnumbered-report framing is not interchangeable here.

No `0x1a` timeout/on command, `0x12` picture command, or explicit save request
was sent. The effect commands end in zero, matching the upstream static path
and the vendor's surviving `Save` parameter position; reset/persistence
behaviour on 6005 has **not** been tested. Nor were green/blue, other effects,
brightness scaling, or LED count tested.

## Why `new_id` alone is not the next driver patch

The original issue proposes force-binding stock `ite_8291_lb`. At the pinned
revision the ID table omits 6005, **and** the command functions branch on
`hdev->product`: `ite8291_write_lightbar_mono`, `ite8291_write_on`, and
`ite8291_write_off` return `-ENOSYS` for it. A dynamic ID or a one-line table
addition does not select the 6010 protocol. Probe ignores the initialization
command return values, so a bound `rgb:lightbar` LED device would not itself
prove commands were sent. The module was not built/loaded in this session.

### Remaining work toward a driver contribution

- Test green and blue independently and a small brightness change, one step at
  a time with a human observing. Do not assume one successful red test proves
  all colour channels or brightness mapping.
- Prepare a narrowly scoped 6005 ID/protocol change that routes **static colour**
  to the now-tested sequence, plus an explicit initialization/off policy.
  Do not alias every 6010 command blindly: on/off, timeout/save, effects and
  suspend/resume are separate untested paths. Check transport-error propagation
  as well; the existing static helper discards transfer returns.
- Build/load the resulting driver on the matching kernel; verify the
  `rgb:lightbar` multi-colour sysfs path and reversible binding. Test lifecycle
  behaviour separately, with permission for suspend or other disruptive steps.
- Prepare the patch and PR description **in this repository** for review.
  Do not open anything in tuxedo-drivers without explicit approval. Issue #5
  remains open pending integration and the remaining live checks.

## Offline tests

```sh
python3 -m unittest discover -s linux/lightbar -p 'test_*.py'
```

These mock device discovery, file opening and ioctls. They verify dry-run
behaviour, exact buffer framing, and an off attempt after a simulated transfer
failure. They are not hardware evidence.
