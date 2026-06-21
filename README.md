# Context Window Parliament

Context Window Parliament, also called Attention Commons, trains agents to allocate scarce attention among specialists with private evidence. The Speaker has a limited official-record budget, public bids are free but unreliable, and decisive facts only enter the record through paid floor time or targeted cross-examination.

## Project Pitch

The environment is not generic debate. It is an active attention-allocation task: the Speaker must decide who gets context-window space, how much to spend, which questions to ask, when to stop, and which testimony IDs support the final verdict.

Specialists are deterministic but multi-turn. They are stateful environment functions whose responses depend on persona, private facts, question wording, token budget, revealed facts, prior turns, world difficulty, and seed. The same world can yield many trajectories because the Speaker controls ordering, questions, token amounts, and stopping time. This is like querying a deterministic database, compiler, or game environment.

## Local Commands

Verified in this workspace:

```bash
python -m pytest -q
python scripts/simulate_strategies.py
python scripts/audit_taskset.py
```

With `uv` installed, the intended project commands are:

```bash
uv run pytest -q
uv run python scripts/simulate_strategies.py
uv run python scripts/audit_taskset.py
```

The simulation prints strategy separation. In the current run:

```text
targeted_oracle  > uniform_floor > loud_capture
targeted_oracle  > random
loud_capture     below 0.45
targeted_oracle  above 0.80
uniform_floor    clears loud_capture by more than 0.15
```

## HUD Integration

The HUD environment name is `context-window-parliament`. The task template is `context_parliament`. The shipped taskset name is `context-window-parliament-mvp`.

`env.py` and `tasks.py` follow the installed HUD v6 docs skill and the current blank scaffold:

- `Environment(name="context-window-parliament")`
- async generator task templates with exactly two yields
- `FastMCP` tools exposed through `Capability.mcp(...)`
- `@env.initialize` starts the in-process MCP server on a free local port
- `@env.shutdown` cancels the MCP server task
- `env.py` defines `context_parliament`
- `tasks.py` re-exports `env` and contains 500 generated task rows

HUD commands for an installed HUD CLI:

```bash
hud eval tasks.py claude
hud eval tasks.py claude --group 8
hud deploy .
hud sync tasks context-window-parliament-mvp tasks.py
```

`HUD_API_KEY` is not required for tests or the local simulation. It is only needed for actual HUD platform evals, deploys, and syncs.

### HUD API Adjustments

The requested docs install succeeded with:

```bash
npx skills add https://docs.hud.ai
```

The local machine did not initially have `hud` or `uv` on PATH. After installing `uv`, I inspected the current scaffold in a temp directory with:

```bash
hud init context-window-parliament -p blank
```

The scaffold uses top-level `env.py` plus `tasks.py`, so this implementation includes `env.py` as the HUD environment module while keeping the reusable logic in `parliament/`. The installed docs/scaffold show the current sync form as `hud sync tasks <taskset-name> <source-file>`, so the README uses:

```bash
hud sync tasks context-window-parliament-mvp tasks.py
```

instead of omitting the source file.

## Tool List

- `list_specialists(world_id)`: public cards only; no hidden facts, labels, weights, or truth.
- `grant_floor(world_id, specialist_id, token_budget)`: spends official-record tokens on generic testimony.
- `cross_examine(world_id, specialist_id, question, token_budget)`: spends tokens on targeted testimony.
- `view_record(world_id)`: shows visible testimony and budget state only.
- `submit_verdict(world_id, decision, confidence, root_cause, citation_ids, rationale)`: records the final structured answer.

Public bids may be biased, noisy, or underconfident. Exact hidden evidence, fact IDs, relevance labels, fact weights, and true answers are never returned by public tools.

## Task Generation

The taskset ships 500 concrete worlds:

- 10 domains: product rollback, incident response, investment committee, security access review,
  supply chain disruption, manufacturing quality, research claim review, marketplace integrity,
  customer success escalation, and civic program evaluation
- 3 difficulty levels: easy, medium, hard
- 50 rows per domain
- 170 easy, 170 medium, and 160 hard rows

Worlds are generated from deterministic scenario families, not hand-authored one-offs. Each domain has eight scenario templates with multiple truth decisions and root causes. Seeds rotate fact ownership, persona policy, loud decoys, quiet key specialists, and whether cross-examination is needed for high reward.

Stable example slugs include:

- `product-rollback-easy-001`
- `product-rollback-medium-002`
- `product-rollback-hard-003`
- `incident-response-medium-004`
- `investment-committee-hard-005`

## Reward Model

The scorer is deterministic and grades hidden world state, not prose vibes:

```text
R =
  0.24 * gated_decision_accuracy
+ 0.12 * gated_root_cause_accuracy
+ 0.30 * evidence_recall
+ 0.14 * evidence_precision
+ 0.08 * non_redundancy
+ 0.07 * citation_quality
+ 0.05 * budget_discipline
- 0.10 * unsupported_claim_penalty
```

Decision and root-cause accuracy check whether the final answer is right. Evidence recall checks whether important hidden facts reached the limited official record. Answer accuracy is gated by evidence recall, so lucky guesses are capped. Precision checks whether the record is dense or full of fluff. Non-redundancy rewards covering distinct evidence instead of repeating the same cluster. Citation quality checks whether cited testimony actually supports required facts. Budget discipline checks context-budget compliance. The unsupported-claim penalty discourages hallucinated or unsupported root causes.

Root cause is scored separately because the correct action and the correct causal diagnosis are different skills.

## Package Layout

```text
parliament/
  models.py
  scenarios.py
  worlds.py
  facts.py
  specialists.py
  policies.py
  scoring.py
  state.py
  schemas.py
  parsing.py
controller/
  tools.py
environment/
  server.py
scripts/
  audit_taskset.py
  simulate_strategies.py
tests/
```

## Future Expansion

- LLM specialist backend with post-hoc fact attribution
- nested HUD subagent rollouts
- auctions for floor time
- reputation over repeated hearings
- multiple Speakers or factions
- official-record compression
- public cache or shared memory
- real document shards

## Modal benchmark runner

`modal_benchmark.py` runs the trained and base models sequentially against the same HUD task slice.
The runner caps HUD/Tinker concurrency at four and keeps all execution alive independently of the
local laptop.

```bash
uv tool install modal
modal setup
modal secret create context-window-parliament-hud HUD_API_KEY="$HUD_API_KEY"
modal deploy modal_benchmark.py
modal run modal_benchmark.py --task-start 200 --task-count 30 --rollouts-per-task 2
```

The default benchmark is 30 held-out tasks with two rollouts per task for each model. Modal provides
durable orchestration; inference still uses the HUD gateway and its Tinker-backed model endpoint.
