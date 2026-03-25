---
name: claude-code-reference
description: >
  Authoritative reference for Claude Code settings.json schema, CLI flags,
  permission system, and hook configuration. Use when editing settings.json,
  writing permission rules, configuring hooks, or generating CLI commands.
  Sourced from official documentation at code.claude.com (March 2026).
---

# Claude Code Reference

Structured reference for Claude Code configuration. Use this to look up
exact field names, types, and semantics instead of guessing from training
data.

**Source**: Official documentation at code.claude.com, fetched March 2026.
As the CLI evolves, re-fetch from the URLs below to update sections that
may have changed.

---

## 1. Settings Schema

**Source**: https://code.claude.com/docs/en/settings

**JSON Schema**: `https://json.schemastore.org/claude-code-settings.json`
(add `"$schema"` to your settings.json for editor autocomplete).

### Configuration scopes

| Scope       | Location                                                        | Who it affects             | Shared? |
|:------------|:----------------------------------------------------------------|:---------------------------|:--------|
| **Managed** | Server-managed, plist/registry, or `managed-settings.json`      | All users on machine       | Yes (IT)|
| **User**    | `~/.claude/settings.json`                                       | You, all projects          | No      |
| **Project** | `.claude/settings.json`                                         | All repo collaborators     | Yes     |
| **Local**   | `.claude/settings.local.json`                                   | You, this repo only        | No      |

**Precedence** (highest to lowest):
1. Managed (cannot be overridden)
2. Command-line arguments
3. Local project settings
4. Shared project settings
5. User settings

**Array settings merge**: When the same array setting appears in multiple
scopes, arrays are concatenated and deduplicated, not replaced.

### Feature locations by scope

| Feature       | User                      | Project                            | Local                          |
|:--------------|:--------------------------|:-----------------------------------|:-------------------------------|
| Settings      | `~/.claude/settings.json` | `.claude/settings.json`            | `.claude/settings.local.json`  |
| Subagents     | `~/.claude/agents/`       | `.claude/agents/`                  | None                           |
| MCP servers   | `~/.claude.json`          | `.mcp.json`                        | `~/.claude.json` (per-project) |
| Plugins       | `~/.claude/settings.json` | `.claude/settings.json`            | `.claude/settings.local.json`  |
| CLAUDE.md     | `~/.claude/CLAUDE.md`     | `CLAUDE.md` or `.claude/CLAUDE.md` | None                           |

### Managed settings delivery

