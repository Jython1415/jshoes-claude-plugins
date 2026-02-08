---
name: alfred-workflow
description: "Design, create, modify, and manage Alfred workflows programmatically. Use when the user wants to build Alfred workflows, add workflow commands, modify existing workflows, or automate Alfred. Covers the complete info.plist schema, node types, connections, scripting, and workflow lifecycle including restart-free registration."
---

# Alfred Workflow Skill

Create and manage Alfred 5 workflows entirely from the command line. This skill provides the complete reverse-engineered schema for `info.plist` workflow definitions.

**This is a living document.** It was reverse-engineered from real workflows and refined through hands-on usage. When you encounter issues creating or debugging Alfred workflows -- undocumented config keys, incorrect version numbers, edge cases in script execution, new node types -- update this skill file with what you learned. Add to the reference tables, correct inaccuracies, and expand the tips section. The goal is for this document to become more reliable with every workflow built.

## Workflow Location and Structure

**Base path**: `~/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows/`

Each workflow is a directory named `user.workflow.{UUID}` containing:

| File | Required | Purpose |
|------|----------|---------|
| `info.plist` | Yes | Workflow definition (XML property list) |
| `icon.png` | No | Workflow icon (256x256 PNG recommended) |
| `src/` | No | Convention: subdirectory for external scripts |
| `*.py`, `*.sh`, etc. | No | External script files referenced by nodes |
| `prefs.plist` | No | User preference overrides |

**Working directory:** When Alfred executes a script node, the working directory is the workflow's root directory. Relative paths in scripts (e.g., `python3 src/main.py`) resolve from there.

## Creating a New Workflow

### Step-by-step process

1. Generate a UUID for the workflow directory (use `uuidgen` command)
2. Generate UUIDs for each node in the workflow
3. Write `info.plist` with all nodes, connections, and uidata
4. Create any needed subdirectories (e.g., `mkdir -p "$WORKFLOW_DIR/src"`) and write external script files into them
5. Validate with `plutil -lint "$WORKFLOW_DIR/info.plist"`
6. Restart Alfred to register: `killall Alfred && sleep 1 && open -a "Alfred 5"`

### UUID Generation

```bash
# Generate a UUID for the workflow directory
uuidgen  # e.g., A1B2C3D4-E5F6-7890-ABCD-EF1234567890

# Generate one UUID per node
uuidgen  # repeat for each node
```

### Directory Creation

```bash
WORKFLOW_DIR="$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows/user.workflow.$(uuidgen)"
mkdir -p "$WORKFLOW_DIR"
```

## info.plist Top-Level Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>bundleid</key>
    <string>com.author.workflow-name</string>
    <key>category</key>
    <string>Productivity</string>
    <key>connections</key>
    <dict>
        <!-- Source UID -> array of destination connections -->
    </dict>
    <key>createdby</key>
    <string>Author Name</string>
    <key>description</key>
    <string>What this workflow does</string>
    <key>disabled</key>
    <false/>
    <key>name</key>
    <string>Workflow Name</string>
    <key>objects</key>
    <array>
        <!-- Array of node objects -->
    </array>
    <key>readme</key>
    <string></string>
    <key>uidata</key>
    <dict>
        <!-- Node UID -> {xpos, ypos} for canvas layout -->
    </dict>
    <key>userconfigurationconfig</key>
    <array/>
    <key>version</key>
    <string>1.0.0</string>
    <key>webaddress</key>
    <string></string>
</dict>
</plist>
```

### Top-Level Keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `bundleid` | string | Yes | Unique identifier (e.g., `com.author.name`) |
| `category` | string | No | Category: Productivity, Tools, Internet, etc. |
| `connections` | dict | Yes | Node wiring (source UID -> destinations) |
| `createdby` | string | No | Author name |
| `description` | string | No | Workflow description |
| `disabled` | boolean | Yes | Whether workflow is disabled |
| `name` | string | Yes | Display name in Alfred |
| `objects` | array | Yes | All node definitions |
| `readme` | string | No | Markdown documentation |
| `uidata` | dict | Yes | Canvas positions per node |
| `userconfigurationconfig` | array | No | User-configurable variables |
| `variablesdontexport` | array | No | Variables excluded from export |
| `version` | string | No | Semver version |
| `webaddress` | string | No | Project URL |

## Node Object Structure

Every node in the `objects` array follows this structure:

```xml
<dict>
    <key>config</key>
    <dict>
        <!-- Node-type-specific configuration -->
    </dict>
    <key>type</key>
    <string>alfred.workflow.TYPE.NAME</string>
    <key>uid</key>
    <string>GENERATED-UUID</string>
    <key>version</key>
    <integer>1</integer>
