import contextlib
import itertools
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
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


CONTENT_OPTIONS = {
    "status": "-gv", "status-interval": "-gv", "status-justify": "-gv", "status-position": "-gv",
    "status-left": "-gv", "status-right": "-gv", "status-left-length": "-gv", "status-right-length": "-gv",
    "window-status-format": "-gwv", "window-status-current-format": "-gwv", "window-status-separator": "-gwv",
    "pane-border-format": "-gwv", "pane-border-status": "-gwv",
}


def content(socket):
    return {name: tmux(socket, "show-options", flags, name).stdout for name, flags in CONTENT_OPTIONS.items()}


@contextlib.contextmanager
def server():
    socket = f"deepwick-test-{os.getpid()}-{next(_ids)}"
    try:
        assert tmux(socket, "-f", "/dev/null", "new-session", "-d").returncode == 0
        yield socket
    finally:
        tmux(socket, "kill-server")
        # tmux never unlinks its socket on exit.
        (Path(os.environ.get("TMUX_TMPDIR") or "/tmp") / f"tmux-{os.getuid()}" / socket).unlink(missing_ok=True)


def options_after(*load):
    with server() as socket:
        defaults = content(socket)
        for command in load:
            result = tmux(socket, *command)
            assert result.returncode == 0 and result.stderr == "", result.stderr
        values = {name: tmux(socket, "show-options", "-gv", name).stdout.strip() for name in EXPECTED}
        values["__content__"] = content(socket)
        values["__default-content__"] = defaults
        return values


@pytestmark_tmux
def test_source_file_sets_every_style():
    values = options_after(("source-file", str(REPO / "deepwick.conf")))
    for name, expected in EXPECTED.items():
        assert values[name].lower() == expected.lower(), name


@pytestmark_tmux
def test_styles_survive_format_expansion():
    # tmux 3.6+ selection and position styles default to #{E:mode-style}, and #D/#F are format aliases.
    with server() as socket:
        tmux(socket, "source-file", str(REPO / "deepwick.conf"))
        for name in EXPECTED:
            raw = tmux(socket, "show-options", "-gv", name).stdout.strip()
            assert tmux(socket, "display-message", "-p", f"#{{E:{name}}}").stdout.strip() == raw, name


@pytestmark_tmux
def test_tpm_entry_point_matches_source_file():
    via_tpm = options_after(("run-shell", str(REPO / "deepwick.tmux")))
    via_source = options_after(("source-file", str(REPO / "deepwick.conf")))
    assert via_tpm == via_source


@pytestmark_tmux
def test_does_not_replace_status_contents():
    values = options_after(("source-file", str(REPO / "deepwick.conf")))
    assert values["__content__"] == values["__default-content__"]


def test_tpm_entry_point_is_executable():
    assert os.access(REPO / "deepwick.tmux", os.X_OK)


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []


LAYOUTS = {"powerline": "deepwick-status.conf", "plain": "deepwick-status-plain.conf"}
FORMATS = ("status-left", "status-right", "window-status-format", "window-status-current-format")
POWERLINE_GLYPHS = {"\ue0b0", "\ue0b1", "\ue0b2", "\ue0b3"}
STYLE = re.compile(r"#\[([^\]]*)\]")


def themed(layout):
    return options_after(("source-file", str(REPO / "deepwick.conf")), ("source-file", str(REPO / LAYOUTS[layout])))


def expand(socket, name, target=":0"):
    return tmux(socket, "display-message", "-p", "-t", target, f"#{{T:{name}}}").stdout.rstrip("\n")


def formats(layout):
    """Each format as tmux renders it for window 0, the current window, with no alerts."""
    with server() as socket:
        tmux(socket, "source-file", str(REPO / "deepwick.conf"))
        tmux(socket, "source-file", str(REPO / LAYOUTS[layout]))
        return {name: expand(socket, name) for name in FORMATS}


def label_style(rendered, index):
    return next(style_dict(style) for style, text in segments(rendered) if text.startswith(f"{index} "))


def segments(value):
    """(style, text) pairs: each #[...] block and the literal text up to the next one."""
    parts = STYLE.split(value)
    return list(zip(parts[1::2], parts[2::2]))


def style_dict(style):
    return dict(item.partition("=")[::2] for item in style.split(","))


