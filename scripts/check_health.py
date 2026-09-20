"""Launch real Streamlit, assert loopback HTTP health, then shut it down."""
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

project = Path(__file__).resolve().parents[1]
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 0))
    port = probe.getsockname()[1]
url = f'http://127.0.0.1:{port}/_stcore/health'
with tempfile.TemporaryFile(mode='w+') as log:
    proc = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'app.py', '--server.address', '127.0.0.1', '--server.port', str(port), '--server.headless', 'true'], cwd=project, stdout=log, stderr=log)
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                log.seek(0)
                raise RuntimeError(log.read())
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    body = response.read().decode()
                    assert response.status == 200 and body == 'ok'
                    print(f'PASS {url} HTTP {response.status} {body}')
                    break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError('Streamlit health endpoint did not become ready')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print('Streamlit test server stopped')
