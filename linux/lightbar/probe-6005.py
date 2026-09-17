#!/usr/bin/env python3
"""One bounded, experimental 6010-protocol test on the GM7MG7P's 6005 HID.

Dry-run by default. --execute requires a human watching the lightbar.
The final zero-brightness request is best-effort OFF, NOT effect restoration.
No EC writes, driver rebinding, timeout/save commands, or opcode sweeps.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import time
from datetime import datetime, timezone

SOURCE = "https://github.com/tuxedocomputers/tuxedo-drivers/blob/2c6bf54075fb38a7fdbefc560734281984bf65bc/src/ite_8291_lb/ite_8291_lb.c"
SOURCE_SHA256 = "de9839b61d0bf01f53e9be1a2b8399521e51292562a42287793b880a393379a0"
DESCRIPTOR = bytes.fromhex("0603ff0901a101150026ff0075089540092081020921910209229508b102c0")
RED = (bytes.fromhex("14 00 01 ff 00 00 00 00"),
       bytes.fromhex("08 02 01 01 14 08 00 00"))
OFF = (bytes.fromhex("14 00 01 00 00 00 00 00"),
       bytes.fromhex("08 02 01 01 00 08 00 00"))


def ioctl_code(direction, number, size):
    # Linux asm-generic ioctl encoding; this probe is restricted to x86_64.
    return (direction << 30) | (size << 16) | (ord('H') << 8) | number


def discover():
    if os.uname().machine != 'x86_64':
        raise RuntimeError('this probe only supports x86_64 Linux')
    board = Path('/sys/class/dmi/id/board_name').read_text().strip()
    if board != 'GM7MG7P':
        raise RuntimeError(f'unexpected board: {board}')
    devices = list(Path('/sys/bus/hid/devices').glob('0003:048D:6005.*'))
    if len(devices) != 1:
        raise RuntimeError(f'expected exactly one 048d:6005 HID, got {len(devices)}')
    device = devices[0]
    if (device / 'report_descriptor').read_bytes() != DESCRIPTOR:
        raise RuntimeError('report descriptor mismatch')
    nodes = list((device / 'hidraw').glob('hidraw*'))
    if len(nodes) != 1:
        raise RuntimeError('expected exactly one hidraw node')
    return device, Path('/dev') / nodes[0].name


def verify_fd(fd):
    info = bytearray(8)
    fcntl.ioctl(fd, ioctl_code(2, 0x03, 8), info, True)  # HIDIOCGRAWINFO
    if struct.unpack('IHH', info) != (3, 0x048d, 0x6005):
        raise RuntimeError('opened hidraw identity mismatch')
    size = bytearray(4)
    fcntl.ioctl(fd, ioctl_code(2, 0x01, 4), size, True)  # HIDIOCGRDESCSIZE
    if struct.unpack('I', size)[0] != len(DESCRIPTOR):
        raise RuntimeError('opened hidraw descriptor size mismatch')
    desc = bytearray(4100)
    struct.pack_into('I', desc, 0, len(DESCRIPTOR))
    fcntl.ioctl(fd, ioctl_code(2, 0x02, 4100), desc, True)  # HIDIOCGRDESC
    if bytes(desc[4:4 + len(DESCRIPTOR)]) != DESCRIPTOR:
        raise RuntimeError('opened hidraw descriptor mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--log', type=Path, help='new JSONL file, never overwritten')
    parser.add_argument('--baseline', default='not observed')
    args = parser.parse_args()
    if args.execute and not args.log:
        parser.error('--execute requires --log')
    device, node = discover()
    print(f'{device.name} -> {node}; descriptor matches FF03/64/64/8')
    print('Candidate: 6010 static red at 20/100 for 10 seconds, then best-effort off.')
    for phase, reports in (('red', RED), ('off', OFF)):
        for report in reports:
            print(f'{phase}: HIDIOCSFEATURE len=8 reportnum=0x{report[0]:02x} {report.hex(" ")}')
    if not args.execute:
        return

    with args.log.open('x') as log:
        def record(event, **fields):
            row = dict(ts=datetime.now(timezone.utc).isoformat(),
                       monotonic=time.monotonic(), event=event, **fields)
            print(json.dumps(row), file=log, flush=True)
            print(json.dumps(row), flush=True)

        record('baseline', observation=args.baseline, observer='user',
               kernel=os.uname().release, board='GM7MG7P', hid=device.name,
               node=str(node), driver=(device / 'driver').resolve().name,
               uevent=(device / 'uevent').read_text(),
               descriptor_hex=DESCRIPTOR.hex(),
               descriptor_sha256=hashlib.sha256(DESCRIPTOR).hexdigest(),
               source=SOURCE, source_sha256=SOURCE_SHA256,
               note='6010 sequence on unverified 6005; not effect restoration')
        fd = os.open(node, os.O_RDWR | os.O_CLOEXEC)
        touched = False
        failed = False

        def send(report, phase):
            # Match upstream hid_hw_raw_request(buf[0], buf, 8, FEATURE, SET).
            # Do NOT prepend zero: that changes reportnum/wValue from upstream.
            # The descriptor is unnumbered, but upstream uses opcode reportnums.
            record('request', phase=phase, hex=report.hex(' '), length=8,
                   reportnum=report[0], usb_wValue=0x300 | report[0])
            ret = fcntl.ioctl(fd, ioctl_code(3, 0x06, 8), bytearray(report), True)
            record('return', phase=phase, result=ret)
            if ret != len(report):
                raise RuntimeError(f'short SET_FEATURE return: {ret}')

        def interrupted(signum, frame):
            raise InterruptedError(f'signal {signum}')

        old_handlers = {s: signal.signal(s, interrupted)
                        for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            verify_fd(fd)
            record('opened_identity_verified')
            touched = True
            for report in RED:
                send(report, 'red')
                time.sleep(0.1)
            record('red_hold_start', seconds=10)
            time.sleep(10)
        except Exception as exc:
            record('error', error=repr(exc))
            failed = True
        finally:
            # A second interrupt must not skip cleanup; SIGKILL/power loss still can.
            for s in old_handlers:
                signal.signal(s, signal.SIG_IGN)
            if touched:
                for report in OFF:
                    try:
                        send(report, 'off_attempt')
                        time.sleep(0.1)
                    except Exception as exc:
                        record('off_error', error=repr(exc))
                        failed = True
            os.close(fd)
            for s, handler in old_handlers.items():
                signal.signal(s, handler)
        record('finished', transport_ok=not failed,
               visual_result='pending human report', original_effect_restored=False)
        if failed:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
