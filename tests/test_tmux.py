import itertools
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette

REPO = Path(__file__).resolve().parents[1]
PALETTE = load_palette()
C = PALETTE.colors
_ids = itertools.count()
pytestmark_tmux = pytest.mark.skipif(shutil.which("tmux") is None, reason="requires tmux")

EXPECTED = {
    "status-style": f"fg={C['foreground']},bg={C['surface']}",
    "status-left-style": f"fg={C['background']},bg={C['blue']},bold",
    "status-right-style": f"fg={C['muted']},bg={C['surface']}",
    "window-status-style": f"fg={C['muted']},bg={C['surface']}",
    "window-status-current-style": f"fg={C['foreground']},bg={C['overlay']},bold",
    "window-status-activity-style": f"fg={C['yellow']},bg={C['surface']}",
    "window-status-bell-style": f"fg={C['red']},bg={C['surface']},bold",
    "pane-border-style": f"fg={C['overlay']}",
    "pane-active-border-style": f"fg={C['blue']}",
    "message-style": f"fg={C['foreground']},bg={C['overlay']}",
    "message-command-style": f"fg={C['yellow']},bg={C['overlay']}",
    "mode-style": f"fg={C['foreground']},bg={C['selection']}",
    "copy-mode-match-style": f"bg={C['selection']}",
    "copy-mode-current-match-style": f"fg={C['gold']},bg={C['selection']},bold",
    "clock-mode-colour": C["blue"],
    "display-panes-colour": C["muted"],
    "display-panes-active-colour": C["blue"],
    "popup-border-style": f"fg={C['blue']}",
    "menu-border-style": f"fg={C['blue']}",
}


def tmux(socket, *args):
    return subprocess.run(["tmux", "-L", socket, *args], capture_output=True, text=True)


def options_after(*load):
    socket = f"deepwick-test-{os.getpid()}-{next(_ids)}"
    try:
        assert tmux(socket, "-f", "/dev/null", "new-session", "-d").returncode == 0
        defaults = {name: tmux(socket, "show-options", "-gv", "status-left").stdout for name in ["status-left"]}
        for command in load:
            result = tmux(socket, *command)
            assert result.returncode == 0 and result.stderr == "", result.stderr
        values = {name: tmux(socket, "show-options", "-gv", name).stdout.strip() for name in EXPECTED}
        values["__status-left__"] = tmux(socket, "show-options", "-gv", "status-left").stdout
        values["__default-status-left__"] = defaults["status-left"]
        return values
    finally:
        tmux(socket, "kill-server")


@pytestmark_tmux
def test_source_file_sets_every_style():
    values = options_after(("source-file", str(REPO / "deepwick.conf")))
    for name, expected in EXPECTED.items():
        assert values[name].lower() == expected.lower(), name


@pytestmark_tmux
def test_tpm_entry_point_matches_source_file():
    via_tpm = options_after(("run-shell", str(REPO / "deepwick.tmux")))
    via_source = options_after(("source-file", str(REPO / "deepwick.conf")))
    assert via_tpm == via_source


@pytestmark_tmux
def test_does_not_replace_status_contents():
    values = options_after(("source-file", str(REPO / "deepwick.conf")))
    assert values["__status-left__"] == values["__default-status-left__"]


def test_tpm_entry_point_is_executable():
    assert os.access(REPO / "deepwick.tmux", os.X_OK)


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []
