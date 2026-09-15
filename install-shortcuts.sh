#!/usr/bin/env bash
# Installs HyprFetch's short subcommands (hyprgui, hyprtui, hyprbench,
# hyprgpu, hyprself, hyprdiag, hyprjson) as symlinks into ~/.local/bin,
# so you can run `hyprgui` from anywhere instead of `./hyprfetch.sh --gui`.
#
# Usage: ./install-shortcuts.sh [--uninstall]

set -e

SELF="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SELF")" && pwd)"
BIN_DIR="$ROOT/bin"
TARGET_DIR="${HYPRFETCH_BIN_DIR:-$HOME/.local/bin}"

if [[ "$1" == "--uninstall" ]]; then
    for f in "$BIN_DIR"/*; do
        name="$(basename "$f")"
        if [[ -L "$TARGET_DIR/$name" ]]; then
            rm -f "$TARGET_DIR/$name"
            echo "Removed $TARGET_DIR/$name"
        fi
    done
    exit 0
fi

if [[ ! -d "$BIN_DIR" ]]; then
    echo "Error: $BIN_DIR not found. Run this from the HyprFetch project root." >&2
    exit 1
fi

mkdir -p "$TARGET_DIR"

for f in "$BIN_DIR"/*; do
    name="$(basename "$f")"
    ln -sf "$f" "$TARGET_DIR/$name"
    echo "Linked $TARGET_DIR/$name -> $f"
done

echo
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo "WARNING: $TARGET_DIR is not on your PATH."
    SHELL_NAME="$(basename "${SHELL:-bash}")"
    if [[ "$SHELL_NAME" == "fish" ]]; then
        echo "You're using fish. Run this once to persist it:"
        echo "  fish_add_path $TARGET_DIR"
        echo "Then open a new terminal (or run: exec fish)."
    else
        echo "Add this to your shell config (e.g. ~/.bashrc or ~/.zshrc):"
        echo "  export PATH=\"$TARGET_DIR:\$PATH\""
        echo "Then open a new terminal (or: source ~/.bashrc)."
    fi
else
    echo "Done. Try: hyprgui | hyprtui | hyprbench | hyprgpu | hyprself | hyprdiag | hyprjson"
    echo "(If your shell still says 'unknown command', open a new terminal so it re-scans PATH.)"
fi