</dict>
```

### Node Version Numbers

The `version` integer corresponds to the node type's internal schema version. Use these known-working values:

| Node Type | Version |
|-----------|---------|
| `input.keyword` | 1 |
| `input.scriptfilter` | 3 |
| `input.listfilter` | 1 |
| `input.filefilter` | 1 |
| `trigger.hotkey` | 2 |
| `trigger.external` | 1 |
| `trigger.universalaction` | 1 |
| `trigger.action` | 1 |
| `action.script` | 2 |
| `action.openurl` | 1 |
| `action.openfile` | 1 |
| `action.launchfiles` | 1 |
| `output.clipboard` | 3 |
| `output.notification` | 1 |
| `utility.argument` | 1 |
| `utility.conditional` | 1 |
| `utility.junction` | 1 |
| `automation.runshortcut` | 1 |

## Node Types Reference

### Input Triggers

#### `alfred.workflow.input.keyword` - Keyword Trigger

Activates when user types a keyword in Alfred.

| Config Key | Type | Description |
|------------|------|-------------|
| `argumenttype` | integer | 0=required, 1=optional, 2=none |
| `keyword` | string | The trigger keyword |
| `subtext` | string | Subtitle shown below keyword |
| `text` | string | Title text shown in Alfred |
| `withspace` | boolean | Whether space is needed after keyword |

#### `alfred.workflow.input.scriptfilter` - Script Filter

Runs a script to dynamically generate a list of results in Alfred.

| Config Key | Type | Description |
|------------|------|-------------|
| `alfredfiltersresults` | boolean | Let Alfred filter the script's results |
| `alfredfiltersresultsmatchmode` | integer | 0=word match, 1=prefix |
| `argumenttype` | integer | 0=required, 1=optional, 2=none |
| `argumenttreatemptyqueryasnil` | boolean | Treat empty query as nil |
| `argumenttrimmode` | integer | Trim mode for input |
| `escaping` | integer | Escaping bitmask (102 is common default) |
| `keyword` | string | The trigger keyword |
| `queuedelaycustom` | integer | Custom delay in tenths of seconds |
| `queuedelayimmediatelyinitially` | boolean | Run immediately on first keystroke |
| `queuedelaymode` | integer | 0=immediate, 1=automatic, 2=custom |
| `queuemode` | integer | 1=wait for previous, 2=terminate previous |
| `runningsubtext` | string | Subtitle while script runs |
| `script` | string | Inline script body |
| `scriptargtype` | integer | 0=argv, 1={query} placeholder |
| `scriptfile` | string | External script filename |
| `subtext` | string | Default subtitle |
| `title` | string | Title shown in Alfred |
| `type` | integer | Script language (see Script Types) |
| `withspace` | boolean | Space needed after keyword |

**Script Filter JSON Output Format:**

The script must output JSON to stdout:

```json
{
  "items": [
    {
      "uid": "unique-id",
      "title": "Result Title",
      "subtitle": "Result subtitle",
      "arg": "value passed to next node",
      "icon": { "path": "icon.png" },
      "valid": true,
      "match": "searchable keywords",
      "variables": { "key": "value" },
      "mods": {
        "cmd": { "subtitle": "Cmd action", "arg": "cmd-arg", "valid": true },
        "alt": { "subtitle": "Alt action", "arg": "alt-arg", "valid": true }
      }
    }
  ],
  "cache": { "seconds": 300, "loosereload": true }
}
```

#### `alfred.workflow.input.listfilter` - List Filter

Static list of items for the user to filter and select.

| Config Key | Type | Description |
|------------|------|-------------|
| `argumenttype` | integer | 0=required, 1=optional, 2=none |
| `fixedorder` | boolean | Preserve item order (don't sort) |
| `items` | string | JSON string of items array |
| `keyword` | string | The trigger keyword |
| `matchmode` | integer | Match mode |
| `withspace` | boolean | Space after keyword |

#### `alfred.workflow.input.filefilter` - File Filter

Search for files matching criteria.

| Config Key | Type | Description |
|------------|------|-------------|
| `anchorfields` | integer | Anchor fields bitmask |
| `argumenttype` | integer | Argument type |
| `daterange` | integer | Date range filter |
| `fields` | integer | Searchable fields bitmask |
| `includesystem` | boolean | Include system files |
| `keyword` | string | Trigger keyword |
| `limit` | integer | Max results |
| `scopes` | array | Search scope paths |
| `sortmode` | integer | Sort mode |
| `subtext` | string | Subtitle |
| `title` | string | Title |
| `types` | array | File UTI types to include |
| `withspace` | boolean | Space after keyword |

#### `alfred.workflow.trigger.hotkey` - Hotkey Trigger

Activates on a global keyboard shortcut.

| Config Key | Type | Description |
|------------|------|-------------|
| `action` | integer | 0=pass through, 1=show Alfred |
| `argument` | integer | 0=none, 1=selection in macOS, 2=clipboard |
| `focusedappvariable` | boolean | Set focused app variable |
| `focusedappvariablename` | string | Variable name for focused app |
| `hotkey` | integer | Key code |
| `hotmod` | integer | Modifier bitmask |
| `leftcursor` | boolean | Use left cursor position |
| `modsmode` | integer | Modifier handling mode |
| `relatedAppsMode` | integer | Related apps mode |

**Hotkey modifier bitmask values:**

| Modifier | Value |
|----------|-------|
| None | 0 |
| Shift | 131072 |
| Control | 262144 |
| Option/Alt | 524288 |
| Command | 1048576 |
| Fn | 8388608 |

Combine with addition: Cmd+Shift = 1048576 + 131072 = 1179648

**Note:** Hotkey assignment (the actual key+modifier combo) is best configured by the user in Alfred Preferences, as key codes are hardware-dependent. Set `hotkey` to 0 and `hotmod` to 0 to leave unassigned, then instruct the user to set it.

#### `alfred.workflow.trigger.external` - External Trigger

Trigger from outside Alfred via URL scheme or AppleScript.

| Config Key | Type | Description |
|------------|------|-------------|
| `availableviaurlhandler` | boolean | Available via alfred:// URL |
| `triggerid` | string | Identifier for the trigger |

**Invocation:** `open "alfred://runtrigger/com.bundle.id/triggerid/?argument=value"`

#### `alfred.workflow.trigger.universalaction` - Universal Action

Appears in Alfred's Universal Actions panel.

| Config Key | Type | Description |
|------------|------|-------------|
| `acceptsfiles` | boolean | Accept file input |
| `acceptsmulti` | boolean | Accept multiple items |
| `acceptstext` | boolean | Accept text input |
| `acceptsurls` | boolean | Accept URL input |
| `name` | string | Action name shown to user |

#### `alfred.workflow.trigger.action` - File Action

Appears when user selects "Actions" on a file in Alfred.

| Config Key | Type | Description |
|------------|------|-------------|
| `acceptsmulti` | boolean | Accept multiple files |
| `filetypes` | array | Accepted file UTI types |
| `name` | string | Action name |

### Actions

#### `alfred.workflow.action.script` - Run Script

Executes a script. There are two distinct patterns for running scripts:

**Pattern A: Inline shell script (type 0 or 11, bash/zsh)**
Set `type: 0`, write the command in `script`, leave `scriptfile` empty. The `{query}` placeholder in the script text is replaced with the input (subject to `escaping`). Use `escaping: 102` to prevent shell injection.

```xml
<key>script</key>
<string>python3 src/main.py</string>
<key>type</key>
<integer>0</integer>
<key>escaping</key>
<integer>102</integer>
```

**Pattern B: External script (type 8)**
Set `type: 8`, put the filename in `scriptfile`, leave `script` empty. The script runs directly (needs shebang like `#!/usr/bin/env python3`). The `{query}` is passed as a command-line argument (`sys.argv[1]`). Set `escaping: 0` (no inline text substitution).

