import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InstallTests(unittest.TestCase):
    def test_install_command_is_runnable_idempotent_and_preserves_conflicts(self):
        project=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);bin=home/'bin';bin.mkdir()
            herdr=bin/'herdr';herdr.write_text('#!/bin/sh\nexit 0\n');herdr.chmod(0o755)
            env={**os.environ,'HOME':str(home),'PATH':str(bin)+':'+os.environ['PATH']}
            command=home/'.local/bin/left-undone'
            for _ in range(2):
                result=subprocess.run([sys.executable,str(project/'install.py')],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertTrue(command.is_symlink())
                result=subprocess.run([str(command),'--help'],env=env,cwd=home,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('--repo',result.stdout)
            command.unlink();command.write_text('unrelated command')
            result=subprocess.run([sys.executable,str(project/'install.py')],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(command.read_text(),'unrelated command')
