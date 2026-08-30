import subprocess, sys

def run(*args):
    return subprocess.run([sys.executable, "-m", "skillock", *args],
                          capture_output=True, text=True)

def test_version():
    r = run("--version")
    assert r.returncode == 0
    assert "0.1.0" in r.stdout
