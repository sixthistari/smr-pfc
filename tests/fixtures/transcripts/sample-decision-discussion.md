# Discussion: Chat Interface Framework Selection

**Date**: 2026-02-20
**Participants**: Justin Hume (EA), Jake (Enterprise Systems Manager)

---

**Justin**: I've been looking at our options for the EA workbench chat interface. We need something that supports MCP tool calling natively, can handle streaming responses, and is easy to deploy in Azure. The main candidates are Chainlit, Gradio, and building something custom with FastAPI + WebSockets.

**Jake**: What's the key constraint? Is it time, capability, or the Azure integration?

**Justin**: All three matter, but the biggest one is MCP support. The ADO wiki integration and our element registry both need to be tool-callable from the chat. Gradio doesn't have MCP support at all — it's a different paradigm. FastAPI custom would work but we'd spend 2 weeks on plumbing before writing any EA logic.

**Jake**: So Chainlit is the obvious answer then?

**Justin**: Yes, and there are a few other reasons. Chainlit has Literal AI backing so it's commercially supported, Apache 2.0 licence so no compliance issues, and it has built-in SQLAlchemy session persistence which we need for the provenance tracking. The session URLs are stable which is important for linking from DevOps work items back to the conversation that created them.

**Jake**: What about the Azure deployment? Container Apps?

**Justin**: Yes, we'd run it as a Docker container in Azure Container Apps. The Anthropic client talks to Azure AI Foundry via the standard Azure endpoint, not the Anthropic API endpoint. That keeps everything inside the tenant.

**Jake**: Alright. Are there any downsides to Chainlit we should document?

**Justin**: The main risk is that it's community-maintained — commercially backed but still a relatively small team. If it stagnates, we'd need to replace the UI layer. That's manageable because the chat layer is thin — the actual EA logic lives in the agent runner and the staging pipeline. Swapping the UI framework shouldn't take more than a week.

**Jake**: So we're deciding: use Chainlit as the chat interface for the EA workbench.

**Justin**: Correct. And we use SQLAlchemy + SQLite for session persistence in the prototype, with the option to move to PostgreSQL if we need concurrent access when Mahtab joins.

---

*Decision confirmed: Chainlit selected as the EA Workbench chat interface framework. Azure Container Apps for deployment. SQLite session persistence for prototype.*
