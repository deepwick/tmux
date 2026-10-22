#!/usr/bin/env bash
# TPM entry point: load the Deepwick styles, plus the status layout named by @deepwick_status.
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmux source-file "$dir/deepwick.conf"
case "$(tmux show-options -gqv @deepwick_status)" in
  powerline) tmux source-file "$dir/deepwick-status.conf" ;;
  plain) tmux source-file "$dir/deepwick-status-plain.conf" ;;
esac
