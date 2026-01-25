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
echo "This setup script creates symlinks for Claude Code CLI."
echo "For Claude Code Web, configuration in .claude/ is automatically available."
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
create_symlink "$SCRIPT_DIR/.claude/settings.json" "$CLAUDE_DIR/settings.json"
create_symlink "$SCRIPT_DIR/.claude/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
create_symlink "$SCRIPT_DIR/.claude/hooks" "$CLAUDE_DIR/hooks"
create_symlink "$SCRIPT_DIR/.claude/plugins/installed_plugins.json" "$CLAUDE_DIR/plugins/installed_plugins.json"

# Create internal symlinks from .claude/hooks to plugin hooks
echo ""
echo "Creating internal plugin hook symlinks..."
HOOKS_DIR="$SCRIPT_DIR/.claude/hooks"
PLUGIN_HOOKS_DIR="$SCRIPT_DIR/plugins/claude-code-hooks/hooks"

# Array of hook files to symlink
HOOK_FILES=(
    "normalize-line-endings.py"
    "gh-authorship-attribution.py"
    "gh-web-fallback.py"
    "prefer-modern-tools.py"
    "detect-cd-pattern.py"
    "prefer-gh-for-own-repos.py"
    "gpg-signing-helper.py"
    "detect-heredoc-errors.py"
    "gh-fallback-helper.py"
    "suggest-uv-for-missing-deps.py"
    "run-with-fallback.sh"
)

# Create symlinks for each hook file
for hook in "${HOOK_FILES[@]}"; do
    target="$HOOKS_DIR/$hook"
    # Use relative path for symlink
    source="../../plugins/claude-code-hooks/hooks/$hook"

    # Remove existing file/symlink if present
    if [[ -e "$target" ]] || [[ -L "$target" ]]; then
        if [[ "$FORCE" == "true" ]] || [[ -L "$target" ]]; then
            rm -f "$target"
            echo "Creating hook symlink: $hook"
            (cd "$HOOKS_DIR" && ln -sf "$source" "$hook")
        else
            echo "Hook file exists (not a symlink): $hook - skipping (use --force to overwrite)"
        fi
    else
        echo "Creating hook symlink: $hook"
        (cd "$HOOKS_DIR" && ln -sf "$source" "$hook")
    fi
done

# Verify symlinks
echo ""
echo "Verifying symlinks..."
ls -la "$CLAUDE_DIR" | grep -E '(settings.json|CLAUDE.md|hooks)' || true

echo ""
echo "Setup complete!"
echo ""
echo "Next steps for CLI users:"
echo "1. Restart Claude Code: /exit then 'claude'"
echo "2. Verify configuration loaded correctly"
echo "3. Test hooks are working"
echo ""
echo "For Claude Code Web users:"
echo "Configuration in .claude/ is automatically available when you use this repository."
echo "No additional setup required!"
echo ""
if [[ -d "$BACKUP_DIR" ]]; then
    echo "Backup saved at: $BACKUP_DIR"
fi
