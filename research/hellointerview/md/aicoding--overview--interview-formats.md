###### Overview

# Interview Formats

The two main formats you'll encounter: platform-based (CoderPad, HackerRank) and BYOE (Bring Your Own Environment).

AI-enabled coding interviews come in two flavors, and knowing which one you're walking into matters a lot. The tools available to you, the types of problems you'll face, and even the strategies that work best are all different depending on the format.

1. **Structured** (CoderPad, HackerRank) where the company provides the environment, AI tools, and a defined problem structure
2. **Open-Ended** where you use your own IDE, your own AI tools, and build from scratch while sharing your screen

Often you can tell which one you're walking into from the invite itself. A link to a browser-based environment they've set up points to structured. Being told to use your own machine and share your screen points to open-ended.

Ask your recruiter which one it is. If they don't know, push until you get an answer.

### Structured

In a structured interview, the company provides the coding environment and the AI assistant. You open a browser, log into CoderPad or HackerRank, and everything is already there. The codebase, the AI chat panel, and the problem statement are all loaded before you write a line.

These interviews follow a defined problem arc. The typical format runs three phases: start by fixing a bug in the existing code, implement a new feature on top of the working codebase, then optimize for larger inputs or edge cases. Knowing that structure early lets you pace yourself. You know roughly what's coming and can avoid burning all your time on phase one.

[Meta](/blog/meta-ai-enabled-coding) is the most well-known example, in part because they were among the first major companies to standardize it and their CoderPad setup has become the reference point candidates compare everything else to. Their interview uses CoderPad with a selection of AI models (GPT-4o, GPT-5, Claude Sonnet/Haiku, Gemini, Llama). [LinkedIn](/blog/linkedin-ai-enabled-coding) also uses CoderPad, with their own model selection and the same multi-phase structure. Uber runs on HackerRank with a pre-set repository, where you're expected to navigate existing code before making changes.

Not every structured round is build-and-optimize. A few companies hand you a pull request instead and ask you to use the AI to work through its description and diff and decide whether you'd approve it. Same skills, different shape.

The downside is that you're locked into whatever tools they give you. If the AI assistant isn't great (and candidates at Meta and Uber have consistently reported it being worse than what they practiced with), you can't switch to something better. You work with what you've got.

Both Meta and LinkedIn offer practice sessions on their platform before the real interview. Always take advantage of these. The CoderPad AI interface has quirks you won't encounter in your normal IDE, and spending 30 minutes getting comfortable with it beforehand is time well spent.

Run one of these in our in-browser sandbox so the multi-phase, constrained-AI format feels familiar before the real thing.

| Problem |  |  |
| --- | --- | --- |
| Battleship | Easy |  |
| Inventory Packer | Easy |  |
| Spell Checker | Easy |  |
| Card Game | Medium |  |
| Friend Recommender | Medium |  |
| Maze Solver | Medium |  |
| Route Planner | Medium |  |
| Task Scheduler | Medium |  |
| Word Container | Medium |  |
| Connect Four | Hard |  |
| Kitchen Orders | Hard |  |
| Maximize Unique Characters | Hard |  |
| Nonogram Solver | Hard |  |

### Open-Ended

You use your own IDE, your own AI tools, and share your screen. This format is more common at companies that want to see how you actually work day-to-day. They're not interested in whether you can adapt to a constrained platform, they want to know what your real workflow looks like.

[Shopify](/blog/shopify-ai-enabled-coding) is the canonical example: they tell you to use whatever you'd normally use at work. The specifics vary across companies that use this format. Some mandate AI usage and score it explicitly (Canva). Some have you build features incrementally against test cases (Rippling). Some vary by team, from structured DSA to open repo work (Adobe).

The upside is that you're working with tools you already know. You don't have to learn an unfamiliar interface under pressure, and you can fall back on workflows you've built over time.

The downside is that the interviewer sees *everything*. Your prompts, your fumbling between tools, that moment where you accidentally paste something into the wrong window. There's no hiding behind a platform. Your workflow is completely visible, which means it needs to actually be good.

The problems here are greenfield. You might get an empty repository and a problem statement, or just a README describing what to build. You start from nothing and build a working application. The emphasis shifts from "can you navigate existing code" to "can you design and build something from scratch with AI as your accelerator."

This tends to require candidates to use many of the skills we cover in our [Low Level Design content](/learn/low-level-design/in-a-hurry/introduction), by showing that you can design software that is both functional and extensible, even if the majority of the actual implementation is handled by the AI.

Ready to try it? Pick a problem, build it in your own editor with your own AI tools, and submit for a hire verdict with a full breakdown.

## What to ask your recruiter

Before your interview, get clear answers to these questions:

**What's the format?**

* Structured or Open-Ended? If the recruiter says "AI-enabled" but doesn't specify, ask directly.
* Is there starter code or are you building from scratch?

**If it's structured**

* Which platform (CoderPad, HackerRank)?
* Is there a practice environment you can access beforehand?
* How many phases does the interview have?

**If it's open-ended**

* Are there restrictions on which AI tools you can use?
* Does the company have a preference (some suggest Cursor specifically)?
* Will you need to push code to a repository, or is screen share enough?

Recruiters are usually happy to give you format details. They want you to succeed. If yours is vague, try asking "what should I have set up on my machine before the interview?" That question tends to surface the specifics.
