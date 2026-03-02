# EA Workbench — Build Instructions for Claude Code

Read this file first. Then read REQUIREMENTS.md, STANDARDS.md, ARCHITECTURE-DECISIONS.md, and SYSTEM-PROMPT.md before writing any code.

---

## Build Approach

### Phase 0 — Foundation (Build First)

Build in this exact order. Each step must work before moving to the next.

**Step 1: Project scaffold**
- Initialise uv project with pyproject.toml
- Create directory structure per STANDARDS.md
- Install core dependencies: chainlit, anthropic, claude-agent-sdk, pydantic, aiosqlite, pyyaml, lxml
- Create `.python-version` (3.12)
- Create `.gitignore` (Python defaults + .staging/exports/ + .agents/runs/)

**Step 2: Pydantic models**
- Define all shared data models in `src/ea_workbench/models/`:
  - `elements.py`: Element, Relationship, Capability, ElementCapability
  - `manifests.py`: RunManifest (matching the JSON schema in REQUIREMENTS.md §6.2)
  - `config.py`: AgentConfig, WorkbenchConfig (matching config.yaml structure)
  - `extraction.py`: StagedEntity, StagedRelationship, ExtractionFile
  - `work.py`: StagedWorkItem, Provenance, SessionRecord (REQUIREMENTS.md §3C, §3D, §3F)
  - `motivation.py`: Need, Requirement, Engagement, Driver, Outcome (REQUIREMENTS.md §3A)
  - `practice.py`: Principle, Standard, Decision, NFR, Idea, Strategy (REQUIREMENTS.md §3B)
- These models are the contract between all components. Get them right first.

**Step 3: Element registry**
- Create SQLite schema (REQUIREMENTS.md §3.2)
- Implement `registry/db.py`: connection manager, schema migration on first run
- Implement `registry/queries.py`: CRUD operations, the views (orphan elements, domain summary), search by name/type/domain
- Write tests against in-memory SQLite

**Step 4: Chainlit chat app (minimal)**
- Create `chat/app.py` with Chainlit entry point
- Load system prompt from `.agents/prompts/chat-agent.md`
- Connect to Anthropic Messages API (with Azure AI Foundry endpoint support)
- Implement basic message handler: user message → LLM call → response
- Configure SQLAlchemy session persistence with SQLite backend (stable session URLs for provenance)
- No MCP yet, no slash commands — just prove the chat loop works with persistence

**Step 5: ADO MCP integration**
- Configure Chainlit MCP for ADO server with both `wiki` and `work-items` domains enabled
- Implement `chat/handlers.py`: on_mcp_connect, tool call processing
- Test: user asks about wiki content, agent reads a page via MCP, responds with grounded answer
- Implement Wiki Write Protocol: diff presentation for updates, collapsible preview for creates, confirmation gate before writes

**Step 6: Element registry MCP**
- Implement `registry/mcp_server.py`: a lightweight local MCP server wrapping registry queries
- Tools: `search_elements`, `get_element`, `list_capabilities`, `query_sql` (parameterised, read-only)
- Connect to Chainlit alongside ADO MCP
- Test: user asks "what elements are in the safety domain?", agent queries registry

**Step 7: Batch agent runner**
- Implement `agents/base.py`: Protocol defining the agent contract
- Implement `agents/runner.py`: loads config.yaml, resolves agent by ID, runs via Agent SDK, writes manifest
- Test with a trivial agent (echo agent that reads a file and writes a summary)

**Step 8: First real agent — ADR Generator (Use Case 12)**
- Implement `agents/adr_generator.py`
- System prompt in `.agents/prompts/adr-generator.md`
- Input: context file (transcript/notes) + existing ADR index
- Output: draft ADR markdown + staged entities
- Test against fixture transcript

**Step 9: Slash commands**
- Implement `chat/commands.py`: `/run`, `/status`, `/staging`, `/health`, `/triage`, `/wrap`
- `/run` triggers batch agent runner, streams status to chat
- `/status` reads recent manifests from `.agents/runs/`
- `/staging` counts files across `.staging/entities/`, `.staging/relationships/`, `.staging/work/`, `.staging/sessions/`
- `/triage` presents staged work items for review; approved items pushed to DevOps via ADO MCP work-items domain
- `/wrap` generates session summary, persists to `.staging/sessions/`, confirms to user

**Step 10: Entity and work artefact extraction integration**
- Implement `extraction/extractor.py`: writes entity staging YAML files
- Implement `extraction/work_staging.py`: writes work artefact staging YAML with provenance
- Implement `extraction/schemas.py`: Pydantic validation for all staging formats
- Add extraction protocol to ADR Generator agent prompt
- Verify staged entities and work items validate against schemas
- All staged items carry provenance blocks (session ID, conversation summary, trigger)

**Step 11: Practice artefact registers and motivation layer bootstrap**
- Create `_index.yaml` templates for all practice artefact types (principles, standards, decisions, NFRs, ideas, strategies)
- Create need/requirement YAML schema templates for `needs/by-domain/` and `requirements/by-domain/`
- Create engagement record template for `needs/engagements/`
- Configure "PFC Link" custom field on DevOps work item types (manual config, documented in README)

### Phase 1 — Governance Agents (Build Second)

After Phase 0 is working end-to-end:

