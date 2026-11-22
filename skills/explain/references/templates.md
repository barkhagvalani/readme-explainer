# Explainer Templates

Template version: 1

Write for a product manager, operator or new hire who does not read code.
Use short sentences and everyday words. Leave out a section when its sources
say nothing about it; never fill a section with guesses.

## Package Explainer (`EXPLAINER.md` beside a directory's README)

```markdown
# <Plain name of what this part does>

**In one sentence:** <what it does for people, not how it works>

## What it does

<2 to 5 short paragraphs or bullets.>

## How it works

<Optional Mermaid diagram, only when the README describes 3+ steps, states,
parties or data moving between systems. One plain sentence under it that says
the same thing, for viewers that do not show diagrams.>

## Who or what uses it

## What it touches

<Other systems, files, services, emails, money or data it reads or changes.>

## Rules it always keeps

<The promises in the README, in plain words.>

## When something goes wrong

<What a person would notice, and who or what to check.>

## What's inside

| Part | What it does |
| :--- | :----------- |
| [<child name>](<child>/EXPLAINER.md) | <one line> |
| <folded directory name> | <one line from its README> |

Source: [README.md](README.md)
```

Rules:

*   Define each project term in plain words where it first appears. Do not link
    to a glossary; each package explainer must stand alone.
*   A definition of general knowledge (for example, what a webhook is) needs no
    source. A claim about what something does in this project must come from
    the sources.
*   Keep it under 80 lines, not counting diagrams.
*   Leave "What's inside" out when the directory has no children.

## Repository Explainer (`EXPLAINER.md` at the repository root)

Same outline as a package explainer, plus these sections after "What it does":

```markdown
## What people see

## Data in and out

## Schedule

<A table of scheduled jobs, if the sources mention any.>

## Costs and guardrails

## Glossary

| Term | What it means here |
| :--- | :----------------- |
```

Rules:

*   The glossary covers project terms used in this explainer and in its child
    explainers' definitions, sorted alphabetically.
*   No line limit, because it carries the glossary.

## Diagrams

| Shape in the README | Mermaid type |
| :------------------ | :----------- |
| 3+ steps, or data moving between systems | `flowchart LR` |
| States something moves through | `stateDiagram-v2` |
| Ordered requests among 3+ parties | `sequenceDiagram` |
| Scheduled jobs | A table (preferred) or `timeline` |

Every node and arrow names something the sources name. At most 12 nodes. A
parent links to a child's explainer instead of repeating its diagram.
