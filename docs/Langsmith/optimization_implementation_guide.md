# Optimization Implementation Guide

## Quick Reference: Priority-Ordered Fixes

| Priority | Optimization                 | Time   | Impact              | Difficulty |
| -------- | ---------------------------- | ------ | ------------------- | ---------- |
| 🔴 P0     | Enable Prompt Caching        | 15 min | 98% prompt cost ↓   | Easy       |
| 🔴 P0     | Parallelize Specialist Calls | 2 hrs  | 47% latency ↓       | Medium     |
| 🟠 P1     | Reduce System Prompt         | 4 hrs  | 60% prompt tokens ↓ | Medium     |
| 🟠 P1     | Combine Translation          | 8 hrs  | 37% latency ↓       | Hard       |
| 🟡 P2     | Enable Streaming             | 2 hrs  | Better UX           | Easy       |
| 🟡 P2     | Model Optimization           | 4 hrs  | 30% cost ↓          | Medium     |

---

## P0: Enable Prompt Caching (15 minutes)

### Current Code Pattern
```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    temperature=None,
)
```

### Optimized Code
```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    temperature=None,
    model_kwargs={
        "extra_headers": {
            "anthropic-beta": "prompt-caching-2024-07-31"
        }
    }
)
```

### Implementation Notes
- ✅ Already configured in some traces (see 019c0716-9110)
- ⚠️ But `cache_read: 0` indicates it's not working
- 🔍 Verify prompt structure marks cacheable sections correctly
- 📦 Requires Langchain Anthropic >= 0.1.0

### How Anthropic Caching Works
```python
# Anthropic caches based on EXACT prefix match
# Mark static content for caching:

messages = [
    {
        "role": "system",
        "content": "Long system prompt here...",
        "cache_control": {"type": "ephemeral"}  # Mark for caching
    },
    {
        "role": "user", 
        "content": "User query"  # Not cached, varies per request
    }
]
```

### Expected Results
- First call: 13,374 prompt tokens charged
- Subsequent calls within 5 minutes: ~200-300 prompt tokens charged
- **Cost reduction: 98%** on prompt tokens

---

## P0: Parallelize Specialist Consultations (2 hours)

### Current Sequential Pattern

**File:** `medical_board_tool.py` (assumed)

```python
async def consult_medical_board(patient_id, clinical_question, specialists):
    """Current implementation - SEQUENTIAL"""
    results = []
    
    for specialist in specialists:
        if specialist == "neurology":
            result = await consult_neurology(patient_id, clinical_question)
        elif specialist == "primary_care":
            result = await consult_primary_care(patient_id, clinical_question)
        # ... etc
        
        results.append(result)
    
    return combine_results(results)
```

**Problem:** Each specialist waits for the previous one
- Neurology: 20 seconds
- Primary Care: 18 seconds  
- **Total: 38 seconds**

### Optimized Parallel Pattern

```python
import asyncio
from typing import List, Dict

async def consult_medical_board(
    patient_id: str, 
    clinical_question: str, 
    specialists: List[str]
) -> Dict:
    """Optimized implementation - PARALLEL"""
    
    # Map specialist names to async functions
    specialist_functions = {
        "neurology": consult_neurology,
        "primary_care": consult_primary_care,
        "cardiology": consult_cardiology,
        "endocrinology": consult_endocrinology,
        # ... etc
    }
    
    # Create list of coroutines
    tasks = [
        specialist_functions[spec](patient_id, clinical_question)
        for spec in specialists
        if spec in specialist_functions
    ]
    
    # Execute all consultations in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any errors gracefully
    valid_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Error consulting {specialists[i]}: {result}")
        else:
            valid_results.append(result)
    
    return combine_results(valid_results)
```

### Expected Results
- Neurology: 20 seconds  }
- Primary Care: 18 seconds } → Run in parallel
- **Total: max(20, 18) = 20 seconds**
- **Time saved: 18 seconds (47% faster)**