- **Server-managed**: Via Claude.ai admin console
- **macOS MDM**: `com.anthropic.claudecode` managed preferences domain
- **Windows GPO**: `HKLM\SOFTWARE\Policies\ClaudeCode` registry key (`Settings` value, REG_SZ)
- **Windows user-level**: `HKCU\SOFTWARE\Policies\ClaudeCode` (lowest policy priority)
- **File-based**: `managed-settings.json` in:
  - macOS: `/Library/Application Support/ClaudeCode/`
  - Linux/WSL: `/etc/claude-code/`
  - Windows: `C:\Program Files\ClaudeCode\`

### All settings.json fields

| Key | Type | Description |
|:----|:-----|:------------|
| `$schema` | string | JSON Schema URL for editor validation |
| `permissions` | object | Permission rules. See [Permission System](#3-permission-system) |
| `hooks` | object | Hook configuration. See [Hook Configuration](#4-hook-configuration) |
| `env` | object | Environment variables applied to every session |
| `model` | string | Override default model (e.g., `"claude-sonnet-4-6"`) |
| `availableModels` | string[] | Restrict model selection via `/model`, `--model`, Config tool |
| `modelOverrides` | object | Map Anthropic model IDs to provider-specific IDs (e.g., Bedrock ARNs) |
| `effortLevel` | `"low"` \| `"medium"` \| `"high"` | Persist effort level across sessions |
| `agent` | string | Run main thread as a named subagent |
| `attribution` | object | Customize git commit/PR attribution. Keys: `commit`, `pr` (strings) |
| `includeCoAuthoredBy` | boolean | **Deprecated** — use `attribution` instead |
| `includeGitInstructions` | boolean | Include built-in git workflow instructions in system prompt (default: `true`) |
| `autoMode` | object | Configure auto mode classifier. Keys: `environment`, `allow`, `soft_deny` (string arrays). Not read from shared project settings |
| `disableAutoMode` | `"disable"` | Prevent auto mode activation |
| `disableAllHooks` | boolean | Disable all hooks and custom status line |
| `allowManagedHooksOnly` | boolean | (Managed only) Block user/project/plugin hooks |
| `allowedHttpHookUrls` | string[] | URL patterns for HTTP hooks. Supports `*` wildcard. Merges across scopes |
| `httpHookAllowedEnvVars` | string[] | Env var names HTTP hooks may interpolate into headers. Merges across scopes |
| `allowManagedPermissionRulesOnly` | boolean | (Managed only) Block user/project permission rules |
| `allowManagedMcpServersOnly` | boolean | (Managed only) Only managed `allowedMcpServers` apply |
| `allowedMcpServers` | object[] | (Managed) MCP server allowlist. Format: `[{"serverName": "..."}]` |
| `deniedMcpServers` | object[] | (Managed) MCP server denylist. Merges from all scopes |
| `enableAllProjectMcpServers` | boolean | Auto-approve all MCP servers in project `.mcp.json` |
| `enabledMcpjsonServers` | string[] | Specific `.mcp.json` servers to approve |
| `disabledMcpjsonServers` | string[] | Specific `.mcp.json` servers to reject |
| `strictKnownMarketplaces` | object[] | (Managed) Plugin marketplace allowlist |
| `blockedMarketplaces` | object[] | (Managed) Marketplace blocklist |
| `pluginTrustMessage` | string | (Managed) Custom message appended to plugin trust warning |
| `statusLine` | object | Custom status line. Format: `{"type": "command", "command": "..."}` |
| `fileSuggestion` | object | Custom `@` file autocomplete. Format: `{"type": "command", "command": "..."}` |
| `respectGitignore` | boolean | Whether `@` picker respects `.gitignore` (default: `true`) |
| `outputStyle` | string | Adjust system prompt output style (e.g., `"Explanatory"`) |
| `language` | string | Preferred response language (e.g., `"japanese"`) |
| `voiceEnabled` | boolean | Enable push-to-talk voice dictation |
| `autoUpdatesChannel` | `"stable"` \| `"latest"` | Release channel for updates (default: `"latest"`) |
| `plansDirectory` | string | Custom plan file storage path (default: `~/.claude/plans`) |
| `showClearContextOnPlanAccept` | boolean | Show "clear context" on plan accept screen |
| `alwaysThinkingEnabled` | boolean | Enable extended thinking by default |
| `forceLoginMethod` | `"claudeai"` \| `"console"` | Restrict login method |
| `forceLoginOrgUUID` | string | Auto-select org during login (requires `forceLoginMethod`) |
| `channelsEnabled` | boolean | (Managed) Allow channels for Team/Enterprise |
| `apiKeyHelper` | string | Script to generate auth value for API requests |
| `otelHeadersHelper` | string | Script to generate OpenTelemetry headers |
| `awsAuthRefresh` | string | Script to refresh AWS credentials |
| `awsCredentialExport` | string | Script to export AWS credentials as JSON |
| `autoMemoryDirectory` | string | Custom auto memory directory. Not allowed in project settings |
| `cleanupPeriodDays` | number | Session retention period (default: 30). `0` disables persistence |
| `companyAnnouncements` | string[] | (Managed) Startup announcements, cycled randomly |
| `spinnerVerbs` | object | Custom spinner verbs. Keys: `mode` (`"replace"` \| `"append"`), `verbs` (string[]) |
| `spinnerTipsEnabled` | boolean | Show spinner tips (default: `true`) |
| `spinnerTipsOverride` | object | Custom spinner tips. Keys: `excludeDefault` (boolean), `tips` (string[]) |
| `prefersReducedMotion` | boolean | Reduce UI animations for accessibility |
| `fastModePerSessionOptIn` | boolean | Require per-session `/fast` opt-in |
| `teammateMode` | `"auto"` \| `"in-process"` \| `"tmux"` | Agent team display mode |
| `feedbackSurveyRate` | number | Survey probability (0-1). `0` suppresses entirely |

### Sandbox settings

Nested under `"sandbox"` in settings.json:

| Key | Type | Description |
|:----|:-----|:------------|
| `enabled` | boolean | Enable bash sandboxing (default: `false`) |
| `autoAllowBashIfSandboxed` | boolean | Auto-approve bash when sandboxed (default: `true`) |
| `excludedCommands` | string[] | Commands that run outside sandbox |
| `allowUnsandboxedCommands` | boolean | Allow `dangerouslyDisableSandbox` escape hatch (default: `true`) |
| `filesystem.allowWrite` | string[] | Additional writable paths. Merges across scopes |
| `filesystem.denyWrite` | string[] | Non-writable paths. Merges across scopes |
| `filesystem.denyRead` | string[] | Non-readable paths. Merges across scopes |
| `filesystem.allowRead` | string[] | Re-allow reading within `denyRead` regions. Merges across scopes |
| `filesystem.allowManagedReadPathsOnly` | boolean | (Managed only) Ignore non-managed `allowRead` |
| `network.allowedDomains` | string[] | Allowed outbound domains. Supports `*.example.com` |
| `network.allowManagedDomainsOnly` | boolean | (Managed only) Ignore non-managed domains |
| `network.allowUnixSockets` | string[] | Allowed Unix socket paths |
| `network.allowAllUnixSockets` | boolean | Allow all Unix sockets (default: `false`) |
| `network.allowLocalBinding` | boolean | Allow localhost binding (macOS only, default: `false`) |
| `network.httpProxyPort` | number | Custom HTTP proxy port |
| `network.socksProxyPort` | number | Custom SOCKS5 proxy port |
| `enableWeakerNestedSandbox` | boolean | Weaker sandbox for Docker (Linux/WSL2, default: `false`) |
| `enableWeakerNetworkIsolation` | boolean | Allow TLS trust service access (macOS, default: `false`) |

**Sandbox path prefixes**:

| Prefix | Meaning |
|:-------|:--------|
| `/` | Absolute path from filesystem root |
| `~/` | Relative to home directory |
| `./` or bare | Relative to project root (project settings) or `~/.claude` (user settings) |

### Worktree settings

| Key | Type | Description |
|:----|:-----|:------------|
| `worktree.symlinkDirectories` | string[] | Directories to symlink into worktrees |
| `worktree.sparsePaths` | string[] | Sparse-checkout paths for worktrees |

### Global config settings (~/.claude.json)

These live in `~/.claude.json`, NOT `settings.json`:

| Key | Type | Description |
|:----|:-----|:------------|
| `autoConnectIde` | boolean | Auto-connect to running IDE from external terminal |
| `autoInstallIdeExtension` | boolean | Auto-install IDE extension in VS Code (default: `true`) |
| `editorMode` | `"normal"` \| `"vim"` | Input key binding mode |
| `showTurnDuration` | boolean | Show turn duration messages (default: `true`) |
| `terminalProgressBarEnabled` | boolean | Terminal progress bar in supported terminals (default: `true`) |

---

## 2. CLI Reference

**Source**: https://code.claude.com/docs/en/cli-reference

### Commands

| Command | Description |
|:--------|:------------|
| `claude` | Start interactive session |
| `claude "query"` | Start session with initial prompt |
| `claude -p "query"` | Print mode (non-interactive), then exit |
| `cat file \| claude -p "query"` | Process piped content |
| `claude -c` | Continue most recent conversation |
| `claude -c -p "query"` | Continue via SDK |
| `claude -r "<session>" "query"` | Resume session by ID or name |
| `claude update` | Update to latest version |
| `claude auth login` | Sign in. Flags: `--email`, `--sso`, `--console` |
| `claude auth logout` | Log out |
| `claude auth status` | Show auth status as JSON. `--text` for human-readable |
| `claude agents` | List all configured subagents |
| `claude auto-mode defaults` | Print built-in auto mode classifier rules |
| `claude auto-mode config` | Show effective auto mode config with settings applied |
| `claude auto-mode critique` | Get AI feedback on custom auto mode rules |
| `claude mcp` | Configure MCP servers |
| `claude remote-control` | Start Remote Control server |

### Flags

| Flag | Description |
|:-----|:------------|
| `--add-dir` | Add additional working directories |
| `--agent` | Specify agent for current session |
| `--agents` | Define subagents dynamically via JSON |
| `--allowedTools` | Tools that execute without permission prompts |
| `--allow-dangerously-skip-permissions` | Enable bypass as option without activating |
| `--append-system-prompt` | Append text to default system prompt |
| `--append-system-prompt-file` | Append file contents to default prompt |
| `--bare` | Minimal mode: skip hooks, skills, plugins, MCP, CLAUDE.md |
| `--betas` | Beta headers for API requests (API key users) |
| `--channels` | MCP server channel notifications to listen for |
| `--chrome` | Enable Chrome browser integration |
| `--continue`, `-c` | Load most recent conversation |
| `--dangerously-skip-permissions` | Skip permission prompts (use with caution) |
| `--debug` | Enable debug mode. Optional category filter: `"api,hooks"` |
| `--disable-slash-commands` | Disable all skills and commands |
| `--disallowedTools` | Tools removed from model context |
| `--effort` | Set effort level: `low`, `medium`, `high`, `max` (Opus only) |
| `--enable-auto-mode` | Unlock auto mode in Shift+Tab cycle |
| `--fallback-model` | Fallback model when default is overloaded (print mode) |
| `--fork-session` | Create new session ID when resuming |
| `--from-pr` | Resume sessions linked to a GitHub PR |
| `--ide` | Auto-connect to IDE on startup |
| `--init` | Run initialization hooks then start interactive |
| `--init-only` | Run initialization hooks then exit |
| `--include-partial-messages` | Include partial streaming events |
| `--input-format` | Input format for print mode: `text`, `stream-json` |
| `--json-schema` | Get validated JSON output matching schema (print mode) |
| `--maintenance` | Run maintenance hooks and exit |
| `--max-budget-usd` | Max dollar spend before stopping (print mode) |
| `--max-turns` | Limit agentic turns (print mode) |
| `--mcp-config` | Load MCP servers from JSON files/strings |
| `--model` | Set model: alias (`sonnet`, `opus`) or full name |
| `--name`, `-n` | Set session display name |
| `--no-chrome` | Disable Chrome integration |
| `--no-session-persistence` | Don't save session to disk (print mode) |
| `--output-format` | Output format: `text`, `json`, `stream-json` |
| `--permission-mode` | Start in specified mode |
| `--permission-prompt-tool` | MCP tool for permission prompts (non-interactive) |
| `--plugin-dir` | Load plugins from directory (repeatable) |
| `--print`, `-p` | Non-interactive print mode |
| `--remote` | Create web session on claude.ai |
| `--remote-control`, `--rc` | Interactive session with Remote Control |
| `--resume`, `-r` | Resume session by ID/name, or show picker |
| `--session-id` | Use specific session UUID |
| `--setting-sources` | Comma-separated setting sources: `user,project,local` |
| `--settings` | Path to additional settings JSON file |
| `--strict-mcp-config` | Only use MCP from `--mcp-config` |
| `--system-prompt` | Replace entire system prompt |
| `--system-prompt-file` | Replace system prompt with file contents |
| `--teammate-mode` | Agent team display: `auto`, `in-process`, `tmux` |
| `--teleport` | Resume web session locally |
| `--tools` | Restrict available tools: `""`, `"default"`, `"Bash,Edit,Read"` |
| `--verbose` | Verbose logging with full turn output |
| `--version`, `-v` | Show version |
| `--worktree`, `-w` | Start in isolated git worktree |

### System prompt flag interactions

| Flag | Behavior |
|:-----|:---------|
| `--system-prompt` | Replaces entire default prompt |
| `--system-prompt-file` | Replaces with file contents |
| `--append-system-prompt` | Appends to default prompt |
| `--append-system-prompt-file` | Appends file contents |

`--system-prompt` and `--system-prompt-file` are mutually exclusive.
Append flags can combine with either replacement flag.

---

## 3. Permission System

**Source**: https://code.claude.com/docs/en/permissions

### Tool approval tiers

| Tool type | Example | Approval required | "Don't ask again" scope |
|:----------|:--------|:------------------|:------------------------|
| Read-only | File reads, Grep | No | N/A |
| Bash commands | Shell execution | Yes | Permanent per project+command |
| File modification | Edit/Write | Yes | Session only |

### Rule evaluation order

Rules evaluate: **deny -> ask -> allow**. First match wins.

Deny rules always take precedence regardless of scope.

### Permission modes

| Mode | Description |
|:-----|:------------|
| `default` | Prompts for permission on first use |
| `acceptEdits` | Auto-accepts file edit permissions for session |
| `plan` | Read-only: can analyze but not modify or execute |
| `auto` | Auto-approves with background safety classifier |
| `dontAsk` | Auto-denies unless pre-approved via allow rules |
| `bypassPermissions` | Skips prompts. Still prompts for `.git`, `.claude`, `.vscode`, `.idea` writes |

### Permission rule syntax

Format: `Tool` or `Tool(specifier)`

#### Match all uses

| Rule | Matches |
|:-----|:--------|
| `Bash` | All Bash commands |
| `Read` | All file reads |
| `WebFetch` | All web fetches |

`Bash(*)` is equivalent to `Bash`.

#### Bash patterns

| Rule | Matches |
|:-----|:--------|
| `Bash(npm run build)` | Exact command |
| `Bash(npm run test *)` | Commands starting with `npm run test` |
| `Bash(* --version)` | Commands ending with `--version` |
| `Bash(git * main)` | Commands like `git checkout main` |

**Word boundary**: `Bash(ls *)` (space before `*`) matches `ls -la` but
NOT `lsof`. `Bash(ls*)` (no space) matches both.

**Shell operators**: Claude Code is aware of `&&` — `Bash(safe-cmd *)`
won't match `safe-cmd && other-cmd`.

**Compound commands**: "Yes, don't ask again" saves separate rules per
subcommand (up to 5 per compound command).

**Limitations**: Bash patterns that constrain arguments are fragile.
Variations in flag order, protocols, variables, and extra spaces can
bypass patterns. For reliable URL filtering, use `WebFetch(domain:...)`
instead of trying to pattern-match `curl` arguments.

#### Read and Edit patterns

Follow gitignore specification with four pattern types:

| Pattern | Meaning | Example |
|:--------|:--------|:--------|
| `//path` | Absolute path from filesystem root | `Read(//Users/alice/secrets/**)` |
| `~/path` | Relative to home directory | `Read(~/Documents/*.pdf)` |
| `/path` | Relative to **project root** | `Edit(/src/**/*.ts)` |
| `path` or `./path` | Relative to **current directory** | `Read(*.env)` |