```xml
<key>scriptfile</key>
<string>src/main.py</string>
<key>type</key>
<integer>8</integer>
<key>escaping</key>
<integer>0</integer>
```

**XML escaping in inline scripts:** Scripts inside `<string>` tags must XML-escape `&` as `&amp;` and `<` as `&lt;`. This is critical for bash `&&` (write `&amp;&amp;`), redirections with `<`, and comparisons. Quotes and `>` do not need escaping inside `<string>` tags.

| Config Key | Type | Description |
|------------|------|-------------|
| `concurrently` | boolean | Allow concurrent execution |
| `escaping` | integer | Escaping bitmask (see Escaping Bitmask section) |
| `script` | string | Inline script body (Pattern A) |
| `scriptargtype` | integer | 0=argv, 1={query} placeholder |
| `scriptfile` | string | External script filename (Pattern B) |
| `type` | integer | Script language (see Script Types) |

#### `alfred.workflow.action.openurl` - Open URL

| Config Key | Type | Description |
|------------|------|-------------|
| `browser` | string | Bundle ID of browser (empty=default) |
| `skipqueryencode` | boolean | Skip URL encoding the query |
| `skipvarencode` | boolean | Skip URL encoding variables |
| `spaces` | string | Space replacement character |
| `url` | string | URL to open (supports `{query}` and `{var:name}`) |

