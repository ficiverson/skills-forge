# Export Formats

`skills-forge export` converts a `.skillpack` archive into a format suitable for a specific AI platform. This lets you author your skill once and deploy it everywhere.

---

## Usage

```bash
# Pack your skill first
skills-forge pack output_skills/development/python-tdd

# Export to different formats
skills-forge export python-tdd-0.1.0.skillpack -f system-prompt
skills-forge export python-tdd-0.1.0.skillpack -f gpt-json
skills-forge export python-tdd-0.1.0.skillpack -f bedrock-xml
skills-forge export python-tdd-0.1.0.skillpack -f mcp-server -o ./server/
```

---

## system-prompt (default)

Plain text system prompt. Works with any LLM API that accepts a `system` parameter.

Output: `<name>.system-prompt.txt`

```
You are a specialist assistant for python-tdd.
Use this skill when writing Python code using TDD.
Triggers on: pytest, test-first, red-green-refactor, unit test.

## Instructions
...
```

---

## gpt-json

OpenAI Custom GPT JSON configuration. Import into [platform.openai.com](https://platform.openai.com).

Output: `<name>.gpt.json`

```json
{
  "name": "python-tdd",
  "description": "Use when writing Python with TDD...",
  "instructions": "..."
}
```

**To use:**

1. Go to [platform.openai.com/gpts](https://platform.openai.com/gpts)
2. Create a new GPT → Configure
3. Paste the JSON or copy `instructions` into the Instructions field

---

## gem-txt

Google Gemini Gem instructions. Import at [gemini.google.com](https://gemini.google.com).

Output: `<name>.gem.txt`

**To use:**

1. Open Gemini → Gems → Create a Gem
2. Paste the contents of the `.gem.txt` file into the Instructions field

---

## bedrock-xml

AWS Bedrock agent prompt XML template, compatible with Bedrock Prompt Management and Agent advanced prompts.

Output: `<name>.bedrock.xml`

**To use:**

1. AWS Console → Amazon Bedrock → Prompt management → Create prompt
2. Choose "Text", select a Claude model
3. Paste the `<system>` block content into the System prompt field

Or for Bedrock Agents advanced prompts:

1. AWS Console → Amazon Bedrock → Agents → your-agent → Edit
2. Under "Advanced prompts", enable the "Orchestration" template override
3. Paste the full XML into the template editor

---

## mcp-server

Self-contained Python MCP (Model Context Protocol) server module that exposes the skill as a tool.

Output: `<name>_mcp_server.py`

**To use:**

```bash
# Install the MCP library
pip install mcp

# Run the server
python python-tdd_mcp_server.py
```

Then add it to your MCP host configuration (Claude Desktop, etc.).

---

## mistral-json

Mistral AI system-prompt JSON format.

Output: `<name>.mistral.json`

---

## gemini-api

Google Gemini Developer API prompt format (distinct from Gemini Gems).

Output: `<name>.gemini-api.json`

---

## openai-assistants

OpenAI Assistants API JSON format for use with the Assistants endpoint.

Output: `<name>.assistants.json`

---

## All formats at once

```bash
for fmt in system-prompt gpt-json gem-txt bedrock-xml mcp-server; do
  skills-forge export my-skill-0.1.0.skillpack -f $fmt -o exports/
done
```