**Important**: `/Users/alice/file` is NOT absolute — it's project-relative.
Use `//Users/alice/file` for absolute paths.

`*` matches files in a single directory. `**` matches recursively.

Edit rules apply to all built-in file-editing tools. Read deny rules apply
to Read, Grep, and Glob (best-effort). Neither applies to Bash subprocesses
— use sandbox for OS-level enforcement.

#### WebFetch patterns

`WebFetch(domain:example.com)` — matches fetch requests to domain.

#### MCP patterns

| Rule | Matches |
|:-----|:--------|
| `mcp__puppeteer` | Any tool from puppeteer server |
| `mcp__puppeteer__*` | Same (wildcard syntax) |
| `mcp__puppeteer__puppeteer_navigate` | Specific tool |

#### Agent patterns

| Rule | Matches |
|:-----|:--------|
| `Agent(Explore)` | Explore subagent |
| `Agent(Plan)` | Plan subagent |
| `Agent(my-custom-agent)` | Custom subagent |

### Permissions + sandbox interaction

- **Permissions** control which tools Claude can use and which files/domains
  it can access. Apply to all tools.
- **Sandboxing** provides OS-level enforcement restricting Bash filesystem
  and network access. Applies only to Bash commands.
- Permission deny rules prevent Claude from attempting access. Sandbox
  restrictions prevent Bash from reaching resources even if prompt injection
  bypasses Claude's decision-making.