#### `alfred.workflow.action.openfile` - Open File

| Config Key | Type | Description |
|------------|------|-------------|
| `openwith` | string | App bundle ID to open with |
| `sourcefile` | string | File path to open |

#### `alfred.workflow.action.launchfiles` - Launch Apps/Files

| Config Key | Type | Description |
|------------|------|-------------|
| `paths` | array | Array of file/app paths to launch |
| `toggle` | boolean | Toggle (quit if already running) |

#### `alfred.workflow.action.revealfile` - Reveal in Finder

| Config Key | Type | Description |
|------------|------|-------------|
| `path` | string | Path to reveal |

#### `alfred.workflow.action.browseinalfred` - Browse in Alfred

| Config Key | Type | Description |
|------------|------|-------------|
| `path` | string | Path to browse |
| `sortBy` | integer | Sort field |
| `sortDirection` | integer | Ascending/descending |
| `sortFoldersAtTop` | boolean | Folders first |
| `sortOverride` | boolean | Override default sort |
| `stackBrowserView` | boolean | Stack view |

#### `alfred.workflow.action.browseinterminal` - Browse in Terminal

| Config Key | Type | Description |
|------------|------|-------------|
| `path` | string | Path to open in terminal |

#### `alfred.workflow.action.actioninalfred` - Action in Alfred

| Config Key | Type | Description |
|------------|------|-------------|
| `jumpto` | integer | Jump target |
| `path` | string | Path |
| `type` | integer | Action type |

### Output

#### `alfred.workflow.output.clipboard` - Copy to Clipboard

| Config Key | Type | Description |
|------------|------|-------------|
| `autopaste` | boolean | Auto-paste after copying |
| `clipboardtext` | string | Text to copy (supports `{query}`, `{var:name}`) |
| `ignoredynamicplaceholders` | boolean | Don't expand placeholders |
| `transient` | boolean | Don't add to clipboard history |

#### `alfred.workflow.output.notification` - Post Notification

| Config Key | Type | Description |
|------------|------|-------------|
| `lastpathcomponent` | boolean | Show only filename |
| `onlyshowifquerypopulated` | boolean | Only show if there's output |
| `removeextension` | boolean | Remove file extension |
| `text` | string | Notification body (supports `{query}`) |
| `title` | string | Notification title (supports `{query}`) |

### Utilities

#### `alfred.workflow.utility.argument` - Set Variables / Transform Argument

| Config Key | Type | Description |
|------------|------|-------------|
| `argument` | string | New argument value |
| `passthroughargument` | boolean | Pass through original argument |
| `variables` | dict | Key-value pairs to set as workflow variables |

#### `alfred.workflow.utility.conditional` - Conditional

Routes flow based on variable matching.

| Config Key | Type | Description |
|------------|------|-------------|
| `conditions` | array | Array of condition objects |
| `elselabel` | string | Label for else branch |
| `hideelse` | boolean | Hide else output |

**Each condition object:**

| Key | Type | Description |
|-----|------|-------------|
| `inputstring` | string | Value to test (e.g., `{var:name}`) |
| `matchcasesensitive` | boolean | Case-sensitive match |
| `matchmode` | integer | 0=is, 1=is not, 2=contains, 3=not contains, 4=starts with, 5=ends with, 6=matches regex |
| `matchstring` | string | Value to match against |
| `outputlabel` | string | Label for this output branch |
| `uid` | string | UUID for this output (used in `sourceoutputuid` of connections) |