### Testing
```python
import asyncio
import time

async def test_parallel_consultations():
    start = time.time()
    
    result = await consult_medical_board(
        patient_id="test-123",
        clinical_question="Test question",
        specialists=["neurology", "primary_care"]
    )
    
    elapsed = time.time() - start
    print(f"Total time: {elapsed:.2f}s")
    assert elapsed < 25, f"Still too slow: {elapsed}s"
```

---

## P1: Reduce System Prompt Size (4 hours)

### Current Bloated Prompt (13,374 tokens)

**Problem areas:**
1. Verbose tool descriptions
2. Extensive specialist lists
3. Repeated instructions
4. In-prompt examples
5. Redundant guidelines

### Optimization Strategy

#### Before: Verbose Tool Description
```python
tools = [
    {
        "name": "get_patient_profile",
        "description": """
            Retrieve the complete health profile for a patient.
            
            Returns demographics, conditions, medications, and allergies.
            Use this when you need a comprehensive view of the patient's health record.
            
            Args:
                patient_id: The UUID of the patient.
            
            Returns:
                A formatted string with the patient's complete health profile.
        """,
        "input_schema": {...}
    }
]
```

#### After: Concise Tool Description
```python
tools = [
    {
        "name": "get_patient_profile",
        "description": "Get patient demographics, conditions, medications, allergies",
        "input_schema": {...}
    }
]
```

**Tokens saved per tool: ~50-80**  
**Total for 15 tools: 750-1,200 tokens saved**

#### Before: Inline Specialist List
```markdown
Available specialists:
- **Primary Care**: General medicine, preventive care, chronic disease management
- **Cardiology**: Chest pain, heart failure, arrhythmias, hypertension, cholesterol
- **Endocrinology**: Diabetes, thyroid, hormonal disorders, metabolic syndrome
- **Pulmonology**: Asthma, COPD, shortness of breath, chronic cough, sleep apnea
- **Neurology**: Headaches, seizures, dizziness, numbness, memory concerns
- **Gastroenterology**: Acid reflux, IBS, IBD, liver disease
- **Oncology**: Cancer screening, suspicious symptoms
- **Psychiatry**: Depression, anxiety, mood changes, sleep problems
- **Orthopedics**: Joint pain, arthritis, back pain, fractures
- **Nephrology**: Kidney disease, electrolyte imbalances
- **Dermatology**: Rashes, eczema, psoriasis, skin lesions
```

#### After: Reference-Based
```markdown
Available specialists: primary_care, cardiology, endocrinology, pulmonology, 
neurology, gastroenterology, oncology, psychiatry, orthopedics, nephrology, dermatology

Use `list_specialist_capabilities(specialist_name)` for detailed info.
```

**Tokens saved: 200-300**

#### Consolidated System Prompt Template

```python
SYSTEM_PROMPT = """You are a Medical Assistant.

## Core Functions
1. Answer health questions using patient tools
2. Extract and confirm new health information
3. Consult specialists for clinical questions
4. Explain in 6th grade language

## Key Rules
- Confirm before adding records
- Use appropriate specialists
- Never fabricate information
- Translate clinical terms

Patient ID: {patient_id}
Date: {current_date}
"""

# Store detailed instructions in separate retrieval system or tool descriptions
```

**Target: 3,000-4,000 tokens** (down from 13,374)

---

## P1: Combine Translation Step (8 hours)

### Current Two-Step Process

```python
# Step 1: Get specialist response (19.87s)
specialist_response = await specialist_chain.ainvoke({
    "clinical_question": question,
    "patient_context": context
})

# Step 2: Translate to plain language (13.08s)
translated = await translation_chain.ainvoke({
    "specialist_response": specialist_response
})

# Total: 32.95 seconds
```

### Option A: Single-Prompt Approach