### Auto mode classifier configuration

Configured via `autoMode` in settings.json. Not read from shared project
settings (`.claude/settings.json`).

| Field | Type | Description |
|:------|:-----|:------------|
| `environment` | string[] | Prose descriptions of trusted infrastructure |
| `allow` | string[] | Exception rules (overrides `soft_deny`) |
| `soft_deny` | string[] | Block rules |

**Precedence**: `soft_deny` blocks first, `allow` overrides as exceptions,
explicit user intent overrides both.

**Warning**: Setting `allow` or `soft_deny` **replaces the entire default
list**. Always start from `claude auto-mode defaults` output.

---

## 4. Hook Configuration

**Source**: https://code.claude.com/docs/en/hooks

### Hook events (lifecycle order)

| # | Event | When | Matcher filters on | Blockable |
|:--|:------|:-----|:-------------------|:----------|
| 1 | `SessionStart` | Session begins/resumes | `startup`, `resume`, `clear`, `compact` | No |
| 2 | `InstructionsLoaded` | CLAUDE.md / rules loaded | `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact` | No |
| 3 | `UserPromptSubmit` | User submits prompt | None (always fires) | Yes |
| 4 | `PreToolUse` | Before tool execution | Tool name | Yes |
| 5 | `PermissionRequest` | Permission dialog | Tool name | Yes |
| 6 | `PostToolUse` | After successful tool | Tool name | No (advisory) |
| 7 | `PostToolUseFailure` | After tool failure | Tool name | No (advisory) |
| 8 | `Notification` | Notification sent | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog` | No |
| 9 | `SubagentStart` | Subagent spawned | Agent type | No |
| 10 | `SubagentStop` | Subagent finishes | Agent type | Yes |
| 11 | `Stop` | Main agent done | None (always fires) | Yes |
| 12 | `StopFailure` | API error | `rate_limit`, `authentication_failed`, `billing_error`, `invalid_request`, `server_error`, `max_output_tokens`, `unknown` | No |
| 13 | `TeammateIdle` | Teammate going idle | None (always fires) | Yes (exit 2) |
| 14 | `TaskCompleted` | Task marked complete | None (always fires) | Yes (exit 2) |
| 15 | `ConfigChange` | Config file changes | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills` | Yes (except policy) |
| 16 | `WorktreeCreate` | Worktree created | None (always fires) | Yes |
| 17 | `WorktreeRemove` | Worktree removed | None (always fires) | No |
| 18 | `PreCompact` | Before compaction | `manual`, `auto` | No |
| 19 | `PostCompact` | After compaction | `manual`, `auto` | No |
| 20 | `Elicitation` | MCP requests input | MCP server name | Yes |
| 21 | `ElicitationResult` | User responds to MCP | MCP server name | Yes |
| 22 | `SessionEnd` | Session terminates | `clear`, `resume`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` | No |

### Configuration schema

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "regex_pattern",
        "hooks": [
          {
            "type": "command",
            "command": "path/to/script.sh",
            "timeout": 600,
            "statusMessage": "Running hook...",
            "once": false,
            "async": false
          }
        ]
      }
    ]
  }
}
```