**Connection wiring for conditionals:** Each condition's `uid` maps to `sourceoutputuid` in the connections dict to route to different destination nodes.

#### `alfred.workflow.utility.junction` - Junction

Merges multiple inputs into one output. Has no config keys.

#### `alfred.workflow.utility.json` - JSON Transform

| Config Key | Type | Description |
|------------|------|-------------|
| `json` | string | JSON transformation definition |

#### `alfred.workflow.utility.replace` - Replace

| Config Key | Type | Description |
|------------|------|-------------|
| `matchmode` | integer | Match mode |
| `matchstring` | string | Pattern to find |
| `replacestring` | string | Replacement text |

#### `alfred.workflow.utility.split` - Split Argument

| Config Key | Type | Description |
|------------|------|-------------|
| `delimiter` | string | Split delimiter |
| `discardemptyarguments` | boolean | Drop empty parts |
| `outputas` | integer | Output format |
| `trimarguments` | boolean | Trim whitespace |
| `variableprefix` | string | Prefix for numbered variables |

#### `alfred.workflow.utility.transform` - Transform

| Config Key | Type | Description |
|------------|------|-------------|
| `type` | integer | Transform type |

#### `alfred.workflow.utility.file` - File Utility

| Config Key | Type | Description |
|------------|------|-------------|
| `fileutivariablename` | string | Variable for file UTI |
| `outputfileuti` | boolean | Output file UTI |

#### `alfred.workflow.utility.hidealfred` - Hide Alfred

| Config Key | Type | Description |
|------------|------|-------------|
| `unstackview` | boolean | Unstack the view |

### User Interface

#### `alfred.workflow.userinterface.text` - Text View

Displays text in a large text window.

| Config Key | Type | Description |
|------------|------|-------------|
| `behaviour` | integer | Behavior mode |
| `fontmode` | integer | Font mode |
| `fontsizing` | integer | Font size |
| `footertext` | string | Footer text |
| `inputfile` | string | Input file path |
| `inputtype` | integer | Input type |
| `loadingtext` | string | Loading text |
| `outputmode` | integer | Output mode |
| `scriptinput` | integer | Script input mode |
| `spellchecking` | boolean | Enable spell check |
| `stackview` | boolean | Stack the view |

### Automation

#### `alfred.workflow.automation.runshortcut` - Run macOS Shortcut

| Config Key | Type | Description |
|------------|------|-------------|
| `inputmode` | integer | Input handling mode |
| `outputmode` | integer | Output handling mode |
| `shortcut` | string | Shortcut name |

#### `alfred.workflow.automation.task` - Automation Task

| Config Key | Type | Description |
|------------|------|-------------|
| `tasksettings` | dict | Task-specific configuration |
| `taskuid` | string | Task identifier (e.g., `com.alfredapp.automation.core/files-and-folders/directory.new`) |

## Script Types

| Value | Language |
|-------|----------|
| 0 | Bash (`/bin/bash`) |
| 1 | PHP |
| 2 | Ruby |
| 3 | Python 2 |
| 4 | Perl |
| 5 | Python 3 |
| 6 | AppleScript |
| 7 | JavaScript for Automation (JXA) |
| 8 | External script (run `scriptfile` directly) |
| 9 | Swift |
| 10 | PowerShell |
| 11 | Zsh (`/bin/zsh`) |

## Data Flow Between Nodes

The fundamental data-passing mechanism in Alfred workflows is **stdout-to-query**: whatever a script node prints to stdout becomes the `{query}` for all downstream connected nodes.

| Source Node Type | What becomes `{query}` for the next node |
|-----------------|------------------------------------------|
| Keyword trigger (argumenttype 0/1) | The text the user typed after the keyword |
| Keyword trigger (argumenttype 2, no arg) | Empty string |
| Script action / Script filter | The script's **stdout** output |
| Universal action trigger | The text/URL/file path the user selected |
| Clipboard output | Passes through its input unchanged |
| Set Variables (utility.argument) | The `argument` value, or passthrough of input |

Non-script nodes (clipboard, notification, open URL, etc.) receive `{query}` from their upstream node and can reference it in their config strings. A clipboard node with `clipboardtext: "{query}"` copies whatever the previous script printed.

## Connections (Wiring Nodes)

The `connections` dict maps each source node UID to an array of destination connection objects:

