# deadpath

Finds backtick-quoted path references in markdown docs that no longer resolve on disk.

## Install

```bash
pip install deadpath
```

## Usage

```bash
deadpath check ./docs
```

Exit code is `0` when clean, `1` when it finds dead paths, `2` when it couldn't run (bad
argument, unreadable config). `--format` controls output: `human` (default), `json`, or
`github` (workflow-command annotations for CI — see [action.yml](action.yml)).

## Real output

Run against a ~1,000-file personal Obsidian vault — a knowledge base *about* work that
mostly lives elsewhere, so this is close to a worst case for false positives:

```
$ deadpath check . --vault
Daily Notes/062726.md:23  .claude/commands/week.md  -- path does not exist
Gmail/Gmail Dashboard.md:61  Patterns/gmail-tracking.md  -- path does not exist
House/Home Inventory.md:12  assets/Trane_Warranty.pdf  -- path does not exist
Music/Dawn Mix Log.md:22  docs/pipeline/dawn-audio-to-midi-handoff.md  -- path does not exist
Music/README.md:21  scripts/mix_analyze.py  -- path does not exist
Projects/Portfolio Site/Overview.md:15  src/App.jsx  -- path does not exist
... (55 more)

68 dead paths found.
```

Almost every one of those is a *mention*, not a broken link — the vault's notes describe
projects whose files live in other trees entirely. That is the failure mode, and it is
why the section below says vaults are the wrong target.

And against [`fiberplane/drift`](https://github.com/fiberplane/drift), a real, actively
maintained repo, run cleanly (no vault mode, no config):

```
$ deadpath check .
CLAUDE.md:44  src/parse/Language.zig  -- path does not exist
docs/DECISIONS.md:43  src/auth/provider.ts  -- path does not exist
docs/DESIGN.md:188  commands/lint.zig  -- path does not exist
...

17 dead paths found.
```

`CLAUDE.md:44` is the headline result: it references src/parse/Language.zig, which does
not exist — drift's actual `src/` holds markdown.zig, symbols.zig, target.zig, and
vcs.zig. A genuinely stale path in the agent instructions of the nearest thing this tool
has to a competitor, found by running it, not by construction.

### Validation, measured against four real corpora

| Corpus | markdown files | findings |
|---|---|---|
| [remarkjs/remark-validate-links](https://github.com/remarkjs/remark-validate-links) | 26 | 0 |
| [lycheeverse/lychee](https://github.com/lycheeverse/lychee) | 66 | 0 |
| [fiberplane/drift](https://github.com/fiberplane/drift) | 17 | 14 (1 genuine, 13 illustrative examples in its own design docs) |
| A 1,000-file personal Obsidian vault | ~1000 | ~68 (a live corpus; the count moves as notes are edited) |

## What it deliberately does not check

deadpath only reads **backtick-quoted paths mentioned in prose** — the sentence "see
src/auth/provider.ts for the token flow," not a markdown link. That is a narrow, specific
wedge, chosen because two other tools already own the adjacent ground better than a
generalist tool would:

- **[remark-validate-links](https://github.com/remarkjs/remark-validate-links)** owns
  markdown **link targets** — `[text](path)` syntax. deadpath deliberately does not parse
  that syntax at all; if your docs are full of real markdown links, that's the right tool,
  and it belongs alongside deadpath rather than instead of it.
- **[fiberplane/drift](https://github.com/fiberplane/drift)** owns **code-anchored semantic
  staleness** — you bind a spec to a symbol via frontmatter, and drift uses tree-sitter AST
  fingerprints to detect when the underlying code changes shape, even if the path itself
  still resolves. That is a different, deeper problem than "does this path exist," and it
  requires annotating your docs to use.

deadpath's actual wedge is **prose paths link checkers never see, with zero setup** — no
frontmatter, no annotation, nothing to opt individual references into. Point it at a
directory and it works, at the cost of only ever answering one narrow question: does this
path exist.

## Known limitations

- **Bracket-containing paths are never checked.** `pages/[id].tsx` (Next.js / Nuxt /
  SvelteKit dynamic routes) and `[Name]`-style placeholders are indistinguishable by
  string alone, so both are excluded. This only produces missed findings, never false
  alarms.
- **Illustrative example paths in design docs will be flagged.** A doc demonstrating
  syntax with a hypothetical src/auth/provider.ts looks identical, as a string, to a real
  reference. This is exactly why drift shows 14 findings for one genuine stale path — most
  of the rest are its own docs walking through worked examples. Use `exclude_globs` (below)
  on docs that are mostly examples.
- **Personal knowledge vaults are the wrong primary target.** A vault is a knowledge base
  *about* work that mostly lives elsewhere — other repos, Google Drive, a Task Board — so
  most of its path-shaped text is a mention, not a link, and was never going to resolve.
  `--vault` mode exists and works (it also resolves Obsidian wikilinks and their implicit
  `.md`), but a repo, where a path really is supposed to point at a file in the same tree,
  is the audience this tool is actually built for.

## Design principle: precision over coverage

A false positive costs more than a missed finding — it's what gets a tool uninstalled. So
a candidate is guilty until proven a path, not the other way around: it must show positive
evidence of being one. An explicit path-like prefix — `./`, `../`, or a Windows drive
letter (`C:\`) — is accepted on its own. Everything else must *also* have a directory
component: a recognized file extension or a first path segment that matches a real
top-level directory in the project being scanned is only positive evidence once a `/`
already appears somewhere in the candidate. That directory-component requirement is why
`and/or`, `TCP/IP`, `input/output`, and bare filenames like `CLAUDE.md` are never flagged
— with no idiom blocklist to write or maintain.

## Config reference

Drop a `.deadpath.toml` in the directory you scan. All keys are optional; the defaults
scan every markdown file with no exclusions.

```toml
[deadpath]
scan_globs = ["**/*.md"]         # default: every markdown file, recursively
exclude_globs = []                 # fnmatch patterns; "*" crosses "/"
allowlist_prefixes = []            # path prefixes to never flag, e.g. staging areas
vault_mode = false                 # Obsidian mode: resolve wikilinks + implicit .md
```

| Key | Type | Default | Effect |
|---|---|---|---|
| `scan_globs` | list of glob patterns | `["**/*.md"]` | Which files get scanned. Uses `pathlib.Path.glob` semantics (`*` does not cross `/`, `**` does). |
| `exclude_globs` | list of glob patterns | `[]` | Files to skip after `scan_globs` matches them. Uses `fnmatch` semantics (`*` *does* cross `/`) — a deliberate dialect difference from `scan_globs`, not a bug. |
| `allowlist_prefixes` | list of path prefixes | `[]` | Candidates whose (normalized) path starts with one of these are never reported, even if they don't resolve — useful for known-future paths or staging areas. |
| `vault_mode` | boolean | `false` | Also equivalent to the `--vault` CLI flag. Resolves paths relative to the vault root, reads `[[wikilinks]]`, and tries the implicit `.md` extension Obsidian applies to extensionless links. |

An advanced fifth key, `extensions`, overrides the built-in list of recognized file
extensions used by the positive-evidence gate above; the default list covers the common
source, doc, and asset extensions and rarely needs changing.

## GitHub Action

```yaml
- uses: <owner>/deadpath@v1
  with:
    path: docs
```

Runs `deadpath check` with `--format github`, so findings show up as inline annotations on
the diff. See [action.yml](action.yml).

## License

MIT — see [LICENSE](LICENSE).
