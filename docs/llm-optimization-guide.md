# LLM Agent Optimization Guide

Practical patterns extracted from optimizing a LangChain tool-calling agent from ~35s to ~12-15s actual / ~5s perceived latency.

---

## 1. Cache LLM Instances (Singleton by Config)

**Problem:** Every agent/specialist instantiation creates a new LLM client, which includes HTTP connection setup, auth validation, etc.

**Solution:** Cache instances by `(provider, model, max_tokens, streaming)` tuple.

```python
from langchain_core.language_models import BaseChatModel

_llm_cache: dict[tuple, BaseChatModel] = {}

def get_chat_model(
    provider: str = None,
    model: str = None,
    max_tokens: int = None,
    streaming: bool = False,
) -> BaseChatModel:
    settings = get_settings()
    provider = provider or settings.llm_provider
    model = model or settings.model_name
    max_tokens = max_tokens or settings.max_tokens

    cache_key = (provider, model, max_tokens, streaming)
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    # ... create llm based on provider ...
    _llm_cache[cache_key] = llm
    return llm
```

**Impact:** Eliminates redundant client creation. Especially important when multiple components (agent + specialists) create LLM instances.

---

## 2. Use a Faster/Cheaper Model for Sub-Agents

**Problem:** If your main agent delegates to specialist/sub-agents, those sub-agents don't need the most powerful (and slowest) model. A reasoning model like Sonnet or Gemini Pro is overkill for a focused specialist prompt.

**Solution:** Add separate config for sub-agent models. Use a fast model (Haiku, GPT-4o-mini, Gemini Flash) for sub-agents.

```python
# config.py
class Settings(BaseSettings):
    # Main agent model
    llm_provider: str = "anthropic"
    model_name: str = "claude-sonnet-4-20250514"

    # Sub-agent model (faster/cheaper)
    specialist_provider: Optional[str] = None   # falls back to llm_provider
    specialist_model: Optional[str] = None      # falls back to model_name
```

```python
# sub_agent.py
class SubAgent:
    def __init__(self):
        settings = get_settings()
        self.llm = get_chat_model(
            provider=settings.specialist_provider,
            model=settings.specialist_model,
        )
```

```env
# .env
LLM_PROVIDER=anthropic
MODEL_NAME=claude-sonnet-4-20250514
SPECIALIST_PROVIDER=anthropic
SPECIALIST_MODEL=claude-3-5-haiku-20241022
```

**Impact:** Sub-agent calls drop from ~18s to ~3-5s. The fast model is sufficient for focused, well-prompted tasks.

**Gotcha:** Double-check model ID strings. Anthropic uses `claude-3-5-haiku-20241022`, NOT `claude-haiku-3-5-20241022`. A wrong model name returns an API error that your agent may silently swallow.

---

## 3. Trim System Prompts Aggressively

**Problem:** Large system prompts (10,000+ tokens) increase latency on every LLM call. They also reduce prompt cache hit rates.

**Solution:** Cut system prompts to the minimum needed. Move role-specific instructions inline. Remove examples that the model already handles well.

**Before (~13,000 tokens):**
```
You are a Medical Assistant...
[500 lines of instructions, examples, edge cases, formatting rules]
```

**After (~950 tokens):**
```python
SYSTEM_PROMPT = """You are a Medical Assistant helping a patient manage their health information.

## Capabilities
1. **Answer Questions** about their health using profile and search tools.
2. **Gather Information**: Extract new conditions, medications, or allergies from conversation. Always confirm before adding to records.
3. **Consult Specialists**: For clinical questions, consult the appropriate specialist tool.
4. **Web Search**: Use `search_medical_web` for up-to-date drug info, guidelines, or research. Cite sources.

## Guidelines
- Explain medical terms in plain language (6th grade reading level)
- Translate specialist responses to patient-friendly language
- Confirm before adding records; ask clarifying questions if details are unclear
- Never fabricate information
"""
```

**Rules of thumb:**
- If the model does it correctly without the instruction, remove the instruction
- Tool descriptions (in the tool schema) replace most "how to use X" instructions
- Bullet points > paragraphs
- One concise guideline > three examples of the same thing

**Impact:** Reduces input tokens per call, improving latency and cost. Improves prompt cache hit rates.

---

## 4. Skip Structured Output for Sub-Agents

