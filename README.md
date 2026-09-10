# mrveiss.github.io

The landing page served at **https://mrveiss.github.io/** — authored here, deployed
from here. This repository is the source of truth; there is no copy step and no
other place to edit it.

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

## What is in here

```
index.html    the landing page — hand-authored, no front matter
_config.yml   Jekyll config: sitemap plugin, theme for future Markdown, README excluded
robots.txt    crawler policy, including named AI agents
llms.txt      llmstxt.org summary for agents
README.md     this file — excluded from the build, not served
```

## Deploying

Push to `main`. GitHub Pages builds and serves it; there is nothing else to do.

**Push once, then leave it alone for 20+ minutes.** Pages deploys are exclusive and
the queue is slow. Do **not** `POST /pages/builds` to hurry one along — that cancels
the deploy already in flight, and the API then reports the cancellation as
`"Page build failed."` with a null detail, indistinguishable from a real content
failure. `gh run list` is the only view that shows whether a runner actually holds
the job. Two of three deploys on the first day of this repository died to that nudge.

`/pages/builds/latest` is a positional alias, not a handle: a newer build re-points
it, so anything watching it can silently follow two different builds and never see
the first one's failure. Key a watcher to the run id.

## The theme does not style the landing page

`index.html` carries no YAML front matter, so Jekyll copies it verbatim instead of
wrapping it in a layout. Its palette, type scale and theme handling are taken from
`AutoBot-AI/docs/index.html` so the root and the project site read as one property.

`_config.yml` sets a theme for any Markdown page added later, so such a page has a
consistent frame rather than arriving unstyled. If `index.html` ever gains front
matter it **will** start being wrapped by that layout — the one change that would
silently alter the page.

## How quickly drift is detected

The freshness check does **not** catch a stale page immediately, and the figure is
worth knowing before trusting a green tick.

Measured on the first `page_build`-triggered run, decomposed:

```
Pages deploy completes -> page_build event fires    14m 49s
page_build fires       -> a runner picks up the job 24m 47s   (outlier, see below)
job runs                                                 4s
                                                    -----------
                                                    39m 38s
```

The middle term is not typical. Across the other freshness runs a runner was
assigned in **3s, 3s, 22s and 4m08s** — so a normal end-to-end detection is closer
to **~15 minutes**, dominated by how long GitHub takes to deliver the `page_build`
event. The 39m38s figure is the worst observed, not the expected one.

Both numbers are one-sample-ish and neither is controlled from this repository.

**What that means in practice:** a divergence lasting a few minutes will usually not
be caught. The incident that prompted this check lasted ~40 minutes and would have
been caught, but only just. This is a personal landing page and that trade is
deliberate — stated here so nobody reads a passing check as proof the site is
currently correct.

The `cron: '7,37 * * * *'` backstop is slower still: GitHub sheds roughly three in
four of those, giving observed gaps of 2h02m and 3h49m.

## Analytics

Google Analytics `G-ZV9XT0XSWR`, the same property as the AutoBot site, so the two
report into one stream rather than splitting traffic.

Consent Mode v2 with everything denied by default; the defaults are set **before**
`gtag.js` loads, which is load-bearing rather than stylistic. The visitor's answer is
stored under `ab-consent` — the same key the `/AutoBot-AI/` page uses. Both are the
same origin, so a visitor who answers on either is not asked twice. **Do not rename
that key**: a new one asks the same person a second time for one decision.

## Licence

Apache-2.0 · © 2026 mrveiss
