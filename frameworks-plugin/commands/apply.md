---
name: apply
description: Apply a specific named framework to your context, walking through it step by step.
argument-hint: "<framework-name> <your context>"
allowed-tools: Read, Glob, Grep, Skill
---

# Apply a specific framework

Raw input: **$ARGUMENTS**

The first token (`$1`) is the framework the user wants; the rest is the context to apply it to.

1. Resolve `$1` to the matching skill in this plugin (accept loose names — e.g. "rumelt", "kernel" → `rumelt-kernel`; "ooda" → `ooda-loop`; "kano" → `kano-model`; "para" → `para-method`; "jtbd" → `jobs-to-be-done`; "lno" → `lno-prioritization`; "nsm"/"north star" → `north-star-metric`; "voss"/"negotiation" → `tactical-empathy`). If it's ambiguous, ask which of the closest 2-3 they mean.
2. Invoke that Skill (`frameworks-plugin:<skill>`) and follow its step structure faithfully — do not improvise the framework from memory.
3. Apply it to the provided context. Where the context is missing information the framework needs, state explicit, labeled assumptions and ask for the key missing inputs.
4. Produce the framework's output template, then flag the weakest step and suggest one complementary framework for a second pass.

If no recognizable framework name is given, run `/frameworks-plugin:list` behavior to show options, or `/frameworks-plugin:recommend` if they described a situation instead.
