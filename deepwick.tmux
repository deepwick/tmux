#!/usr/bin/env bash
# TPM entry point: load the Deepwick styles.
tmux source-file "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deepwick.conf"
