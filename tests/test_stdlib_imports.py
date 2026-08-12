import os
import socket


def test_socket_import_comes_from_python_stdlib():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    socket_path = os.path.abspath(socket.__file__)

    try:
        common = os.path.commonpath([repo_root, socket_path])
    except ValueError:
        # Different drives (e.g. repo on D:, Python on C:) — cannot be
        # inside the repo, so the stdlib is not shadowed.
        return

    assert common != repo_root