### Hook types

**Command** (most common):

| Field | Required | Type | Description |
|:------|:---------|:-----|:------------|
| `type` | yes | `"command"` | |
| `command` | yes | string | Shell command to execute |
| `timeout` | no | number | Seconds (default: 600) |
| `async` | no | boolean | Run in background without blocking |

**HTTP**:

| Field | Required | Type | Description |
|:------|:---------|:-----|:------------|
| `type` | yes | `"http"` | |
| `url` | yes | string | POST endpoint |
| `headers` | no | object | HTTP headers; supports `$VAR_NAME` interpolation |
| `allowedEnvVars` | no | string[] | Env vars allowed in header values |
| `timeout` | no | number | Seconds (default: 600) |

**Prompt**:

| Field | Required | Type | Description |
|:------|:---------|:-----|:------------|
| `type` | yes | `"prompt"` | |
| `prompt` | yes | string | Prompt text; `$ARGUMENTS` placeholder for JSON input |
| `model` | no | string | Model to use (default: fast model) |
| `timeout` | no | number | Seconds (default: 30) |

**Agent**:

| Field | Required | Type | Description |
|:------|:---------|:-----|:------------|
| `type` | yes | `"agent"` | |
| `prompt` | yes | string | Task prompt; `$ARGUMENTS` for JSON input |
| `timeout` | no | number | Seconds (default: 60) |

