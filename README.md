# CAO — Chief Architect Office marketplace

A private Claude Code plugin marketplace. It currently distributes one plugin:

| Plugin | What it does |
| --- | --- |
| **architect** | Acts as the organization's chief software architect during planning, review, and coding. See [`plugins/architect/README.md`](plugins/architect/README.md). |

## Install for a team

Commit this to the repository your team works in, as `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "cao": {
      "source": { "source": "github", "repo": "kutib/cao" }
    }
  },
  "enabledPlugins": {
    "architect@cao": true
  }
}
```

Developers pick it up the next time they trust the folder — there is no per-developer
setup step.

To install it manually instead:

```bash
claude
/plugin marketplace add kutib/cao
/plugin install architect@cao
```

**This is a private repository.** Claude Code clones it with each developer's own git
credentials, so everyone who installs the plugin needs read access to `kutib/cao`.

## Develop

```bash
# Load the plugin without installing it
claude --plugin-dir ./plugins/architect

# After editing, inside the session
/reload-plugins

# Before opening a PR
claude plugin validate ./plugins/architect --strict
```

## Release

1. Change the plugin under `plugins/architect/`.
2. Bump `version` in `plugins/architect/.claude-plugin/plugin.json`. **Teams receive
   updates only when this changes.**
3. Run `claude plugin validate ./plugins/architect --strict`.
4. Merge to the default branch. Users refresh with `/plugin marketplace update`.

## Changing a standard

The reference files under `plugins/architect/references/` are the organization's
architecture standards. Changes go through a pull request to this repository so the
reasoning is reviewed and recorded.

Disagreement with a rule is legitimate — raise it as a PR against the rule, with the
argument. A standard nobody can justify should be deleted rather than tolerated.

Before first rollout, fill in `plugins/architect/references/org-profile.md`. It is
the only file holding organization-specific values, and the skills will ask the
developer whenever they hit a `TODO` there.
