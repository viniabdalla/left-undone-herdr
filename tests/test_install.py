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
            herdr=bin/'herdr';herdr.write_text("""#!/bin/sh
state="$HOME/plugin-root"
case "$2" in
    list)
        if test -f "$state"; then
            printf '{"result":{"plugins":[{"plugin_id":"left-undone","plugin_root":"%s","source":{"kind":"local"}}]}}\n' "$(cat "$state")"
        else
            printf '{"result":{"plugins":[]}}\n'
        fi
        ;;
    link) printf '%s\n' "$3" > "$state" ;;
    unlink) rm "$state" ;;
    *) exit 1 ;;
esac
""");herdr.chmod(0o755)
            env={**os.environ,'HOME':str(home),'PATH':str(bin)+':'+os.environ['PATH']}
            command=home/'.local/bin/left-undone'
            for _ in range(2):
                result=subprocess.run([sys.executable,str(project/'install.py')],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertTrue(command.is_symlink())
                result=subprocess.run([str(command),'--help'],env=env,cwd=home,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('--repo',result.stdout)
            skill=home/'.agents/skills/left-undone-herdr'
            claude_skill=home/'.claude/skills/left-undone-herdr'
            state=home/'.local/state/left-undone-herdr'
            state.mkdir(parents=True)
            data=state/'state.db';data.write_text('persisted tasks')
            skill.unlink();skill.symlink_to(home/'unrelated-skill')
            for _ in range(2):
                result=subprocess.run([sys.executable,str(project/'uninstall.py')],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertFalse(command.is_symlink())
                self.assertFalse(claude_skill.is_symlink())
                self.assertTrue(skill.is_symlink())
                self.assertFalse((home/'plugin-root').exists())
                self.assertEqual(data.read_text(),'persisted tasks')
            skill.unlink()
            (home/'plugin-root').write_text(str(home/'other-checkout'))
            for script in ('install.py','uninstall.py'):
                result=subprocess.run([sys.executable,str(project/script)],env=env,capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual((home/'plugin-root').read_text(),str(home/'other-checkout'))
            (home/'plugin-root').unlink()
            command.write_text('unrelated command')
            result=subprocess.run([sys.executable,str(project/'install.py')],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(command.read_text(),'unrelated command')