@pytest.mark.parametrize("layout", LAYOUTS)
def test_committed_layout_matches_generator(layout):
    import generate
    assert (REPO / LAYOUTS[layout]).read_text(encoding="utf-8") == generate.render(PALETTE, layout)


@pytestmark_tmux
@pytest.mark.parametrize("layout", LAYOUTS)
def test_layout_replaces_status_contents(layout):
    values = themed(layout)
    content, defaults = values["__content__"], values["__default-content__"]
    for name in FORMATS:
        assert content[name] != defaults[name], name
    assert content["window-status-separator"] == "\n"
    assert content["status-justify"] == "left\n"
    # Room for the date, time and a fully qualified host name.
    assert content["status-right-length"] == "60\n"


@pytestmark_tmux
@pytest.mark.parametrize("layout", LAYOUTS)
def test_layout_keeps_deepwick_styles(layout):
    values = themed(layout)
    for name, expected in EXPECTED.items():
        assert values[name].lower() == expected.lower(), name


@pytestmark_tmux
@pytest.mark.parametrize("layout", LAYOUTS)
def test_layout_colors_are_palette_colors(layout):
    allowed = {value.lower() for value in C.values()}
    for name, value in formats(layout).items():
        styles = [style_dict(style) for style, _ in segments(value)]
        assert styles, name
        for style in styles:
            assert style["fg"] in allowed and style["bg"] in allowed, (name, style)


@pytestmark_tmux
def test_powerline_layout_uses_powerline_separators():
    used = set()
    for name, value in formats("powerline").items():
        for style, text in segments(value):
            glyphs = {ch for ch in text if not ch.isascii()}
            assert glyphs <= POWERLINE_GLYPHS, (name, text)
            if glyphs:
                # Glyphs mustn't pick up bold from the *-style options.
                assert {"nobold", "noitalics", "nounderscore"} <= set(style.split(",")), (name, style)
            used |= glyphs
    assert used == POWERLINE_GLYPHS


@pytestmark_tmux
def test_plain_layout_needs_no_patched_font():
    for name, value in formats("plain").items():
        assert value.isascii(), name


@pytestmark_tmux
@pytest.mark.parametrize("layout", LAYOUTS)
def test_tab_colors(layout):
    values = formats(layout)
    assert label_style(values["window-status-format"], 0) == {"fg": C["muted"].lower(), "bg": C["overlay"].lower()}
    assert label_style(values["window-status-current-format"], 0) == {
        "fg": C["background"].lower(), "bg": C["teal"].lower()}


@pytestmark_tmux
@pytest.mark.parametrize("layout", LAYOUTS)
def test_tpm_option_loads_layout(layout):
    via_tpm = options_after(("set-option", "-g", "@deepwick_status", layout), ("run-shell", str(REPO / "deepwick.tmux")))
    assert via_tpm == themed(layout)


@pytestmark_tmux
@pytest.mark.parametrize("value", ["", "bogus"])
def test_tpm_option_other_values_leave_contents(value):
    values = options_after(("set-option", "-g", "@deepwick_status", value), ("run-shell", str(REPO / "deepwick.tmux")))
    assert values["__content__"] == values["__default-content__"]


ALERTS = {
    "activity": ("echo hi", "window_activity_flag", {"fg": C["yellow"].lower(), "bg": C["overlay"].lower()}),
    "bell": ("printf '\\a'", "window_bell_flag", {"fg": C["red"].lower(), "bg": C["overlay"].lower(), "bold": ""}),
}


@pytestmark_tmux
@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("alert", ALERTS)
def test_inactive_tab_shows_alerts(layout, alert):
    command, flag, expected = ALERTS[alert]
    with server() as socket:
        tmux(socket, "source-file", str(REPO / "deepwick.conf"))
        tmux(socket, "source-file", str(REPO / LAYOUTS[layout]))
        tmux(socket, "set-option", "-g", "monitor-activity", "on")
        tmux(socket, "new-window", "-d", "-n", "alerting", "--", "sh", "-c", f"sleep 0.3; {command}; exec sleep 30")
        deadline = time.monotonic() + 5
        while expand(socket, f"{flag}", ":1") != "1":
            assert time.monotonic() < deadline, f"{flag} never set"
            time.sleep(0.05)
        rendered = expand(socket, "window-status-format", ":1")
        assert label_style(rendered, 1) == expected
        name_style = next(style_dict(style) for style, text in segments(rendered) if text.startswith("alerting "))
        assert name_style == expected
