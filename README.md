# README Explainer

Turn a repository's README files into plain-language explainers for people who
don't read code: product managers, operators, designers and new hires.

READMEs are written for engineers and AI agents. They're full of file names,
interfaces and test commands. README Explainer writes an `EXPLAINER.md` beside
each README that says, in everyday words, what that part of the system does, who
uses it, what it touches and what to check when something goes wrong. The root
explainer adds a glossary.

## How it works

1.  **Reads only READMEs.** It never reads code, so an explainer says only what
    the READMEs say. Missing facts are reported as gaps instead of being guessed.
2.  **Writes from the bottom up.** Each folder's explainer is written before its
    parent's, so a parent can summarise its children.
3.  **Checks each explainer twice, with fresh eyes.** A fact checker compares it
    with its READMEs, and a reader who doesn't write code reports anything hard
    to follow. Both run as separate read-only agents with no memory of the
    conversation.
4.  **Leaves your writing alone.** An `EXPLAINER.md` that a person wrote or edited
    is never overwritten.
5.  **Knows when it's out of date.** Each explainer records a fingerprint of its
    sources, so a later run can tell which explainers need rewriting.

## Install

In Claude Code:

```sh
claude plugin marketplace add barkhagvalani/readme-explainer
claude plugin install readme-explainer@readme-explainer
```

Requirements:

*   Claude Code with plugin support.
*   Python 3.8 or later, used for hashing and checks. It uses only the standard
    library.

## Use

From your repository:

```text
/readme-explainer:explain
```

Options:

| Option | Default | What it does |
| :----- | :------ | :----------- |
| `path` | current folder | The repository root, or a folder inside it. |
| `refresh=true` | off | Also rewrites explainers that are out of date. |
| `extra_sources=<file>,<file>` | none | Extra human-written files the root explainer may use, such as a runbook. |

Example:

```text
/readme-explainer:explain . refresh=true extra_sources=docs/runbook.md
```

The skill shows a plan and asks before writing anything. At the end it reports
what it wrote, what it skipped and why, and the gaps it found in your READMEs.

## Which folders get an explainer

Every folder with a README is covered. A folder gets its own explainer when it
is the repository root, has child folders with READMEs, or describes a feature,
an outside system, a scheduled job, costs or data people read. Smaller folders
appear as a row in their parent's "What's inside" table instead.

## Explainers you wrote yourself

The skill marks its own files with a footer on the last line:

```text
<!-- readme-explainer v1 source: src/intake/README.md fingerprint:sha256:… output:sha256:… -->
```

A file without that footer, or one changed since the skill wrote it, is treated
as yours and skipped. To hand a file back to the skill, delete or rename it.

## Works well with the Elephant-Goldfish Model

The best sources are READMEs that describe each folder's interface, rules and
side effects. The [Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model)
plugin's `/egm:egm-bootstrap` skill writes READMEs like that. README Explainer
doesn't need it, though; any README works.

## Limits

*   An explainer is only as accurate as its READMEs. If a README is out of date,
    so is its explainer.
*   It doesn't remove internal details such as hostnames or customer names.
    Read explainers before sharing them outside your team.
*   Large repositories start many agents. The plan shows the count before
    anything runs.

## Development

Run the tests:

```sh
python3 -m unittest discover -s tests
```

Try a local copy without installing it:

```sh
claude --plugin-dir /path/to/readme-explainer
```

## License

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

This project is not affiliated with or endorsed by Google.