```python
# Combined prompt instructs specialist to write plainly
specialist_prompt = """
You are a {specialty} specialist providing clinical guidance.

IMPORTANT: Write your response in plain language (6th grade reading level).
- Avoid medical jargon
- Explain terms simply
- Use bullet points
- Lead with most important info

Patient Context: {patient_context}
Clinical Question: {clinical_question}
"""

# Single call: ~18-20 seconds
response = await specialist_chain.ainvoke(...)
```

**Pros:**
- Saves 13 seconds
- Saves $0.012 per consultation
- Simpler architecture

**Cons:**
- May reduce quality of clinical assessment
- Less separation of concerns
- Harder to tune separately

### Option B: Streaming Translation

```python
async def consult_with_streaming_translation(question, context):
    """Generate and translate simultaneously"""
    
    # Start specialist generation
    specialist_stream = specialist_chain.astream({
        "question": question,
        "context": context
    })
    
    # As specialist generates, feed chunks to translator
    translated_chunks = []
    async for chunk in specialist_stream:
        # Stream translation in parallel
        translated = await translate_chunk(chunk)
        translated_chunks.append(translated)
        yield translated  # Stream to user immediately
    
    return "".join(translated_chunks)
```

**Pros:**
- Best perceived latency (user sees output immediately)
- Maintains separation of concerns
- Can still cache/optimize separately

**Cons:**
- More complex implementation
- Requires streaming support throughout stack
- Chunk-level translation may lose context

### Recommendation: Start with Option A

Simplest implementation with immediate 37% latency improvement. Can add streaming later if needed.

---

## P2: Enable Streaming (2 hours)

### Current Synchronous Response

```python
# User waits 35 seconds for complete response
response = await medical_assistant.ainvoke(user_message)
return response
```

### Streaming Implementation

```python
async def stream_response(user_message):
    """Stream chunks as they generate"""
    async for chunk in medical_assistant.astream(user_message):
        if chunk.get("content"):
            yield chunk["content"]
```

### FastAPI Endpoint Example

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/chat/stream")
async def chat_stream(message: str):
    async def generate():
        async for chunk in stream_response(message):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

### Expected User Experience

**Before (Synchronous):**
```
[User sends message]
[Wait 35 seconds...]
[Complete response appears]
```

**After (Streaming):**
```
[User sends message]
[First words appear in 2-3 seconds]
[Response builds progressively]
[Complete in 35 seconds total, but user engaged throughout]
```

**Perceived latency reduction: 70-90%**

---

## P2: Model Optimization by Task (4 hours)

### Current Uniform Model Usage

All tasks use `claude-sonnet-4-20250514`:
- Medical Assistant: claude-sonnet-4
- Specialists: claude-sonnet-4  
- Translation: claude-sonnet-4

### Optimized Model Selection

```python
from langchain_anthropic import ChatAnthropic

# High-complexity clinical reasoning
specialist_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=2048
)

# Simple translation/formatting
translation_llm = ChatAnthropic(
    model="claude-haiku-4-20250320",  # 70% cheaper
    max_tokens=1024
)

# Entry point routing
assistant_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=512  # Just routing, doesn't need much
)
```

### Cost Comparison (per 1M tokens)

| Model           | Input | Output | Use Case                         |
| --------------- | ----- | ------ | -------------------------------- |
| Claude Opus 4   | $15   | $75    | Reserved for complex cases       |
| Claude Sonnet 4 | $3    | $15    | Clinical reasoning, specialists  |
| Claude Haiku 4  | $1    | $5     | Translation, formatting, routing |

### Expected Savings

**Current:** Translation with Sonnet
- 1,273 input tokens @ $3/1M = $0.00382
- 523 output tokens @ $15/1M = $0.00785
- **Total: $0.0117**

**Optimized:** Translation with Haiku
- 1,273 input tokens @ $1/1M = $0.00127
- 523 output tokens @ $5/1M = $0.00262
- **Total: $0.0039**

**Savings per consultation: $0.0078 (67% reduction on translation)**

---

## Monitoring and Validation

