#!/bin/bash
# Setup script for Claude Code configuration
# Usage: ./setup.sh [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
FORCE=false

# Parse arguments
if [[ "$1" == "--force" ]]; then
    FORCE=true
fi

echo "Claude Code Configuration Setup"
echo "================================"
echo "Repository: $SCRIPT_DIR"
echo "Target: $CLAUDE_DIR"
echo ""

# Create backup
BACKUP_DIR="$HOME/.claude-backup-$(date +%Y%m%d-%H%M%S)"
if [[ -d "$CLAUDE_DIR" ]]; then
    echo "Creating backup at $BACKUP_DIR..."
    cp -R "$CLAUDE_DIR" "$BACKUP_DIR"
    echo "Backup created successfully"
fi

# Function to create symlink
create_symlink() {
    local source="$1"
    local target="$2"

    if [[ -L "$target" ]] && [[ "$FORCE" == "false" ]]; then
        echo "Symlink already exists: $target"
        echo "   Use --force to overwrite"
        return
    fi

    if [[ -e "$target" ]] || [[ -L "$target" ]]; then
        echo "Removing existing: $target"
        rm -rf "$target"
    fi

    echo "Creating symlink: $target -> $source"
    ln -s "$source" "$target"
}

# Ensure .claude directory exists
mkdir -p "$CLAUDE_DIR/plugins"

# Create symlinks
echo ""
echo "Creating symlinks..."
create_symlink "$SCRIPT_DIR/settings.json" "$CLAUDE_DIR/settings.json"
create_symlink "$SCRIPT_DIR/CLAUDE-global.md" "$CLAUDE_DIR/CLAUDE.md"
create_symlink "$SCRIPT_DIR/hooks" "$CLAUDE_DIR/hooks"
create_symlink "$SCRIPT_DIR/plugins/installed_plugins.json" "$CLAUDE_DIR/plugins/installed_plugins.json"

# Verify symlinks
echo ""
echo "Verifying symlinks..."
ls -la "$CLAUDE_DIR" | grep -E '(settings.json|CLAUDE.md|hooks)' || true

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart Claude Code: /exit then 'claude'"
echo "2. Verify configuration loaded correctly"
echo "3. Test hooks are working"
echo ""
echo "Backup saved at: $BACKUP_DIR"
