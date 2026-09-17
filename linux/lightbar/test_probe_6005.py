#!/usr/bin/env python3
"""Offline checks; no HID nodes are opened and no commands reach hardware."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('probe', Path(__file__).with_name('probe-6005.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_ioctl_encoding(self):
        self.assertEqual(probe.ioctl_code(3, 0x06, 8), 0xc0084806)
        self.assertEqual(probe.ioctl_code(2, 0x03, 8), 0x80084803)

    def run_mock(self, fail_first=False, dry=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dev = root / 'device'
            dev.mkdir()
            (dev / 'uevent').write_text('HID_ID=0003:0000048D:00006005\n')
            (dev / 'driver').symlink_to(root / 'hid-generic')
            log = root / 'run.jsonl'
            argv = ['probe'] if dry else ['probe', '--execute', '--log', str(log)]
            requests = []

            def ioctl(fd, code, buf, mutate):
                requests.append((code, bytes(buf)))
                if fail_first and len(requests) == 1:
                    raise OSError('mock transfer failure')
                return len(buf)

            with patch.object(probe, 'discover', return_value=(dev, Path('/dev/mock'))), \
                 patch.object(probe, 'verify_fd'), \
                 patch.object(probe.os, 'open', return_value=99) as opened, \
                 patch.object(probe.os, 'close') as closed, \
                 patch.object(probe.fcntl, 'ioctl', side_effect=ioctl), \
                 patch.object(probe.time, 'sleep'), \
                 patch('sys.argv', argv), patch('builtins.print', wraps=print):
                if fail_first:
                    with self.assertRaises(SystemExit):
                        probe.main()
                else:
                    probe.main()
                if dry:
                    opened.assert_not_called()
                    self.assertFalse(log.exists())
                else:
                    closed.assert_called_once_with(99)
                    rows = [json.loads(line) for line in log.read_text().splitlines()]
                    self.assertEqual(rows[-1]['visual_result'], 'pending human report')
                    self.assertFalse(rows[-1]['original_effect_restored'])
                    self.assertEqual(rows[-1]['transport_ok'], not fail_first)
            return requests

    def test_dry_run_has_no_open(self):
        self.assertEqual(self.run_mock(dry=True), [])

    def test_sequence_and_framing(self):
        requests = self.run_mock()
        self.assertEqual([b for _, b in requests], list(probe.RED + probe.OFF))
        self.assertTrue(all(code == 0xc0084806 for code, _ in requests))

    def test_error_stops_red_but_attempts_off(self):
        requests = self.run_mock(fail_first=True)
        self.assertEqual([b for _, b in requests], [probe.RED[0], *probe.OFF])


if __name__ == '__main__':
    unittest.main()
