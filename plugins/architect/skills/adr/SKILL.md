---
name: adr
description: Record an architectural decision as a numbered ADR in docs/adr/, capturing the context, the options that were rejected, the deciding factor, the consequences accepted, and the conditions that should reopen it. Use immediately after a human chooses between architectural options, or when asked to write down or supersede a decision.
when_to_use: Triggered by "record this decision", "write an ADR", "document why we chose", "supersede ADR-000N", or automatically after a decision checkpoint in any other architect skill.
argument-hint: [decision title]
---

# Architecture decision record

Decision: `$ARGUMENTS`

## 1. Check whether it is worth recording

Write an ADR when a future engineer would otherwise ask "why on earth is it like
this?" — specifically when the decision:

- Chose between genuinely viable options, or
- Accepted a cost, limitation, or risk deliberately, or
- Is expensive to reverse, or
- Contradicts what someone would reasonably expect.

Do **not** write one for a choice any competent engineer would make the same way. A
directory full of ADRs recording the obvious makes the important ones invisible.

If it does not clear the bar, say so in one line and stop.

## 2. Check for an existing decision

List `docs/adr/`. If a Confluence MCP server is connected, also search Confluence —
the organization may have recorded this decision outside the repository, and a second
contradictory record is the worst outcome. See
`${CLAUDE_PLUGIN_ROOT}/references/stack/confluence-mcp.md`.

If an ADR already covers this ground:

- **Same decision, more detail** → update it in place.
- **Reverses it** → write a new ADR, set the old one's status to
  `Superseded by ADR-NNNN`, and state in the new one what changed in the world. Do
  not edit history to look consistent; the reversal is the useful part.
- **Adjacent** → cross-reference both.

## 3. Number and name it

**ADRs live in the repository**, always — even when design documents live in
Confluence. They version with the code they constrain and appear in the diff a
reviewer reads. If the organization also wants it visible in Confluence, publish a
link, not a copy.

Next free four-digit number in `docs/adr/`, starting at `0001`. Filename:
`docs/adr/NNNN-<kebab-case-slug>.md`.

**Title states the decision as a claim, not a topic.** "Use Kafka for order events",
not "Messaging technology". A reader scanning filenames should learn the decisions
without opening anything.

## 4. Write it

Follow `${CLAUDE_PLUGIN_ROOT}/templates/adr.md`.

The parts that are usually done badly, and must not be:

- **Options considered.** Include the rejected options with their real merits. An
  ADR listing only the chosen option is marketing. The next engineer needs to know
  the alternative was understood, not overlooked.
- **The deciding factor.** Name the single thing that tipped it. If that factor
  changes, the decision should be revisited — which is what makes the ADR useful
  years later.
- **Consequences.** The costs accepted and the new permanent obligations: an index
  to maintain, a consumer group to watch, a schema to keep compatible. Rate how
  reversible it is: easy, moderate, or hard.
- **Revisit when.** Concrete conditions — a volume threshold, a second consumer, a
  vendor change. "When it becomes a problem" is not a condition.

## 5. Attribute the decision honestly

The `Deciders` field names the humans who chose. If Claude drafted the ADR after a
developer answered a decision checkpoint, the developer is the decider. Never list
the assistant as a decider, and never record a decision the human did not actually
make — if the choice was made by default rather than deliberately, say so in the
context.

## 6. Confirm

Show the developer the ADR path, the title, and the deciding factor in two lines.
Ask them to correct the deciding factor if you got it wrong — that field is the one
most worth being right.

If this is the repository's first ADR, also create `docs/adr/README.md` with a
one-line index that lists each ADR by number, title, and status, and add a line to
it for every ADR thereafter.
