# Notion Voice CoPilot – Agents Config

This branch introduces **Voice AI Agents** built for personal productivity and reflection inside the Notion Voice CoPilot framework. Each agent runs as a conversational service optimized for natural, friendly, and low-friction interactions.

## Agents in This Branch

### 1. Journaling Companion – *Juno*

A warm, casual “friend” who helps you reflect on your day through short voice conversations.

### 2. To-Do Assistant – *Jot*

A quick and helpful personal assistant for managing to-do lists by voice.

---

## Directory Structure

```
Agents/
├── Journaling Companion.json    # Agent definition for Juno
├── Journaling Companion.md      # Prompt for Juno
├── To-Do Assistant.json         # Agent definition for Jot
├── To-Do Assistant.md           # Prompt for Jot
```

---

## Setup

### Create Agents in Ultravox (Console)

Follow these steps once per agent (first Juno, then Jot):

1. **Open Ultravox Console → Agents** (Dashboard → *Agents*).
2. **New Agent** → click **New Agent**.
3. **Name & System Prompt**

   * **Name:** Use the agent’s name (`Juno` or `Jot`).
   * **System Prompt:** Paste from the corresponding JSON’s `systemPrompt`.

4. **Voice & Other Configurations**

   * Pick a voice.
   * Use the JSON files to fill in other values (e.g., join timeout, VAD settings).
5. **Test** → Click **Test Agent** to start/stop a call.


**Reference link:** [Agent Quickstart – Ultravox Docs][1]

---

## Running the Agents

Use the created **Agent IDs** in your Voice App configuration. These IDs connect the Notion Voice CoPilot service to the Ultravox agents you’ve set up.

[1]: https://docs.ultravox.ai/gettingstarted/quickstart/agent-console "Agent Quickstart - Ultravox Docs"
