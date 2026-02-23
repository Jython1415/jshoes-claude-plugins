---
name: code-review
description: >
  Multi-agent code review for pull requests. Use when reviewing a PR,
  after creating or updating a pull request, when asked to check code
  quality before merging, or when doing a final review of changes.
  Checks for bugs, logic errors, and convention document compliance.
argument-hint: "[--light] [--comment]"
---

# Code Review

You have been asked to review a pull request (or have determined that a
review is warranted). Perform a thorough, high-signal review using
parallel agents.

**Agent assumptions (communicate to all agents and subagents):**
- All tools are functional. Do not test tools or make exploratory calls.
- Only call a tool if required. Every tool call should have a clear purpose.

## Arguments

- `--light`: Cost-optimized single-agent review. Same quality bar as the
  full pipeline; uses Sonnet instead of Opus and one agent instead of many.
  A good default for any PR when cost matters. Replaces Steps 1–3 with one
  structured pass; Steps 4–5 apply normally.
- `--comment`: Post inline GitHub comments for each finding (applies in
  both modes).

## Light Mode (when --light is passed)

Skip Steps 1–3. Launch **one Sonnet agent** with the PR number and these
instructions:

1. Run `gh pr view <PR_NUMBER>` to get the PR title and description.
2. Run `gh pr diff <PR_NUMBER>` to get the full diff.
3. **Fetch convention docs (mandatory):** Check for CLAUDE.md and README.md
   in the repo root and in every directory that contains a modified file.
   Read each file you find. Do this before any review passes begin.
4. **Enumerate changed files:** List every file modified in the diff. Mark
   any that are high-risk: authentication/authorization logic, state
   mutation, external API calls, data serialization, security-adjacent code.
   This list is your coverage checklist for Pass 3.
5. **Orient:** Write 2–3 sentences summarizing what this PR does, in plain
   language. This grounds the review passes that follow.
6. Do a thorough review. Work through these passes in order:

   **Pass 1 — Category sweep:**
   Using the convention docs from step 3, work through each file from
   step 4, starting with high-risk files. For each file, scan for
   candidates in each category:
   - `correctness`: logic errors, wrong results, missing edge cases
   - `security`: injection, auth bypass, data exposure, unsafe operations
   - `convention`: violations of CLAUDE.md and README.md rules found in
     step 3
   - `performance`: algorithmic issues, unnecessary work in hot paths

   **Pass 2 — Validate candidates:**
   For each candidate from Pass 1, apply the HIGH SIGNAL ONLY bar:
   flag only issues where code will definitely fail, produce wrong results
   regardless of inputs, or clearly violate a stated convention.
   For each surviving finding, it must have:
   - **Category**: one of `correctness`, `security`, `convention`,
     `performance`
   - **Severity**: one of `critical`, `major`, `minor`
   - **Evidence**: the exact code snippet from the diff that demonstrates
     the issue — if you cannot cite a specific snippet, skip the finding
   - **Confidence**: 0.0–1.0 — skip any finding below 0.7

   **Pass 3 — Coverage check, then self-check:**
   List every file from step 4. Confirm you examined each one in Pass 1.
   For any file not yet examined, scan it now using the Pass 1 categories.
   Then ask: "Is there anything I missed?" Re-read any high-risk areas
   (auth, data mutation, external calls). Add new findings that pass the
   bar above.

7. Return a list of findings with: file path, line range, category,
   severity, description, evidence, confidence.

After this agent returns, proceed to Step 4.

Follow these steps precisely (full mode only — skip if --light was passed):

## Step 1: Gather context (2 parallel agents)

**Agent A (haiku):** Return a list of file paths for all relevant convention
documents (CLAUDE.md, README.md, CONTRIBUTING.md, ARCHITECTURE.md,
DEVELOPMENT.md, and similar files that codify codebase practices):
- Convention documents in the repo root, if they exist
- Any convention documents in directories containing modified files, and
  all parent directories up to the repo root

Use `gh pr diff` and Glob to identify these.

**Agent B (sonnet):** View the PR with `gh pr view` and `gh pr diff`. Return:
- PR number, title, description
- List of changed files
- Plain-language summary of what the changes do

## Step 2: Review (4 parallel agents)

Give each agent the PR title, description, and summary from Step 1. Each
agent returns a list of issues. Each issue includes: description, file path,
line range, and reason (e.g. "convention document violation", "bug").

**Agents 1 + 2: Convention document compliance (sonnet)**
Audit changes for compliance with convention documents (CLAUDE.md and
README.md files found in Step 1) in parallel. When evaluating compliance
for a file, only consider convention documents that share a file path with
the file or its parent directories. Each agent reviews independently
for redundancy.

