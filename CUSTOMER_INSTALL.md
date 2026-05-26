# Codeer Skill Customer Install Guide

This guide helps you set up the Codeer CLI and Codeer Agent Skill for Claude
Code or Codex.

Use this guide if you already use Claude Code or Codex, but do not want to
manage Codeer through the web UI only.

## What You Will Install

There are two separate pieces:

1. **Codeer CLI**: the `codeer` command-line tool. Install this with `pipx`.
2. **Codeer Agent Skill**: the instructions Claude Code or Codex uses to work
   with Codeer agents, knowledge base files, eval cases, and production
   histories.

The Skill does not include your API key. Keep API keys outside chats, prompts,
and shared project files.

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

Create a local CLI profile:

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

## 5. Verify the Setup

Open Claude Code or Codex in the project where you want to manage the Codeer
agent, then ask it to run:

```bash
codeer check
```

Then list the workspace agents:

```bash
codeer agent list
```

If both commands work, the CLI credentials and Skill setup are ready.

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