### Common fields (all types)

| Field | Required | Default | Description |
|:------|:---------|:--------|:------------|
| `type` | yes | — | `"command"`, `"http"`, `"prompt"`, or `"agent"` |
| `timeout` | no | varies | Seconds before canceling |
| `statusMessage` | no | — | Custom spinner message |
| `once` | no | `false` | Skills only: run once per session |

### Common input fields (all events)

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "default",
  "hook_event_name": "EventName",
  "agent_id": "subagent-id-if-in-subagent",
  "agent_type": "agent-name-if-in-subagent"
}
```

### Exit code behavior

| Exit code | Behavior |
|:----------|:---------|
| **0** | Success. JSON output processed. Stdout shown in verbose mode (except `UserPromptSubmit` and `SessionStart` where stdout is added as context) |
| **2** | Blocking error. Stderr shown to Claude/user. Blocks tool calls, denies permissions, etc. |
| **other** | Non-blocking error. Stderr shown in verbose mode. Execution continues |

### JSON output schema (all events)

```json
{
  "continue": true,
  "stopReason": "Message when continue is false",
  "suppressOutput": false,
  "systemMessage": "Warning to user",
  "decision": "block",
  "reason": "Explanation",
  "hookSpecificOutput": {
    "hookEventName": "EventName",
    "additionalContext": "Context for Claude"
  }
}
```

| Field | Default | Description |
|:------|:--------|:------------|
| `continue` | `true` | If `false`, stops Claude entirely (overrides event-specific decisions) |
| `stopReason` | — | Message to user (not Claude) when stopping |
| `suppressOutput` | `false` | Hide stdout from verbose mode |
| `systemMessage` | — | Warning shown to user |

### PreToolUse output (permission control)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "explanation",
    "updatedInput": {"field": "new_value"},
    "additionalContext": "context for Claude"
  }
}
```

