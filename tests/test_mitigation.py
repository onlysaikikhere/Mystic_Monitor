import unittest
from unittest.mock import patch, MagicMock
import os
import signal
import time

# Mock config before importing daemon so it doesn't fail based on real files
patch('configparser.ConfigParser.read').start()

import daemon.mystic_daemon as mystic_daemon

class TestMitigationLogic(unittest.TestCase):
    def setUp(self):
        # Reset daemon state
        mystic_daemon.reaper_tracking.clear()
        mystic_daemon.trip_tracking.clear()
        mystic_daemon.cooldown_tracking.clear()
        
        # Override config mapping
        mystic_daemon.config['ActiveMitigation'] = {
            'mode': 'kill',
            'consecutive_trips': '3',
            'cooldown_seconds': '30',
            'enable_throttling': 'true',
            'throttle_cpu_threshold': '40.0',
            'enable_reaper': 'true',
            'reaper_cpu_threshold': '95.0',
            'protected_processes': 'systemd,sshd,bash'
        }

    @patch('daemon.mystic_daemon.psutil.process_iter')
    def test_whitelist_skipped(self, mock_process_iter):
        # Mock process data matching a protected process
        proc1 = MagicMock()
        proc1.info = {'pid': 1, 'name': 'systemd', 'cpu_percent': 99.0, 'cmdline': ['/lib/systemd/systemd']}
        mock_process_iter.return_value = [proc1]

        result = mystic_daemon.mitigate_threat(99.0, 50.0)
        self.assertTrue("WHITELISTED" in result)
        self.assertTrue("systemd" in result)
        self.assertEqual(len(mystic_daemon.reaper_tracking), 0)

    @patch('daemon.mystic_daemon.psutil.process_iter')
    @patch('daemon.mystic_daemon.psutil.Process.nice')
    def test_grace_period_and_tracking(self, mock_nice, mock_process_iter):
        proc1 = MagicMock()
        proc1.info = {'pid': 1000, 'name': 'bad_script.py', 'cpu_percent': 99.0, 'cmdline': ['python3']}
        mock_process_iter.return_value = [proc1]

        # In "kill" mode requiring consecutive_trips = 3, first 2 are TRACKING
        res1 = mystic_daemon.mitigate_threat(99.0, 50.0)
        res2 = mystic_daemon.mitigate_threat(99.0, 50.0)
        self.assertTrue("TRACKING" in res1)
        self.assertTrue("TRACKING" in res2)
        
        # 3rd trip enters Reaper logic but is within 15 seconds
        with patch('daemon.mystic_daemon.time.time', return_value=time.time()):
            res3 = mystic_daemon.mitigate_threat(99.0, 50.0)
            self.assertTrue("GRACE PENDING" in res3)
            self.assertEqual(len(mystic_daemon.reaper_tracking), 1)
            mock_nice.assert_called_with(19)

    @patch('daemon.mystic_daemon.psutil.process_iter')
    @patch('daemon.mystic_daemon.os.kill')
    def test_escalation_to_sigkill(self, mock_kill, mock_process_iter):
        proc1 = MagicMock()
        proc1.info = {'pid': 1000, 'name': 'bad_script.py', 'cpu_percent': 99.0, 'cmdline': ['python3']}
        mock_process_iter.return_value = [proc1]

        # Fast forward trips to require the kill check mapping
        mystic_daemon.trip_tracking[1000] = 3
        # Set reaper tracking 16 seconds in the past
        mystic_daemon.reaper_tracking[1000] = time.time() - 16

        res = mystic_daemon.mitigate_threat(99.0, 50.0)
        
        self.assertTrue("KILLED (SIGKILL)" in res)
        mock_kill.assert_called_with(1000, signal.SIGKILL)
        self.assertTrue(1000 in mystic_daemon.cooldown_tracking)
        self.assertFalse(1000 in mystic_daemon.reaper_tracking)
        self.assertEqual(mystic_daemon.trip_tracking[1000], 0)

if __name__ == '__main__':
    unittest.main()