```xml
<key>connections</key>
<dict>
    <key>SOURCE-NODE-UID</key>
    <array>
        <dict>
            <key>destinationuid</key>
            <string>TARGET-NODE-UID</string>
            <key>modifiers</key>
            <integer>0</integer>
            <key>modifiersubtext</key>
            <string></string>
            <key>vitoclose</key>
            <false/>
        </dict>
    </array>
</dict>
```

### Connection Keys

| Key | Type | Description |
|-----|------|-------------|
| `destinationuid` | string | Target node UID |
| `modifiers` | integer | Modifier key for this connection (0=default) |
| `modifiersubtext` | string | Text shown when modifier held |
| `sourceoutputuid` | string | For conditional nodes: which output branch |
| `vitoclose` | boolean | Close Alfred after this action |

### Modifier Values for Connections

| Modifier | Value |
|----------|-------|
| None (default action) | 0 |
| Option/Alt | 524288 |
| Command | 1048576 |
| Control | 262144 |
| Cmd+Alt+Ctrl | 1835008 |
| Fn | 8388608 |

### Parallel Outputs (Fan-Out)

A single source node can connect to multiple destinations with `modifiers: 0`. All destinations receive the same `{query}` and execute in parallel. This is the standard pattern for performing an action and notifying the user simultaneously:

```xml
<key>SCRIPT-UID</key>
<array>
    <!-- Both fire simultaneously on Enter -->
    <dict>
        <key>destinationuid</key>
        <string>CLIPBOARD-UID</string>
        <key>modifiers</key>
        <integer>0</integer>
        <key>vitoclose</key>
        <false/>
    </dict>
    <dict>
        <key>destinationuid</key>
        <string>NOTIFICATION-UID</string>
        <key>modifiers</key>
        <integer>0</integer>
        <key>vitoclose</key>
        <false/>
    </dict>
</array>
```

### Branching with Modifiers

A single source node can have multiple connections with different modifiers to create alternate actions when the user holds modifier keys:

```xml
<key>SOURCE-UID</key>
<array>
    <!-- Default action (Enter) -->
    <dict>
        <key>destinationuid</key>
        <string>DEFAULT-ACTION-UID</string>
        <key>modifiers</key>
        <integer>0</integer>
        <key>vitoclose</key>
        <false/>
    </dict>
    <!-- Cmd+Enter action -->
    <dict>
        <key>destinationuid</key>
        <string>CMD-ACTION-UID</string>
        <key>modifiers</key>
        <integer>1048576</integer>
        <key>vitoclose</key>
        <false/>
    </dict>
</array>
```

### Conditional Node Connections

Conditional nodes use `sourceoutputuid` to route different condition matches to different destinations:

```xml
<key>CONDITIONAL-NODE-UID</key>
<array>
    <dict>
        <key>destinationuid</key>
        <string>DEST-FOR-CONDITION-1</string>
        <key>modifiers</key>
        <integer>0</integer>
        <key>sourceoutputuid</key>
        <string>CONDITION-1-UID</string>
        <key>vitoclose</key>
        <false/>
    </dict>
    <dict>
        <key>destinationuid</key>
        <string>DEST-FOR-CONDITION-2</string>
        <key>modifiers</key>
        <integer>0</integer>
        <key>sourceoutputuid</key>
        <string>CONDITION-2-UID</string>
        <key>vitoclose</key>
        <false/>
    </dict>
</array>
```

## Canvas Layout (uidata)

Every node needs an entry in `uidata` with at least x/y coordinates:

```xml
<key>uidata</key>
<dict>
    <key>NODE-UID</key>
    <dict>
        <key>xpos</key>
        <real>150</real>
        <key>ypos</key>
        <real>150</real>
    </dict>
</dict>
```

**Layout conventions:**
- Nodes flow left-to-right: triggers at x=30-90, actions at x=250-400, outputs at x=500+
- Vertical spacing between parallel branches: ~125px apart
- Horizontal spacing between connected nodes: ~150-200px apart
- Optional keys: `colorindex` (integer, node color), `note` (string, developer annotation)

## User Configuration Variables

Define user-editable settings with `userconfigurationconfig`:

