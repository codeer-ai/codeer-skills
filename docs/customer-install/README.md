# Codeer Skill Customer Install Guide

This guide helps you set up the Codeer CLI and Codeer Agent Skill for Claude
Code or Codex.

Use this guide if you want Claude Code or Codex to help with the Codeer Agent
lifecycle: planning agents from your files and KB, analyzing production
histories, designing behavior eval cases, debugging failed behaviors, and
showing proposed changes before anything is applied.

## What You Will Install

There are two separate pieces:

1. **Codeer CLI**: the local `codeer` command-line tool. It signs in to Codeer,
   calls the Codeer API, and runs commands such as `codeer agent`,
   `codeer eval`, `codeer history`, and `codeer kb`.
2. **Codeer Agent Skill**: the workflow instructions Claude Code or Codex uses
   to understand the Codeer Agent lifecycle: how to plan an agent, prepare KB,
   design behavior cases, analyze production histories, and ask before making
   changes.

The Skill does not include your API key. Keep API keys outside chats, prompts,
and shared project files.

## What You Can Do With This Skill

- Plan and create an Agent v0 from a folder of KB, product docs, SOPs, or other
  source files.
- Generate behavior case categories, cases, and rubrics before applying them.
- Use failed behavior cases to decide whether to adjust KB, the Agent, retrieval,
  or Standard / Rubric.
- Analyze production histories and negative feedback to find failure patterns
  and coverage gaps.
- Help you start the next iteration with evidence and a preview of proposed
  changes before anything is applied.

## Requirements

- Python 3.11 or newer
- Claude Code or Codex
- A Codeer account with access to the target workspace
- Permission to issue an Admin workspace API key

## 1. Create a Codeer API Key

1. Open your Codeer dashboard.
2. In the left sidebar, open **API Keys**.
3. Click **Issue New Key**.
4. Enter a key name, such as `Claude Code` or `Codex`.
5. Choose **Admin** access.
6. Optionally set an expiration date.
7. Click **Issue Key**.
8. Copy the full API key immediately and store it securely.

The full API key is shown only once. If you close the dialog before saving it,
revoke that key and issue a new one.

Use **Admin** for this setup because the Codeer Agent Skill can create or update
agents, knowledge base resources, and eval resources. **Member** keys are only
for lower-risk chat, read, and list use cases.

## 2. Install the Codeer CLI

Install the CLI from PyPI with `pipx`:

```bash
pipx install codeer-cli
```

Verify that the command is available:

```bash
codeer --help
```

If `pipx` is not installed:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

Then restart the terminal and run:

```bash
pipx install codeer-cli
```

If your shell cannot find `codeer`, restart the terminal and try again. If it
still cannot find the command, run:

```bash
pipx ensurepath
```

As a fallback, you can install into your user Python environment:

```bash
python -m pip install --user codeer-cli
```

## 3. Configure Codeer CLI Credentials

Create a local CLI profile. The profile name `work` is only an example. You can
choose any name that is easy to recognize, such as `codeer`, `prod`,
`client-a`, or `support-agent`. If you choose a different name, use the same
name in the later `codeer profile use ...` command.

```bash
codeer profile add work
```

The command will ask for the API key. Paste the key you created in Codeer. The
key is not echoed back on screen.

Select the profile:

```bash
codeer profile use work
```

Verify the setup:

```bash
codeer check
```

`codeer check` should confirm authentication, workspace scope, and organization
scope. If you already know the default agent ID for this project, you can also
set it as a non-secret environment variable:

```bash
export CODEER_AGENT_ID=<agent-id>
```

Do not put `CODEER_API_KEY` into `.claude/settings.json`, project `.env` files,
Git commits, or agent chat messages.

## 4. Install the Skill

### Claude Code

Install the Skill from the public GitHub `codeer-agent` folder URL:

```bash
claude install-skill https://github.com/codeer-ai/codeer-skills/tree/main/codeer-agent
```

Use the `codeer-agent` folder URL, not the repository root.

### Codex

Install the Skill through Codex's built-in skill installer:

```text
$skill-installer install https://github.com/codeer-ai/codeer-skills/tree/main/codeer-agent
```

Restart Codex if the skill does not appear after installation.

## 5. Verify the CLI and API Setup

First verify the local CLI and Codeer API credentials:

```bash
codeer check
```

Then list the workspace agents:

```bash
codeer agent list
```

If both commands work, the CLI credentials are ready.

## 6. Verify the Skill

Open Claude Code or Codex in the project where you want to manage the Codeer
agent, then ask:

```text
Please confirm whether the Codeer Agent Skill is loaded. Explain how you can
help me plan an Agent from KB/files, create behavior cases, analyze production
history, and show me proposed changes before applying them.
```

The answer should mention the Codeer Agent lifecycle, behavior cases,
production history, and asking for confirmation before creating, updating, or
publishing Codeer resources.

## 7. What To Do Next

If you do not have an agent yet, point Claude Code or Codex at your KB folder,
product docs, SOPs, or source files and ask it to discuss what Agent v0 should
be built.

If you have an agent but no behavior cases yet, ask it to design behavior
categories, cases, and rubrics before applying anything.

If you have behavior cases but some are failing, ask it to analyze whether the
fix belongs in the KB, the Agent instructions, retrieval, or the Standard /
Rubric.

If the agent is already in production, ask it to analyze production histories
and negative feedback to find patterns and coverage gaps.

If you are preparing the next version, ask it to propose changes, show a
preview of what will change, and wait for approval before applying or
publishing.

## Common Issues

### `codeer` Command Not Found

The CLI installed, but your shell cannot find the executable. Run:

```bash
pipx ensurepath
```

Then restart the terminal. If you used the fallback pip install, make sure your
Python user scripts directory is on `PATH`.

### `codeer check` Shows 401 or 403

The API key is missing, invalid, expired, revoked, or under-scoped. Create a new
Admin workspace API key and update the CLI profile:

```bash
codeer profile add work
codeer profile use work
codeer check
```

### The Wrong Workspace Appears

The active API key belongs to a different workspace. Switch to a profile created
with the correct workspace API key:

```bash
codeer profile use <profile-name>
codeer check
```

### The Agent Is Not Found

If you set `CODEER_AGENT_ID`, make sure that agent belongs to the same workspace
as the API key. You can unset the default and list available agents:

```bash
unset CODEER_AGENT_ID
codeer agent list
```

### The API Key Was Lost

Codeer only shows the full key once. Revoke the lost key in **API Keys**, then
issue a new Admin key and update your CLI profile.

## Maintenance

Upgrade the CLI:

```bash
pipx upgrade codeer-cli
codeer check
```

Reinstall the Claude Code Skill if Codeer publishes Skill changes you need:

```bash
claude install-skill https://github.com/codeer-ai/codeer-skills/tree/main/codeer-agent
```

For Codex, rerun:

```text
$skill-installer install https://github.com/codeer-ai/codeer-skills/tree/main/codeer-agent
```

Remove the CLI:

```bash
pipx uninstall codeer-cli
```