**Agent 3: Bug detection -- diff only (opus)**
Scan for obvious bugs. Focus only on the diff without reading extra context.
Flag only significant bugs; ignore nitpicks and likely false positives. Do
not flag issues that cannot be validated without context outside the diff.

**Agent 4: Bug detection -- with context (opus)**
Look for problems in the introduced code: security issues, incorrect logic,
missing error handling. Read surrounding code as needed, but only flag issues
within the changed code.

**CRITICAL: HIGH SIGNAL ONLY.** Flag issues where:
- Code will fail to compile or parse (syntax errors, type errors, missing
  imports, unresolved references)
- Code will definitely produce wrong results regardless of inputs (clear
  logic errors)
- Clear, unambiguous convention document violations where you can quote the exact rule

Do NOT flag:
- Code style or quality concerns
- Potential issues that depend on specific inputs or state
- Subjective suggestions or improvements
- Pre-existing issues not introduced by this PR
- Pedantic nitpicks a senior engineer would ignore
- Issues a linter would catch (do not run the linter)
- General code quality concerns (e.g. test coverage) unless a convention
  document explicitly requires it
- Issues mentioned in a convention document but silenced in code (e.g. lint
  ignore comments)
- Something that appears to be a bug but is actually correct

**If you are not certain an issue is real, do not flag it. False positives
erode trust and waste reviewer time.**

## Step 3: Validate (parallel agents per issue)

For each issue found by Agents 3 and 4 in Step 2, launch a parallel
subagent to validate it. Each validation agent receives:
- The PR title and description
- The issue description and location
- Access to read the relevant source files

The agent's job: verify the issue is real with high confidence. Examples:
- If "variable is not defined" was flagged, confirm it is actually undefined
  in scope.
- For convention document violations, confirm the rule is scoped to that
  file and is actually violated.

Use opus subagents for bugs and logic issues. Use sonnet for convention
document violations.

Filter out any issues not validated. This produces the final issue list.

## Step 4: Output

Print a summary of findings to the terminal.

If issues were found, list each with:
- File path and line range
- Brief description
- Category (bug, convention document violation, etc.)

If no issues were found:

    No issues found. Checked for bugs and convention document compliance.

If `--comment` was NOT passed as an argument, **stop here. Do not post any
GitHub comments.**

## Step 5: Post comments (only if --comment was passed)

If NO issues were found, post a single summary comment and stop:

    gh pr comment <PR_NUMBER> --body "## Code review

    No issues found. Checked for bugs and convention document compliance."

If issues WERE found, post inline review comments using `gh api`.

First get the latest commit SHA:

    COMMIT_SHA=$(gh pr view <PR_NUMBER> --json headRefOid -q '.headRefOid')

For each issue, post an inline comment:

    gh api \
      repos/{owner}/{repo}/pulls/<PR_NUMBER>/comments \
      -f body="<comment body>" \
      -f path="<file path>" \
      -f commit_id="$COMMIT_SHA" \
      -F line=<line_number> \
      -f side="RIGHT"

For issues spanning multiple lines, add `start_line` and `start_side`:

    gh api \
      repos/{owner}/{repo}/pulls/<PR_NUMBER>/comments \
      -f body="<comment body>" \
      -f path="<file path>" \
      -f commit_id="$COMMIT_SHA" \
      -F start_line=<start_line_number> \
      -f start_side="RIGHT" \
      -F line=<end_line_number> \
      -f side="RIGHT"

Comment formatting rules:
- Provide a brief description of the issue
- For small, self-contained fixes (< 6 lines), include a GitHub suggestion
  block using triple-backtick `suggestion` fencing
- For larger fixes (6+ lines, structural changes, changes spanning multiple
  locations), describe the issue and suggested approach without a suggestion
  block
- Never post a suggestion unless committing it fully resolves the issue
- When citing a convention document violation, link to the relevant file
  using full SHA:
  `https://github.com/{owner}/{repo}/blob/{full_sha}/{path}#L{start}-L{end}`
- You must use the full 40-character SHA in links. Do not use shell
  interpolation like `$(git rev-parse HEAD)` inside comment bodies -- the
  body is rendered as Markdown, not executed.
- For comment bodies containing backticks or newlines, write the body to a
  temp file and pass it via `-F body=@<tmpfile>` to avoid shell escaping
  issues.

**Post only ONE comment per unique issue. No duplicates.**

## Notes

- Use `gh` CLI for all GitHub interactions. Do not use web fetch.
- Create a task list (TaskCreate) before starting.
- `{owner}/{repo}` can be obtained from
  `gh repo view --json nameWithOwner -q '.nameWithOwner'`.