**Note**: A hook `"allow"` does not bypass permission rules. Deny and ask
rules still evaluate after `allow`. A hook exit code 2 blocks before
permission rules are checked.

### Tool input schemas (PreToolUse)

**Bash**: `{"command": "...", "description": "...", "timeout": 120000, "run_in_background": false}`

**Write**: `{"file_path": "/abs/path", "content": "..."}`

**Edit**: `{"file_path": "/abs/path", "old_string": "...", "new_string": "...", "replace_all": false}`

**Read**: `{"file_path": "/abs/path", "offset": 10, "limit": 50}`

**Glob**: `{"pattern": "**/*.ts", "path": "/optional/dir"}`

**Grep**: `{"pattern": "regex", "path": "/optional/dir", "glob": "*.ts", "output_mode": "content|files_with_matches|count", "-i": true, "multiline": false}`

**WebFetch**: `{"url": "https://...", "prompt": "..."}`

**WebSearch**: `{"query": "...", "allowed_domains": [...], "blocked_domains": [...]}`

**Agent**: `{"prompt": "...", "description": "...", "subagent_type": "...", "model": "..."}`

### Special environment variables

| Variable | Scope | Description |
|:---------|:------|:------------|
| `CLAUDE_ENV_FILE` | SessionStart only | Path to persist env vars for Bash commands |
| `CLAUDE_CODE_REMOTE` | All hooks | `"true"` in web environments |
| `CLAUDE_PROJECT_DIR` | All hooks | Project root directory |
| `CLAUDE_PLUGIN_ROOT` | Plugin hooks | Plugin installation directory |
| `CLAUDE_PLUGIN_DATA` | Plugin hooks | Persistent data directory across updates |

### Hook deduplication

Identical hooks run once. Deduped by command string (command hooks) or
URL (HTTP hooks).

### Hook scope locations

| Location | Scope |
|:---------|:------|
| `~/.claude/settings.json` | All projects |
| `.claude/settings.json` | Single project (shareable) |
| `.claude/settings.local.json` | Single project (private) |
| Managed policy settings | Organization-wide |
| Plugin `hooks/hooks.json` | When plugin enabled |
| Skill/agent frontmatter | While component active |
