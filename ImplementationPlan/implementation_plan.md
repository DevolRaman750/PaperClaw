# Stateful Queen Adapter Architecture Plan

This document outlines the step-by-step implementation plan for building a highly efficient, "Patch-based" Queen Adapter that acts as a bridge between an external Builder Platform and the local Hive agent framework.

## 1. Goal Description

The objective is to implement an API adapter layer (the "Queen Adapter") that handles agent updates via high-efficiency JSON Patches (deltas) instead of full file generations. This minimizes LLM token consumption and generation latency. The Adapter will maintain local state of the agent's graph, merge incoming patches from the external LLM, and forward the fully compiled JSON graph to Hive's build tools to instantly overwrite the underlying Python files.

---

## 2. Implementation Steps

### Step 2.1: Define Data Models (Pydantic / TypeScript)
First, define strict validation schemas for the incoming patches. The external LLM must adhere to these schemas.
- **`AgentPatchRequest`**: The root payload containing `agent_id`, `metadata_updates`, `node_updates`, and `edge_updates`.
- **`NodeUpdate`**: Requires `node_id`, `action` (`add`, `modify`, `remove`), and an optional `changes` dictionary.
- **`EdgeUpdate`**: Requires `source`, `target`, and `action`.

### Step 2.2: Implement the State Store
The Adapter needs a fast, simple way to retrieve the "Base State" (the DraftGraph schema) of any agent.
- **Approach**: Create a local directory `adapter_state/` or use a Document DB (MongoDB/Postgres JSONB).
- **Format**: Store the JSON under keys like `agent_{agent_id}_v{version}.json`.
- **Workflow**: When an agent is initialized, save `v1`. Each time a patch is successfully processed and built by Hive, bump the version and save `v2`.

### Step 2.3: Build the Patch Merge Logic Engine
This is the core compute of the Adapter. It must safely apply patches without crashing.
- **Node Modification**: Iterate through the existing graph's `nodes` array. If an update matches a `node_id`, merge the dictionaries recursively.
- **Node Addition**: Append to the `nodes` array.
- **Edge Mutability**: When an `edge_update` arrives with `action: remove`, find and remove the matching `{source, target}` pair in the `edges` array.
- **Validation**: After merging, run the entire resulting JSON through a `DraftGraphValidator` to ensure no required fields sit empty.

### Step 2.4: Integrate with Hive Building Tools
Once the Adapter has cleanly merged the JSON into a valid `DraftGraph` object, it needs to trigger the Hive scaffolding tools programmatically.
1. Use `subprocess` or direct Python imports (if the adapter is Python) to call the `save_agent_draft()` logic.
2. Call `confirm_and_build()` to dissolve decision nodes.
3. Execute `initialize_and_build_agent(agent_name, nodes, _draft=patched_json)` to physically scaffold `exports/<agent_name>/agent.py`.

---

## 3. Edge Cases to Handle

> [!WARNING]
> You must build defensive logic in the Adapter for these specific failure modes.

1. **Orphaned Edges**: If the patch deletes a Node (e.g., node `check-priority`), the Adapter must automatically clean up any edges in the `edges` array where `source` or `target` was `check-priority`. The LLM might forget to explicitly delete the edges.
2. **Concurrent Edits**: If two updates hit the API at the exact same millisecond, they will cause a "Lost Update" race condition. **Fix**: Use optimistic locking (e.g., the patch must include `parent_version: 1`) or a queue system.
3. **Hallucinated Node References**: The LLM creates an edge mapping from a node that doesn't exist. **Fix**: Your post-merge validator must verify that all `source` and `target` strings in the edge list perfectly match an `id` in the nodes list.
4. **Invalid Tool Names**: The LLM might hallucinate a tool (e.g., `magical_search`). The merge will succeed, but Hive will throw an error later. **Fix**: The Queen Adapter should have a cached list of valid MCP tools to validate against before sending to Hive.

---

## 4. Trade-offs of this Method

> [!NOTE]
> Ensure stakeholders understand these architectural trade-offs.

### Advantages
- **90%+ Cost Reduction**: Token usage scales with the *size of the update*, not the *size of the agent*.
- **Speed**: Generating a 50-token JSON patch takes an LLM ~1.5 seconds. Generating an 8,000-token JSON graph takes ~45 seconds.
- **Less Code Hallucination**: Because the LLM isn't rewriting the whole graph, it can't accidentally "forget" or alter an unrelated node during the rewrite.

### Disadvantages
- **Complexity of the Merger**: You are now responsible for maintaining the "Patch Merge Engine". It is much easier to just ask the LLM for a full file than to write reliable JSON dictionary-merging code handling add/update/delete arrays.
- **Drift**: If a developer manually edits `exports/agent/agent.py` in their IDE, the Queen Adapter's "State Store JSON" will be out of sync. Patches will be applied to old data, overwriting the developer's manual work. **Fix**: Treat the Queen Adapter as the absolute source of truth. Manual file edits are volatile and will be lost.

---

## 5. User Review Required

Does this general architecture meet your needs for the Builder platform? Let me know if you would like me to actually begin writing the **Node.js/Python code** for the adapter implementation (Step 2.3 Merge Engine is usually the trickiest part), or if you just needed this design blueprint!