```xml
<key>userconfigurationconfig</key>
<array>
    <dict>
        <key>config</key>
        <dict>
            <key>default</key>
            <string>default_value</string>
            <key>placeholder</key>
            <string>hint text</string>
            <key>required</key>
            <true/>
            <key>trim</key>
            <true/>
        </dict>
        <key>description</key>
        <string>What this setting does</string>
        <key>label</key>
        <string>Setting Label</string>
        <key>type</key>
        <string>textfield</string>
        <key>variable</key>
        <string>variable_name</string>
    </dict>
</array>
```

### Configuration Types

| Type | Description | Extra Config Keys |
|------|-------------|-------------------|
| `textfield` | Single-line text | `default`, `placeholder`, `required`, `trim` |
| `textarea` | Multi-line text | `default`, `placeholder`, `required`, `trim`, `verticalsize` |
| `checkbox` | Boolean toggle | `default` (boolean), `text` (checkbox label) |
| `popupbutton` | Dropdown menu | `default`, `pairs` (array of `[label, value]` arrays) |

## Variable Placeholders

Use these anywhere in config strings:

| Placeholder | Description |
|-------------|-------------|
| `{query}` | Current input/argument passed to the node |
| `{var:variable_name}` | Custom workflow variable |
| `{const:alfred_workflow_name}` | Workflow display name |
| `{const:alfred_workflow_bundleid}` | Workflow bundle ID |
| `{const:alfred_workflow_data}` | Workflow data directory path |
| `{const:alfred_workflow_cache}` | Workflow cache directory path |
| `{const:alfred_workflow_description}` | Workflow description |
| `{const:alfred_workflow_uid}` | Workflow UID |
| `{const:alfred_workflow_version}` | Workflow version |

## Escaping Bitmask

The `escaping` key is a bitmask controlling which characters are escaped in `{query}`:

| Bit | Value | Character |
|-----|-------|-----------|
| 1 | 1 | Spaces |
| 2 | 2 | Backquotes |
| 3 | 4 | Double quotes |
| 4 | 8 | Backslashes |
| 5 | 16 | Dollar signs |
| 6 | 32 | Semicolons |
| 7 | 64 | Single quotes |

Common value: `102` = 2+4+32+64 (backquotes, double quotes, semicolons, single quotes).

**When to use which value:**

| Script Pattern | `escaping` | Why |
|---------------|------------|-----|
| Inline bash/zsh (type 0/11) with `{query}` | `102` | Escapes characters that break shell syntax while preserving spaces and backslashes in user input |
| External script (type 8) | `0` | No inline text substitution occurs, so escaping is irrelevant |
| Inline script that ignores `{query}` | `0` | No user input is interpolated into the script text |
| Python/Ruby/etc. direct (type 5/2/etc.) | `0` | Alfred passes `{query}` via argv, not text substitution |

## Restarting Alfred

After writing workflow files, restart Alfred to register:

```bash
killall Alfred && sleep 1 && open -a "Alfred 5"
```

Alfred watches its workflow directories. A restart forces a full reload of all workflows. There is no lighter-weight reload mechanism available from the CLI.

## External Trigger Invocation

Workflows with external triggers can be invoked via URL scheme:

```bash
open "alfred://runtrigger/BUNDLE_ID/TRIGGER_ID/?argument=VALUE"
```

## Complete Example: Keyword -> Script -> Clipboard

