# LangGraph Design Patterns Used

> Engineering reference for anyone extending or debugging the platform.

## Why LangGraph (not LangChain, not raw OpenAI)

| Tech | Strength | Weakness | When we use it |
|------|----------|----------|----------------|
| Raw OpenAI API | Simple, single call | No state, no orchestration | One-shot Q&A bots (AceAchievers Portfolio B) |
| LangChain | Linear pipelines, lots of integrations | Hard to express loops + conditional branches | When you have a fixed N-step pipeline |
| **LangGraph** | Stateful graphs, conditional routing, HITL, retries | Steeper learning curve | **This platform — complex multi-step workflows** |

We deliberately avoid additional agent frameworks (AutoGen, CrewAI) on top — they add accidental complexity for our use case.

---

## The graph topology

```
Triage  ──confidence ≥ 0.5──>  Resolver  ──>  Supervisor
   │                              ▲              │
   │                              │              │ quality
   │                              │              │ < 0.7
   │                              └──retry──────┘
   │                                              │
   └──confidence < 0.5──┐                         │
                         ▼                         │
                    Human Escalation <──exhausted──┘
                         │
                         ▼
                        END
```

This is the **Triage / Resolver / Supervisor + HITL** pattern. It's the canonical agent topology for customer service automation. Variations:
- Add a **Memory** node before Triage (for long-term context)
- Add a **Branch** node between Triage and Resolver (for intent-specific specialists)
- Add **Parallel** branches when multiple downstream calls are independent

These are roadmap items (v1.2+).

---

## State management

We use a **TypedDict** for state, not a Pydantic BaseModel. Reasons:
- LangGraph's recommended pattern (lower overhead)
- `Annotated[list, add_messages]` reducer handles message accumulation correctly
- Direct dict access in agents = less ceremony

Each vertical extends the base state by **subclassing** the TypedDict:
```python
class EducationState(BaseSupportState, total=False):
    parent_id: str | None
    student_id: str | None
```

`total=False` makes all fields optional — important because the graph mutates state incrementally as it flows through nodes.

---

## Conditional routing

LangGraph supports two routing styles:
1. **Static edges:** `graph.add_edge("a", "b")` — always go A→B
2. **Conditional edges:** `graph.add_conditional_edges("a", router_fn, {"x": "node_x", "y": "node_y"})` — `router_fn(state)` returns a key

We use **conditional edges after Triage and Supervisor**. The routing functions are pure (no side effects), making them trivial to unit test:

```python
def route_after_triage(state):
    if state["requires_human"] or state["confidence"] < 0.5:
        return "human_escalation"
    return "resolver"
```

**Pure routing functions are a feature, not a limitation.** They keep the graph's control flow explicit and reviewable.

---

## Tool calling

The Resolver agent uses OpenAI's function-calling API via our `MockLLMProvider` and `OpenAILLMProvider` adapters. The schema for each tool is **derived automatically** from Python type hints + docstrings — vertical authors don't write JSON schemas by hand.

```python
@tool
def lookup_subscription(user_email: str) -> dict:
    """Look up a parent's active subscription(s) by email address."""
    ...
```

Becomes (auto-generated):
```json
{
  "type": "function",
  "function": {
    "name": "lookup_subscription",
    "description": "Look up a parent's active subscription(s) by email address.",
    "parameters": {
      "type": "object",
      "properties": {"user_email": {"type": "string", "description": ""}},
      "required": ["user_email"]
    }
  }
}
```

This is in `core/agents/tools.py`. It works for `str / int / float / bool / list / dict` parameters — extend `_PY_TO_JSON` for new types.

---

## Human-in-the-loop (HITL)

LangGraph's `interrupt_before=["human_escalation"]` parameter pauses the graph **before** running the named node, persisting state in the checkpointer. The graph then waits for an external trigger to resume.

Flow:
1. Graph reaches `human_escalation` node → pauses (`interrupt_before`)
2. Our `/api/chat` SSE stream emits `{"type": "human_escalation", ...}` event
3. Customer-facing widget shows "escalated to team" message
4. Operator sees pending item in `/api/pending-human`
5. Operator submits decision via `/api/resume`
6. `core.api.main._PENDING_HUMAN` records the decision
7. Graph resumes from `human_escalation` node, which now reads `state["human_decision"]` and produces `final_response`

**In v1 we use `MemorySaver` checkpointer** (in-memory, per-process). For multi-instance deployments (Vercel cold starts), upgrade to Redis-backed checkpointer in v1.2.

---

## Supervisor retry loop

The Supervisor scores the Resolver's draft. If `quality_score < 0.7` AND `retry_count < 2`, the graph routes back to Resolver with `quality_feedback` injected into the system prompt — the Resolver sees what's wrong and tries again.

If `retry_count >= 2`, the graph escalates to human (we don't loop forever).

**Why the retry loop?** Single-shot LLM generation has high variance. The Supervisor pattern converts variance into a deterministic quality floor: we either ship a draft that meets the bar, or we hand off to a human. Customers get one of two acceptable outcomes; never a low-quality machine response.

---

## Streaming events

We emit 6 SSE event types per chat (`core/api/sse.py`):

| Event | Purpose | Frontend use |
|-------|---------|--------------|
| `thread` | Carries `thread_id` for multi-turn | Save to localStorage |
| `triage` | Shows agent classification | Render "✓ Detected intent: refund" |
| `tool_call` | LLM requesting tool execution | Render "🔧 Looking up subscription..." |
| `tool_result` | Tool returned data | (Optional) hide or show snippet |
| `token` | Streaming response tokens | Append to bubble (typewriter effect) |
| `citations` | Sources used | Render source pills |
| `done` | Stream ended | Final formatting + analytics |

Frontend (`deploy/aceachievers/widget.js`) shows the Agent thinking process inline — a deliberate UX choice to differentiate from "magic black box" chatbots.

---

## LangGraph quirks worth knowing

1. **Async-first:** Always use `ainvoke` / `astream` / `astream_events`. Sync versions exist but are second-class.
2. **`astream_events(version="v2")`** is the new event API; v1 events have different schemas. Don't mix.
3. **State mutations are dict-merge, not replace.** Returning `{"intent": "x"}` from a node merges into state, doesn't replace it.
4. **The `add_messages` reducer is special.** It appends to the messages list rather than replacing — required for conversation history.
5. **Checkpointer required for `interrupt_before`.** Without a checkpointer, the graph can't pause.
6. **`config={"configurable": {"thread_id": ...}}`** is mandatory for any checkpointed invocation.

---

## When NOT to use LangGraph

If your workflow is **single-call Q&A** (no tools, no state, no branching), use the raw OpenAI API — LangGraph is overkill.

AceAchievers Portfolio B (parent concierge FAQ bot) is a good example of "didn't need LangGraph." This platform is what came next when the FAQ bot hit complexity ceiling.

See the ADR in `aceachievers/portfolio/articles/ADR-001-retrieval-stack.md` for the parallel decision on RAG.