**Problem:** `llm.with_structured_output(PydanticModel)` uses function calling under the hood, which adds schema tokens to every request and forces the model to produce JSON. If you then convert that structured output back to plain text anyway, it's pure overhead.

**Solution:** If the consumer of the sub-agent output is another LLM (the main agent), just return plain text. The main agent can interpret natural language directly.

**Before:**
```python
class SpecialistResponse(BaseModel):
    assessment: str
    recommendations: List[Recommendation]
    red_flags: List[str]
    guidelines_referenced: List[str]
    confidence: str
    limitations: str

class SubAgent:
    def __init__(self):
        self.structured_llm = self.llm.with_structured_output(SpecialistResponse)

    def consult(self, context, question) -> SpecialistResponse:
        return self.structured_llm.invoke(messages)
```

**After:**
```python
class SubAgent:
    def consult(self, context, question) -> str:
        # Plain text prompt asks for the same structure, but as markdown
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=(
                f"{formatted_context}\n\n## Question\n\n{question}"
                "\n\nBe concise. Respond with:\n"
                "1. **Assessment** (2-3 paragraphs)\n"
                "2. **Red Flags** (if any)\n"
                "3. **Top 3 Recommendations** with priority\n"
                "4. **Guidelines Referenced**\n"
                "5. **Limitations**"
            )),
        ]
        response = self.llm.invoke(messages)
        return response.content
```

**When to keep structured output:** When the consumer is your application code (not another LLM) and needs to parse fields programmatically (e.g., storing in a database, rendering in a UI with specific field mapping).

**Impact:** Saves ~1-2s per sub-agent call from reduced schema overhead and faster generation.

---

## 5. Stream the Final Response

**Problem:** The user waits for the entire agent pipeline (tool calls + final synthesis) before seeing any output. With a 3-call pipeline, this can be 30+ seconds of blank screen.

**Solution:** Execute tool calls synchronously (they must complete), then stream only the final LLM response token-by-token.

```python
from typing import Generator

class Agent:
    def chat_stream(
        self,
        message: str,
        conversation_history: list[dict] = None,
        on_tool_start: callable = None,
    ) -> Generator[str, None, None]:
        """Tool calls block, then final response streams."""
        messages = self._build_messages(message, conversation_history)
        response = self.llm_with_tools.invoke(messages)

        max_iterations = 5
        iteration = 0

        # Tool loop (blocking)
        while response.tool_calls and iteration < max_iterations:
            iteration += 1
            tool_results = self._execute_tools_parallel(
                response.tool_calls, on_tool_start
            )

            messages.append(response)
            for i, tc in enumerate(response.tool_calls):
                messages.append(ToolMessage(
                    content=tool_results[i]["output"],
                    tool_call_id=tc.get("id"),
                ))

            if on_tool_start:
                on_tool_start("__thinking__")
            response = self.llm_with_tools.invoke(messages)

        # Stream the final response
        if iteration > 0 and not response.tool_calls:
            for chunk in self.llm_with_tools.stream(messages):
                text = self._extract_chunk_text(chunk)
                if text:
                    yield text
        else:
            yield self._extract_chunk_text(response) or str(response.content)

    def _extract_chunk_text(self, chunk) -> str:
        """Handle both string and list content blocks."""
        if isinstance(chunk.content, str):
            return chunk.content
        elif isinstance(chunk.content, list):
            parts = []
            for block in chunk.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        return ""
```

**Streamlit integration:**
```python
# Use st.write_stream() which handles generators natively
if hasattr(agent, "chat_stream"):
    response = st.write_stream(
        agent.chat_stream(user_prompt, history, on_tool_start=callback)
    )
else:
    response = agent.chat(user_prompt, history)
    st.markdown(response)
```

**Impact:** User sees first tokens ~5s after submission instead of waiting 30s+ for the full response. Total wall-clock time is the same, but perceived latency drops dramatically.

**Note on the tool status callback:** The `on_tool_start` callback lets you update the UI while tools execute (e.g., "Consulting cardiologist..."). Pass a sentinel like `"__thinking__"` between tool loops so the UI can show "Synthesizing..." during the final LLM call.

---

## 6. Parallelize Tool Calls

**Problem:** When the LLM returns multiple tool calls in one response (e.g., "look up medications AND consult cardiology"), they execute sequentially by default.

**Solution:** Use `ThreadPoolExecutor` to run independent tool calls concurrently. Skip the overhead for single tool calls.