A workflow that converts clipboard text to title case when the user types "title":

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>bundleid</key>
    <string>com.user.title-case</string>
    <key>connections</key>
    <dict>
        <key>KEYWORD-UID</key>
        <array>
            <dict>
                <key>destinationuid</key>
                <string>SCRIPT-UID</string>
                <key>modifiers</key>
                <integer>0</integer>
                <key>modifiersubtext</key>
                <string></string>
                <key>vitoclose</key>
                <false/>
            </dict>
        </array>
        <key>SCRIPT-UID</key>
        <array>
            <dict>
                <key>destinationuid</key>
                <string>CLIPBOARD-UID</string>
                <key>modifiers</key>
                <integer>0</integer>
                <key>modifiersubtext</key>
                <string></string>
                <key>vitoclose</key>
                <false/>
            </dict>
        </array>
    </dict>
    <key>createdby</key>
    <string>Claude</string>
    <key>description</key>
    <string>Convert clipboard text to title case</string>
    <key>disabled</key>
    <false/>
    <key>name</key>
    <string>Title Case</string>
    <key>objects</key>
    <array>
        <dict>
            <key>config</key>
            <dict>
                <key>argumenttype</key>
                <integer>2</integer>
                <key>keyword</key>
                <string>title</string>
                <key>subtext</key>
                <string>Convert clipboard to title case</string>
                <key>text</key>
                <string>Title Case</string>
                <key>withspace</key>
                <false/>
            </dict>
            <key>type</key>
            <string>alfred.workflow.input.keyword</string>
            <key>uid</key>
            <string>KEYWORD-UID</string>
            <key>version</key>
            <integer>1</integer>
        </dict>
        <dict>
            <key>config</key>
            <dict>
                <key>concurrently</key>
                <false/>
                <key>escaping</key>
                <integer>102</integer>
                <key>script</key>
                <string>pbpaste | python3 -c "import sys; print(sys.stdin.read().title(), end='')"</string>
                <key>scriptargtype</key>
                <integer>1</integer>
                <key>scriptfile</key>
                <string></string>
                <key>type</key>
                <integer>0</integer>
            </dict>
            <key>type</key>
            <string>alfred.workflow.action.script</string>
            <key>uid</key>
            <string>SCRIPT-UID</string>
            <key>version</key>
            <integer>2</integer>
        </dict>
        <dict>
            <key>config</key>
            <dict>
                <key>autopaste</key>
                <false/>
                <key>clipboardtext</key>
                <string>{query}</string>
                <key>ignoredynamicplaceholders</key>
                <false/>
                <key>transient</key>
                <false/>
            </dict>
            <key>type</key>
            <string>alfred.workflow.output.clipboard</string>
            <key>uid</key>
            <string>CLIPBOARD-UID</string>
            <key>version</key>
            <integer>3</integer>
        </dict>
    </array>
    <key>readme</key>
    <string></string>
    <key>uidata</key>
    <dict>
        <key>KEYWORD-UID</key>
        <dict>
            <key>xpos</key>
            <real>30</real>
            <key>ypos</key>
            <real>150</real>
        </dict>
        <key>SCRIPT-UID</key>
        <dict>
            <key>xpos</key>
            <real>230</real>
            <key>ypos</key>
            <real>150</real>
        </dict>
        <key>CLIPBOARD-UID</key>
        <dict>
            <key>xpos</key>
            <real>430</real>
            <key>ypos</key>
            <real>150</real>
        </dict>
    </dict>
    <key>userconfigurationconfig</key>
    <array/>
    <key>version</key>
    <string>1.0.0</string>
    <key>webaddress</key>
    <string></string>
</dict>
</plist>
```

**Important:** Replace `KEYWORD-UID`, `SCRIPT-UID`, and `CLIPBOARD-UID` with real UUIDs generated by `uuidgen`. Every UID in a workflow must be unique.

## Validation Checklist

Before writing a workflow, verify:

1. Every node in `objects` has a unique `uid`
2. Every `uid` referenced in `connections` exists in `objects`
3. Every `destinationuid` in connections exists in `objects`
4. Every node `uid` has an entry in `uidata`
5. `sourceoutputuid` values match condition `uid` values in conditional nodes
6. Script type integers match the intended language
7. External script files referenced in `scriptfile` exist in the workflow directory
8. `bundleid` is unique across all installed workflows
9. The plist is valid XML (properly closed tags, escaped special characters)
10. Special characters in scripts are XML-escaped (`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&apos;`)

## Tips

- For simple keyword->script workflows, prefer inline scripts over external files
- Use `argumenttype: 2` (no argument) for keyword triggers that don't need input
- Use `scriptargtype: 1` with `{query}` for scripts that process the previous node's output
- Use `scriptargtype: 0` for scripts that receive arguments via `$1`/`argv`
- Set `queuedelaymode: 1` on script filters for automatic debouncing
- Set `queuemode: 2` on script filters to cancel previous runs on new input
- **Python path reliability:** macOS ships `/usr/bin/python3` (Xcode CLT). If using an inline bash script (type 0) that calls `python3`, the PATH may be more restricted than an interactive shell. Prefer `/usr/bin/python3` for reliability, or use type 5 (Python 3 direct) which uses Alfred's own Python resolution. For external scripts (type 8), use `#!/usr/bin/env python3` in the shebang.
- For workflows with user-configurable keywords, use `{var:keyword_name}` as the keyword value and define it in `userconfigurationconfig`
- Test plists with `plutil -lint info.plist` for XML syntax errors, and `plutil -p info.plist` to pretty-print for debugging
