# mrveiss.github.io

The landing page served at **https://mrveiss.github.io/**.

It exists because GitHub Pages serves the user root *only* from a repository with
this exact name. A project repository always serves under its own path — which is
why AutoBot's site lives at [`/AutoBot-AI/`](https://mrveiss.github.io/AutoBot-AI/),
and why the root returned 404 until this repository had a page in it.

## What it points to

| | |
|---|---|
| [**AutoBot-AI**](https://github.com/mrveiss/AutoBot-AI) | Self-hosted, agentic AI you own — voice and chat, vision-driven browser and computer control, visual workflows, human-in-the-loop approvals, multi-user RBAC, a knowledge graph. [Site](https://mrveiss.github.io/AutoBot-AI/) |
| [**Claude-Dev-Skills**](https://github.com/mrveiss/Claude-Dev-Skills) | Claude Code skills encoding *how to work* — exploring before building, planning, reviewing, auditing, committing cleanly. Project-agnostic. |
| [**AutoBot-AI-Claude-dev-skills**](https://github.com/mrveiss/AutoBot-AI-Claude-dev-skills) | The same discipline, AutoBot-specific — issue implementation, PR mechanics, stack debugging. |

The three are not peers. AutoBot is the platform; the two skills marketplaces are
the working practice extracted from building it. The page's layout says so — one
primary, two derived — rather than presenting a row of three equal cards.

## Source of truth is elsewhere

`index.html` here is a **deployed copy**. It is authored in
[`AutoBot-AI/site/mrveiss.github.io/`](https://github.com/mrveiss/AutoBot-AI/tree/Dev_new_gui/site/mrveiss.github.io),
where it gets review and CI like anything else.

To change the page:

1. Edit it there, in a pull request.
2. After that merges, copy `index.html` into this repository and push.

**The copy is manual on purpose.** This is the first thing a visitor sees, and a
change reaching it without a human reading the diff is a worse failure than a page
that is a few minutes stale.

## The theme does not style the landing page

`index.html` carries no YAML front matter, so Jekyll copies it verbatim instead of
wrapping it in a layout. Its palette, type scale and theme handling are taken from
`AutoBot-AI/docs/index.html` so the root and the project site read as one property.

`_config.yml` sets a theme for any Markdown page added later, so such a page has a
consistent frame rather than arriving unstyled. If `index.html` ever gains front
matter it **will** start being wrapped by that layout — the one change that would
silently alter the page.

## Licence

Apache-2.0 · © 2026 mrveiss