- Wiki Integrity Agent (UC 13) + ADO pipeline YAML
- Design-Time Guardrail Agent (UC 7) + ADO pipeline YAML
- Spec Decomposition Agent (UC 6)
- Bootstrap capability model YAML from existing wiki content
- Staging review workflow (approve/reject commands)
- ArchiMate XML export script (`extraction/export.py`) — including motivation layer types for Orbus syndication
- Provenance blocks validated on all staged artefacts
- Context-bootstrap handler for DevOps work item launch (`/chat?init=devops-item&id=NNN`)
- Motivation layer capture functional in chat (engagement records, needs, requirements)

### Phase 2 — Remaining Agents (Build Third)

- Transcript Classifier (UC 1)
- Weekly summary agent (aggregates session records into planning template)
- Multi-Format Export (UC 14)
- Use-Case Assessment (UC 2)
- Capability Intelligence (UC 4)
- Orbus syndication pipeline (ArchiMate XML validated for iServer import format)
- Stakeholder Comms (UC 5)
- Remaining agents (UC 3, 8, 9, 10, 11, 15)
- Practice artefact analytics (idea→decision conversion, risk mitigation tracking)

---

## Key Implementation Notes

### Chainlit Configuration

```toml
# .chainlit/config.toml
[project]
name = "EA Workbench"
enable_telemetry = false

[features]
prompt_playground = false
multi_modal = false

[features.mcp.stdio]
enabled = true
allowed_executables = ["npx", "uvx", "uv", "node"]

[UI]
name = "EA Workbench"
default_theme = "dark"
```

### Azure AI Foundry Routing

The Chainlit chat app uses the Anthropic Python client with Azure endpoint:

```python
from anthropic import AsyncAnthropic

# When CLAUDE_CODE_USE_FOUNDRY=1 is set, the Agent SDK routes through Azure.
# For the Messages API (chat), configure the client directly:
client = AsyncAnthropic(
    base_url=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    # Azure AI Foundry handles auth via managed identity or API key
)
```

Note: Verify the exact Azure AI Foundry configuration for Anthropic models. The endpoint URL and auth mechanism may differ from standard Azure OpenAI. Check Azure AI Foundry documentation for Claude model deployment specifics.

### Agent SDK Invocation Pattern

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_batch_agent(
    agent_config: AgentConfig,
    prompt: str,
    workspace: str,
) -> RunManifest:
    """Execute a batch agent and return its manifest."""
    run_id = str(uuid.uuid4())[:8]
    start = time.monotonic()
    
    options = ClaudeAgentOptions(
        system_prompt=load_prompt(agent_config.system_prompt),
        allowed_tools=agent_config.tools,
        cwd=workspace,
        model=agent_config.model,
    )
    
    result_text = ""
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "result"):
            result_text = message.result
    
    duration = time.monotonic() - start
    
    # Parse structured output from result
    # Write manifest
    # Return manifest
```

### MCP Server for Element Registry

The custom MCP server is a local stdio process that wraps SQLite queries. Keep it minimal:

```python
# Conceptual — actual MCP server implementation may use 
# the MCP Python SDK or a simpler stdio protocol
TOOLS = {
    "search_elements": {
        "description": "Search architectural elements by name, type, or domain",
        "parameters": {
            "query": "Search term (matches name or description)",
            "domain": "Optional domain filter",
            "archimate_type": "Optional ArchiMate type filter",
        }
    },
    "get_element": {
        "description": "Get full details of an element by ID",
        "parameters": {"element_id": "Element identifier"}
    },
    "list_capabilities": {
        "description": "List capabilities, optionally filtered by level or domain",
        "parameters": {
            "parent_id": "Optional parent capability ID",
            "max_level": "Maximum hierarchy depth to return"
        }
    },
    "find_orphan_elements": {
        "description": "Find elements not linked to any capability",
        "parameters": {}
    },
    "domain_summary": {
        "description": "Get element counts by domain, type, and status",
        "parameters": {"domain": "Optional domain filter"}
    }
}
```

### Dynamic System Prompt Loading

At Chainlit session start, the system prompt is assembled from the template plus live data:

```python
@cl.on_chat_start
async def on_start():
    # Load prompt template
    template = Path(".agents/prompts/chat-agent.md").read_text()
    
    # Load dynamic sections
    capabilities = load_capability_summary("capabilities/capability-model.yaml", max_depth=2)
    glossary = load_glossary_summary("vocabulary/enterprise-glossary.yaml", max_terms=50)
    wiki_tree = await get_wiki_tree_via_mcp(max_depth=2)
    
    # Assemble
    system_prompt = template.replace("{{CAPABILITY_MODEL_SUMMARY}}", capabilities)
    system_prompt = system_prompt.replace("{{GLOSSARY_SUMMARY}}", glossary)
    system_prompt = system_prompt.replace("{{WIKI_TREE_SUMMARY}}", wiki_tree)
    
    cl.user_session.set("system_prompt", system_prompt)
    cl.user_session.set("message_history", [])
```

---

## What NOT to Build

- **No authentication system** (single-user prototype; Chainlit's built-in auth for Phase 1)
- **No database migrations framework** (SQLite schema is simple; a single `CREATE TABLE IF NOT EXISTS` script suffices)
- **No API layer between chat and batch** (slash commands invoke the runner directly; no REST API)
- **No background task queue** (agent runs are foreground; async but not queued)
- **No custom CSS/theming** (Chainlit defaults; dark mode only)
- **No WebSocket or SSE infrastructure** (Chainlit handles this internally)
- **No logging infrastructure** (Python logging module + structured JSON to files)
- **No monitoring/alerting** (read the manifest files; Phase 1 concern)
