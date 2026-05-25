---
name: research
description: Run web searches and documentation lookups, compare options, and compile findings into
  a structured report for user approval before any implementation begins.
argument-hint: "[topic]"
---


# Research Skill

## When to Activate

- Evaluating a new trading strategy or prediction method
- Comparing external APIs or data providers
- Selecting a library, ML model, or infrastructure tool
- Assessing viability of a new Polymarket domain
- Any architectural or refactoring decision requiring external evidence

## Workflow

### 1. Determine Research Mode

| Mode             | When                                                                 | Depth                         |
|------------------|----------------------------------------------------------------------|-------------------------------|
| **Quick Lookup** | Simple, scoped question (e.g. does this library support X?)          | 1–2 searches, short summary   |
| **Deep Dive**    | Major decision (new strategy, model selection, architectural change) | Multi-source, full comparison |

### 2. Scan Codebase First (when recommending libraries or tools)

Before searching externally, check what is already in use:
- Review `pyproject.toml` for existing dependencies
- Check `src/` for patterns, utilities, or integrations that may already solve the problem
- Avoid recommending something already in the stack or incompatible with NautilusTrader

Skip this step for strategy, model, or domain research.

### 3. Search External Sources (in order — stop when confident)

1. **Official docs** — vendor docs, SDK references, API specs (use Context7 or web fetch)
2. **GitHub** — existing implementations, open-source projects, community patterns
3. **Exa** — blog posts, academic papers, benchmarks
4. **PyPI / package registries** — maintenance status, download trends, compatibility

**Source credibility filter — prefer:**
- Official documentation and vendor references
- Repos with active maintenance and substantial community adoption
- Peer-reviewed papers or established technical blogs
- Discard: undated posts, anonymous forum opinions, marketing copy without evidence

### 4. Evaluate by Research Type

**API / Data Source**
- Endpoint structure, parameters, and response fields
- Rate limits, authentication, pricing, and free tier
- Coverage relevance to our Polymarket markets

**Library / Tool / Infrastructure**
- Relevance to the problem
- Strengths and weaknesses
- Maintenance status and compatibility with our stack (Python 3.14, uv, NautilusTrader)

**Strategy / Model / Prediction Method**
- What problem it solves and how
- Strengths and weaknesses vs. alternatives
- Fit with Polymarket's binary market structure

## Output Format

**Quick Lookup**
```
## Research Summary: <Topic>

Answer: <direct answer>
Source: <where this came from>
Recommendation: <what to do>
```

**Deep Dive**
```
## Research Report: <Topic>

### Problem
<One paragraph — what we're trying to solve and why>

### Options Compared (max 5)
| Option | Strengths         | Weaknesses     | Fit for Project | Explanation    |
|--------|-------------------|----------------|-----------------|----------------|
| name   | - s1 - s2 - s3    | - w1 - w2 - w3 | ★★★☆☆ (3/5)     | - e1 - e2\  e3 |      

### Findings (max 3)
- <most important finding>  
- <second finding> 
- <third finding>

### Recommendation
Pick: <option>
Why: <1–2 sentences citing specific evidence from the table above>
Trade-off: <what we give up by not choosing the runner-up>

Awaiting your approval before any handoff.
```