### Add Timing Instrumentation

```python
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        
        # Log to monitoring system
        log_timing(
            function=func.__name__,
            duration=elapsed,
            args=args
        )
        
        return result
    return wrapper

@timing_decorator
async def consult_specialist(patient_id, question):
    ...
```

### Performance Metrics to Track

```python
metrics = {
    "assistant_latency": [],           # Entry point
    "specialist_latency": {},          # By specialist type
    "translation_latency": [],         # Translation step
    "total_consultation_time": [],     # End-to-end
    "prompt_tokens": [],               # Track caching effectiveness
    "completion_tokens": [],           # Track verbosity
    "cache_hit_rate": 0.0,            # % of cached prompts
    "parallel_speedup": 0.0,          # Time saved by parallelization
}
```

### Success Criteria

After implementing optimizations:

- ✅ Prompt tokens < 5,000 (currently 13,374)
- ✅ Cache hit rate > 80% (currently 0%)
- ✅ Total consultation time < 15s (currently 35s)
- ✅ Cost per consultation < $0.025 (currently $0.075)
- ✅ Time to first token < 3s (currently 4-20s)

---

## Rollout Plan

### Phase 1: Quick Wins (Week 1)
- Day 1: Enable prompt caching
- Day 2: Test caching effectiveness
- Day 3: Implement parallel specialist calls
- Day 4-5: Test and validate parallel execution

**Expected improvements:** 60% cost reduction, 40% latency reduction

### Phase 2: Prompt Optimization (Week 2)
- Day 1-2: Audit and reduce system prompts
- Day 3: Update tool descriptions
- Day 4-5: Test and validate

**Expected improvements:** Additional 30% prompt token reduction

### Phase 3: Architecture Changes (Week 3-4)
- Week 3: Combine translation or implement streaming
- Week 4: Model optimization by task type
- Test and validate

**Expected improvements:** Additional 20% latency reduction, 20% cost reduction

### Phase 4: Polish (Week 5)
- Implement comprehensive monitoring
- Add response caching for common queries
- Performance tuning based on real data

---

## Testing Checklist

Before deploying optimizations:

- [ ] Load test with 100 concurrent requests
- [ ] Verify cache hit rates > 80%
- [ ] Confirm parallel execution working
- [ ] Validate response quality unchanged
- [ ] Check error handling for parallel failures
- [ ] Monitor token usage patterns
- [ ] Verify cost tracking accuracy
- [ ] Test edge cases (1 specialist, 5 specialists, etc.)
- [ ] Validate streaming works end-to-end
- [ ] Confirm model selection logic correct

---

## Risk Mitigation

### Prompt Caching Risks
**Risk:** Cache invalidation issues  
**Mitigation:** Use cache TTL of 5 minutes, version system prompts

### Parallel Execution Risks
**Risk:** One specialist failure breaks entire flow  
**Mitigation:** Use `return_exceptions=True`, handle gracefully

### Translation Combination Risks
**Risk:** Quality degradation in specialist responses  
**Mitigation:** A/B test, keep translation option available

### Model Optimization Risks
**Risk:** Haiku insufficient for translation quality  
**Mitigation:** Run quality evaluation on 100 samples before rollout

---

## Expected Final Results

### Performance Improvements
- **Latency:** 35s → 10-12s (71% faster)
- **Prompt tokens:** 13,374 → 2,500-3,000 (78% reduction)
- **Cost:** $0.075 → $0.020-0.025 (67% cheaper)
- **Time to first token:** 4-20s → 1-3s (75% faster)

### User Experience Improvements
- Immediate feedback (streaming)
- Faster consultations
- Same quality responses
- Lower operational costs

### ROI
- Implementation time: 2-3 weeks
- Cost savings: 67% per consultation
- If 1,000 consultations/month:
  - Current cost: $75/month
  - Optimized cost: $25/month
  - **Savings: $50/month = $600/year**
- **Payback period: < 1 month**