```python
from concurrent.futures import ThreadPoolExecutor

def _execute_tools_parallel(self, tool_calls, on_tool_start=None):
    """Execute tool calls concurrently. Single call = no thread overhead."""
    if len(tool_calls) == 1:
        result = self._execute_tool_call(tool_calls[0])
        return [{"tool_call_id": tool_calls[0].get("id"), "output": result}]

    results = [None] * len(tool_calls)

    def _run(idx, tc):
        if on_tool_start:
            on_tool_start(tc.get("name", ""))
        results[idx] = {
            "tool_call_id": tc.get("id"),
            "output": self._execute_tool_call(tc),
        }

    with ThreadPoolExecutor(max_workers=min(len(tool_calls), 4)) as executor:
        futures = [executor.submit(_run, i, tc) for i, tc in enumerate(tool_calls)]
        for f in futures:
            f.result()  # Wait for all to complete, propagate exceptions

    return results
```

**Key details:**
- `max_workers=min(len(tool_calls), 4)` caps thread count to avoid overhead
- Results array preserves order (important: tool results must match tool call order)
- Single tool call path avoids ThreadPoolExecutor overhead entirely
- Works with `ThreadPoolExecutor` (not `asyncio`) because LangChain tools are synchronous

**Impact:** When the agent calls multiple tools at once (e.g., `consult_medical_board` triggers 3 specialists), total time = max(individual times) instead of sum(individual times).

---

## 7. Enable Prompt Caching (Anthropic)

**Problem:** Repeated calls with the same system prompt (e.g., same agent prompt on every user message) re-process the entire prompt each time.

**Solution:** Enable Anthropic's prompt caching via the beta header. The system prompt and tool definitions are cached across calls.

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model=model,
    api_key=api_key,
    max_tokens=max_tokens,
    model_kwargs={
        "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}
    },
)
```

**Requirements:**
- System prompt must be >= 1024 tokens for caching to activate (2048 for Haiku)
- Prompt prefix must be identical across calls (same system prompt, same tool definitions)
- Cache TTL is 5 minutes; frequent calls within that window benefit most

**Impact:** Reduces input token processing time by up to 85% on cache hits. Most impactful for agents with large tool schemas.

---

## 8. Eliminate Redundant LLM Calls

**Problem:** Post-processing steps that use an LLM to transform output (e.g., "translate specialist response to patient-friendly language" as a separate LLM call) add an entire round-trip.

**Solution:** Push the transformation instruction into the producing LLM's prompt, or into the consuming LLM's prompt. Eliminate the middleware call.

**Before (3 LLM calls):**
```
Agent LLM -> Specialist LLM -> Translation LLM -> User
```

**After (2 LLM calls):**
```
Agent LLM -> Specialist LLM -> User
(Agent's system prompt says: "Translate specialist responses to plain language")
```

The main agent is already synthesizing a response after receiving tool results. Adding "translate to patient-friendly language" to its system prompt costs zero extra latency.

**Impact:** Eliminates one full LLM round-trip (~5-10s depending on model).

---

## Summary: Optimization Checklist

| Optimization | Latency Saved | Effort |
|---|---|---|
| Cache LLM instances | ~0.5s per duplicate | Low |
| Faster model for sub-agents | ~13-15s per sub-call | Low |
| Trim system prompts | ~1-3s per call | Medium |
| Skip structured output | ~1-2s per sub-call | Low |
| Stream final response | Perceived: ~20-25s | Medium |
| Parallelize tool calls | Varies (sum -> max) | Low |
| Prompt caching (Anthropic) | ~1-3s on cache hits | Low |
| Eliminate redundant LLM calls | ~5-10s per removed call | Medium |

## Architecture Pattern

```
User Message
    |
    v
[Main Agent LLM] (powerful model: Sonnet, GPT-4o, Gemini Pro)
    |
    |-- tool calls (parallel if multiple)
    |      |
    |      v
    |   [Sub-Agent LLM] (fast model: Haiku, GPT-4o-mini, Flash)
    |      returns plain text
    |
    v
[Main Agent LLM - streamed] (synthesize + translate to user language)
    |
    v
User sees tokens streaming
```

The main agent handles routing, synthesis, and user-facing language. Sub-agents handle domain-specific reasoning with a fast model. The final response streams to minimize perceived latency.
