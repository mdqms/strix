---
name: llm-agent-mcp-config
description: Audit how an app wires LLMs, agents, and MCP servers — unconstrained tool access, prompt-injection sinks, untrusted MCP servers, and secrets in agent config
---

# LLM / Agent / MCP Configuration

Apps increasingly embed LLM agents and connect to MCP servers. The risk is rarely
the model itself; it is the **wiring**: what tools the agent can call, what
untrusted text reaches its context, and which MCP servers it trusts. This skill is
about the configuration and glue, complementing the packaged
`vulnerabilities/llm_prompt_injection` and `agentic_system_security` knowledge.
White-box scans.

## What to look for

1. **Over-powered tools behind an LLM.** An agent that can run shell, read/write
   the filesystem, make arbitrary HTTP calls, or execute SQL, driven by text that
   includes untrusted input. Map every tool the agent exposes and ask: if an
   attacker controls part of the prompt, what can they make it do?
2. **Prompt-injection sinks.** Untrusted content (user input, fetched web pages,
   emails, retrieved documents, tool output) concatenated into the system/user
   prompt with no separation or isolation. The classic path: RAG/retrieved text →
   prompt → a tool call.
3. **Untrusted MCP servers.** `mcp-servers.json` / client config pointing at a
   remote MCP server you don't control, or a `stdio` server launched from a
   repo-local script. MCP tool descriptions enter the model's context — a hostile
   server can inject instructions ("tool-poisoning"). Enumerate configured servers
   and their trust.
4. **Secrets / no human gate.** LLM/provider API keys in config or committed;
   agents that take irreversible actions (payments, deletes, sends) with no
   confirmation step.

## Procedure

```bash
# agent/LLM/MCP wiring and tool grants
grep -rniE 'mcp|tool_?call|function_?call|system_?prompt|openai|anthropic|langchain|llm' \
  --include=*.py --include=*.js --include=*.ts --include=*.json . 2>/dev/null | head -40
# MCP server configs
find . -name 'mcp*servers*.json' -o -name '.mcp.json' 2>/dev/null
cat ~/.strix/mcp-servers.json 2>/dev/null   # (the target's own config, if in scope)
# untrusted text flowing into prompts
grep -rniE 'prompt\s*[+=].*(request|input|body|message|content|document|page)' . 2>/dev/null | head -20
```

## Reporting

- `create_vulnerability_report`, one per concrete injection-to-impact path or
  dangerous tool grant. "Uses an LLM" is not a finding; "untrusted web content
  reaches an agent that can run shell" is.
- `evidence_state`: `reproduced` if you drove an injection to a real tool action;
  `static_trace` if you traced the wiring. Name the injection source and the sink
  tool in `technical_analysis`.

---
Adapted from gstack CSO (MIT); see ../NOTICE.
