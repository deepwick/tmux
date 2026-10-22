# Deepwick for tmux

Deepwick colors for tmux: status bar, windows, pane borders, messages, copy
mode, popups, and menus. By default only styles are set, so your status bar
contents stay as they are; an optional status layout is included.

> Deepwick is an unofficial theme derived from
> [Polywick Blue](https://vscode.polywickstudio.net) by Polywick Studio (MIT).
> Not affiliated with Polywick Studio.

![Deepwick in tmux](screenshot.png)

## Install

With [TPM](https://github.com/tmux-plugins/tpm), add to `~/.tmux.conf`:

```tmux
set -g @plugin 'deepwick/tmux'
```

and press `prefix` + `I`. Without TPM:

```tmux
source-file /path/to/deepwick.conf
```

For true colors, make sure your terminal is advertised as RGB-capable, for
example `set -as terminal-features ',xterm-256color:RGB'`.

## Status layout (optional)

A powerline status layout in Deepwick colors, like nord-tmux's: the session
name on Blue, window tabs on Overlay with the current one on Teal, and the
date, time and host name on the right.

With TPM, set this before the `run '~/.tmux/plugins/tpm/tpm'` line:

```tmux
set -g @deepwick_status 'powerline'
```

Without TPM, source the layout after `deepwick.conf`:

```tmux
source-file /path/to/deepwick.conf
source-file /path/to/deepwick-status.conf
```

The powerline layout needs a [Nerd Font](https://www.nerdfonts.com) or a
powerline-patched font. Without one, use `plain` (or
`deepwick-status-plain.conf`): the same layout with spaces and `|` instead
of the arrow glyphs.

Either layout replaces `status-left`, `status-right`, the window formats,
`window-status-separator`, `status-justify` and `status-right-length`. As
with the styles alone, an inactive tab turns Yellow on activity (with
`monitor-activity on`) and bold Red on a bell. To
change the date or time format, set your own `status-right` after the theme
loads, starting from the one in `deepwick-status.conf`. Both layout files are
generated: run `PYTHONPATH=../spec python3 generate.py` with a
[deepwick spec](https://github.com/deepwick/spec) checkout next to this repo.

Tested with tmux 3.7c.

## License

MIT. See [LICENSE](LICENSE).
