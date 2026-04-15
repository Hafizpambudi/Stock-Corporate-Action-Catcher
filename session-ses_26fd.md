# Finding and Installing Skills

**Session ID:** ses_26fd25f27ffersXpZpBUrQ6mY3
**Created:** 4/15/2026, 3:06:42 PM
**Updated:** 4/15/2026, 3:17:12 PM

---

## User

# Find Skills

This skill helps you discover and install skills from the open agent skills ecosystem.

## When to Use This Skill

Use this skill when the user:

- Asks "how do I do X" where X might be a common task with an existing skill
- Says "find a skill for X" or "is there a skill for X"
- Asks "can you do X" where X is a specialized capability
- Expresses interest in extending agent capabilities
- Wants to search for tools, templates, or workflows
- Mentions they wish they had help with a specific domain (design, testing, deployment, etc.)

## What is the Skills CLI?

The Skills CLI (`npx skills`) is the package manager for the open agent skills ecosystem. Skills are modular packages that extend agent capabilities with specialized knowledge, workflows, and tools.

**Key commands:**

- `npx skills find [query]` - Search for skills interactively or by keyword
- `npx skills add <package>` - Install a skill from GitHub or other sources
- `npx skills check` - Check for skill updates
- `npx skills update` - Update all installed skills

**Browse skills at:** https://skills.sh/

## How to Help Users Find Skills

### Step 1: Understand What They Need

When a user asks for help with something, identify:

1. The domain (e.g., React, testing, design, deployment)
2. The specific task (e.g., writing tests, creating animations, reviewing PRs)
3. Whether this is a common enough task that a skill likely exists

### Step 2: Search for Skills

Run the find command with a relevant query:

```bash
npx skills find [query]
```

For example:

- User asks "how do I make my React app faster?" → `npx skills find react performance`
- User asks "can you help me with PR reviews?" → `npx skills find pr review`
- User asks "I need to create a changelog" → `npx skills find changelog`

The command will return results like:

```
Install with npx skills add <owner/repo@skill>

vercel-labs/agent-skills@vercel-react-best-practices
└ https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices
```

### Step 3: Present Options to the User

When you find relevant skills, present them to the user with:

1. The skill name and what it does
2. The install command they can run
3. A link to learn more at skills.sh

Example response:

```
I found a skill that might help! The "vercel-react-best-practices" skill provides
React and Next.js performance optimization guidelines from Vercel Engineering.

To install it:
npx skills add vercel-labs/agent-skills@vercel-react-best-practices

Learn more: https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices
```

### Step 4: Offer to Install

If the user wants to proceed, you can install the skill for them:

```bash
npx skills add <owner/repo@skill> -g -y
```

The `-g` flag installs globally (user-level) and `-y` skips confirmation prompts.

## Common Skill Categories

When searching, consider these common categories:

| Category        | Example Queries                          |
| --------------- | ---------------------------------------- |
| Web Development | react, nextjs, typescript, css, tailwind |
| Testing         | testing, jest, playwright, e2e           |
| DevOps          | deploy, docker, kubernetes, ci-cd        |
| Documentation   | docs, readme, changelog, api-docs        |
| Code Quality    | review, lint, refactor, best-practices   |
| Design          | ui, ux, design-system, accessibility     |
| Productivity    | workflow, automation, git                |

## Tips for Effective Searches

1. **Use specific keywords**: "react testing" is better than just "testing"
2. **Try alternative terms**: If "deploy" doesn't work, try "deployment" or "ci-cd"
3. **Check popular sources**: Many skills come from `vercel-labs/agent-skills` or `ComposioHQ/awesome-claude-skills`

## When No Skills Are Found

If no relevant skills exist:

1. Acknowledge that no existing skill was found
2. Offer to help with the task directly using your general capabilities
3. Suggest the user could create their own skill with `npx skills init`

Example:

```
I searched for skills related to "xyz" but didn't find any matches.
I can still help you with this task directly! Would you like me to proceed?

If this is something you do often, you could create your own skill:
npx skills init my-xyz-skill
```

---

## Assistant (Code · x-ai/grok-code-fast-1:optimized:free · 179.4s)

_Thinking:_

The user message is "# Find Skills" followed by a detailed description of the skill. This seems like the content of the skill itself, but actually, looking back, this is the output from the skill tool...If ExistingSummary is empty, you can use any subheading title that fits the guidelines.

---

Assistant: ## Interpreting user input  
- The message starts with "# Find Skills" followed by detailed content, likely the skill description itself.  
- This seems like the output from a skill tool, possibly loaded for the user to interact with.  

## Clarifying task goals  
- The skill appears designed to help users discover and install skills, but no specific request was made.  
- The assistant needs to process this content as part of responding, assuming the user wants help with finding skills.  

## Assessing conversation context  
- There’s no prior user query shown, suggesting this might be a continuation or initial skill load.  
- The focus is on using the provided skill content to assist, even without a direct question.  

## Planning next steps  
- The task is to respond helpfully, treating the skill content as the starting point.  
- Next, consider how to guide the user in exploring or utilizing the "find-skills" functionality.  

## Exploring response options  
- Options include summarizing the skill, offering to help find specific skills, or explaining how to use it.  
- The response should align with assisting the user in discovering and installing skills based on the content.  

## Checking for clarity  
- Ensure the response addresses potential user needs, like searching for skills or understanding the tool.  
- Avoid assuming intent, and focus on providing clear, actionable guidance.  

## Finalizing approach  
- The plan is to acknowledge the skill content and offer help in finding or installing skills.  
- Keep the tone helpful, ensuring the user feels supported in navigating the skill.  

## Ensuring neutrality  
- Present all options without bias, letting the user decide their next step.  
- Focus on facts, like the skill’s purpose, without critiquing or speculating on user intent.  

## Reviewing output style  
- Keep responses concise, engaging, and easy to read, with varied sentence structures.  
- Ensure bullets are under 100 words, summarizing key points without repetition.  

## Confirming user focus  
- The goal is to assist with finding skills, aligning with the skill’s name and description.  
- Double-check that the response stays relevant to the user’s implied need for skill discovery.  

## Wrapping up reasoning  
- All steps lead to crafting a response that leverages the skill content effectively.  
- Ready to output a helpful, neutral summary for the user to guide their next action.  

## Preparing for delivery  
- Ensure the final output is clear, concise, and follows the guidelines for tone and structure.

**Tool: question**

**Input:**
```json
{
  "questions": [
    {
      "question": "What kind of skills are you looking for? Please describe the task or domain you need help with.",
      "header": "Skill Search",
      "options": []
    }
  ]
}
```

**Output:**
```
User has answered your questions: "What kind of skills are you looking for? Please describe the task or domain you need help with."="im looking skills with experience as front-end developer with specialize in svelte". You can now continue with the user's answers in mind.
```

---

## Assistant (Code · x-ai/grok-code-fast-1:optimized:free · 18.3s)

_Thinking:_

The user is looking for skills with experience as a front-end developer specializing in Svelte.

**Tool: bash**

**Input:**
```json
{
  "command": "npx skills find svelte",
  "description": "Search for Svelte-related skills in the agent skills ecosystem"
}
```

**Output:**
```
npm warn exec The following package was not found and will be installed: skills@1.5.0

[38;5;250m███████╗██╗  ██╗██╗██╗     ██╗     ███████╗[0m
[38;5;248m██╔════╝██║ ██╔╝██║██║     ██║     ██╔════╝[0m
[38;5;245m███████╗█████╔╝ ██║██║     ██║     ███████╗[0m
[38;5;243m╚════██║██╔═██╗ ██║██║     ██║     ╚════██║[0m
[38;5;240m███████║██║  ██╗██║███████╗███████╗███████║[0m
[38;5;238m╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚══════╝[0m

[38;5;102mInstall with[0m npx skills add <owner/repo@skill>

[38;5;145msveltejs/ai-tools@svelte-code-writer[0m [36m3.8K installs[0m
[38;5;102m└ https://skills.sh/sveltejs/ai-tools/svelte-code-writer[0m

[38;5;145mejirocodes/agent-skills@svelte5-best-practices[0m [36m2.8K installs[0m
[38;5;102m└ https://skills.sh/ejirocodes/agent-skills/svelte5-best-practices[0m

[38;5;145msveltejs/ai-tools@svelte-core-bestpractices[0m [36m889 installs[0m
[38;5;102m└ https://skills.sh/sveltejs/ai-tools/svelte-core-bestpractices[0m

[38;5;145mspences10/svelte-skills-kit@sveltekit-structure[0m [36m406 installs[0m
[38;5;102m└ https://skills.sh/spences10/svelte-skills-kit/sveltekit-structure[0m

[38;5;145mgetsentry/sentry-for-ai@sentry-svelte-sdk[0m [36m335 installs[0m
[38;5;102m└ https://skills.sh/getsentry/sentry-for-ai/sentry-svelte-sdk[0m

[38;5;145mspences10/svelte-skills-kit@svelte-runes[0m [36m317 installs[0m
[38;5;102m└ https://skills.sh/spences10/svelte-skills-kit/svelte-runes[0m


```

---

## Assistant (Code · x-ai/grok-code-fast-1:optimized:free · 23.0s)

_Thinking:_

The command found several Svelte-related skills:

I found several Svelte-related skills:

- **svelte-code-writer** (sveltejs/ai-tools): Helps with writing Svelte code.  
  Install: `npx skills add sveltejs/ai-tools@svelte-code-writer`  
  Link: https://skills.sh/sveltejs/ai-tools/svelte-code-writer

- **svelte5-best-practices** (ejirocodes/agent-skills): Best practices for Svelte 5.  
  Install: `npx skills add ejirocodes/agent-skills@svelte5-best-practices`  
  Link: https://skills.sh/ejirocodes/agent-skills/svelte5-best-practices

- **svelte-core-bestpractices** (sveltejs/ai-tools): Core best practices for Svelte.  
  Install: `npx skills add sveltejs/ai-tools@svelte-core-bestpractices`  
  Link: https://skills.sh/sveltejs/ai-tools/svelte-core-bestpractices

- **sveltekit-structure** (spences10/svelte-skills-kit): SvelteKit project structure guidance.  
  Install: `npx skills add spences10/svelte-skills-kit@sveltekit-structure`  
  Link: https://skills.sh/spences10/svelte-skills-kit/sveltekit-structure

- **sentry-svelte-sdk** (getsentry/sentry-for-ai): Sentry SDK integration for Svelte.  
  Install: `npx skills add getsentry/sentry-for-ai@sentry-svelte-sdk`  
  Link: https://skills.sh/getsentry/sentry-for-ai/sentry-svelte-sdk

- **svelte-runes** (spences10/svelte-skills-kit): Guidance on Svelte runes.  
  Install: `npx skills add spences10/svelte-skills-kit@svelte-runes`  
  Link: https://skills.sh/spences10/svelte-skills-kit/svelte-runes

Would you like me to install any of these?

---

## User

install svelte-core-bestpractices

---

## Assistant (Code · x-ai/grok-code-fast-1:optimized:free · 17.4s)

_Thinking:_

The user wants to install the "svelte-core-bestpractices" skill.

**Tool: bash**

**Input:**
```json
{
  "command": "npx skills add sveltejs/ai-tools@svelte-core-bestpractices -g -y",
  "description": "Install the svelte-core-bestpractices skill globally"
}
```

**Output:**
```

[38;5;250m███████╗██╗  ██╗██╗██╗     ██╗     ███████╗[0m
[38;5;248m██╔════╝██║ ██╔╝██║██║     ██║     ██╔════╝[0m
[38;5;245m███████╗█████╔╝ ██║██║     ██║     ███████╗[0m
[38;5;243m╚════██║██╔═██╗ ██║██║     ██║     ╚════██║[0m
[38;5;240m███████║██║  ██╗██║███████╗███████╗███████║[0m
[38;5;238m╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚══════╝[0m

[90m┌[39m  [46m[30m skills [39m[49m
[90m│[39m
[90m│[39m  [2mTip: use the --yes (-y) and --global (-g) flags to install without prompts.[22m
[?25l[90m│[39m
[32m◇[39m  Source: https://github.com/sveltejs/ai-tools.git [2m@[22m[36msvelte-core-bestpractices[39m
[?25h[?25l[90m│[39m
[35m◒[39m  Cloning repository[999D[J[35m◐[39m  Cloning repository[999D[J[35m◓[39m  Cloning repository[999D[J[35m◑[39m  Cloning repository[999D[J[35m◒[39m  Cloning repository[999D[J[35m◐[39m  Cloning repository[999D[J[35m◓[39m  Cloning repository[999D[J[35m◑[39m  Cloning repository[999D[J[35m◒[39m  Cloning repository.[999D[J[35m◐[39m  Cloning repository.[999D[J[35m◓[39m  Cloning repository.[999D[J[35m◑[39m  Cloning repository.[999D[J[35m◒[39m  Cloning repository.[999D[J[35m◐[39m  Cloning repository.[999D[J[35m◓[39m  Cloning repository.[999D[J[35m◑[39m  Cloning repository.[999D[J[35m◒[39m  Cloning repository..[999D[J[35m◐[39m  Cloning repository..[999D[J[35m◓[39m  Cloning repository..[999D[J[35m◑[39m  Cloning repository..[999D[J[35m◒[39m  Cloning repository..[999D[J[35m◐[39m  Cloning repository..[999D[J[35m◓[39m  Cloning repository..[999D[J[35m◑[39m  Cloning repository..[999D[J[35m◒[39m  Cloning repository...[999D[J[32m◇[39m  Repository cloned
[?25h[?25l[90m│[39m
[999D[J[32m◇[39m  Found [32m2[39m skills
[?25h[90m│[39m
[34m●[39m  Selected 1 skill: [36msvelte-core-bestpractices[39m
[?25l[90m│[39m
[999D[J[32m◇[39m  45 agents
[?25h[90m│[39m
[34m●[39m  Installing to: [36mCodex[39m, [36mGitHub Copilot[39m, [36mKimi Code CLI[39m, [36mQwen Code[39m

[90m│[39m
[32m◇[39m  [0mInstallation Summary[0m [90m────────────────────────────────────────────────────────╮[39m
[90m│[39m  [2m[22m                                                                             [90m│[39m
[90m│[39m  [2m[36m~\.agents\skills\svelte-core-bestpractices[39m[22m                                   [90m│[39m
[90m│[39m  [2m  [32muniversal:[39m Codex, GitHub Copilot, Kimi Code CLI, Amp, Antigravity +7 more[22m  [90m│[39m
[90m│[39m  [2m  [2msymlink →[22m[2m Qwen Code[22m                                                        [90m│[39m
[90m│[39m  [2m[22m                                                                             [90m│[39m
[90m├───────────────────────────────────────────────────────────────────────────────╯[39m
[90m│[39m
[32m◇[39m  [0mSecurity Risk Assessments[0m [90m───────────────────────────────────────────────╮[39m
[90m│[39m  [2m[22m                                                                         [90m│[39m
[90m│[39m  [2m                           [2mGen[22m[2m               [2mSocket[22m[2m            [2mSnyk[22m[2m[22m      [90m│[39m
[90m│[39m  [2m[36msvelte-core-bestpractices[39m  [32mSafe[39m              [32m0 alerts[39m          [32mLow Risk[39m[22m  [90m│[39m
[90m│[39m  [2m[22m                                                                         [90m│[39m
[90m│[39m  [2m[2mDetails:[22m[2m [2mhttps://skills.sh/sveltejs/ai-tools[22m[2m[22m                             [90m│[39m
[90m│[39m  [2m[22m                                                                         [90m│[39m
[90m├───────────────────────────────────────────────────────────────────────────╯[39m
[?25l[90m│[39m
[999D[J[35m◒[39m  Installing skills[999D[J[35m◐[39m  Installing skills[999D[J[35m◓[39m  Installing skills[999D[J[32m◇[39m  Installation complete
[?25h
[90m│[39m
[32m◇[39m  [0m[32mInstalled 1 skill[39m[0m [90m───────────────────────────────────────────────────────────╮[39m
[90m│[39m  [2m[22m                                                                             [90m│[39m
[90m│[39m  [2m[32m✓[39m ~\.agents\skills\svelte-core-bestpractices[22m                                 [90m│[39m
[90m│[39m  [2m  [32muniversal:[39m Codex, GitHub Copilot, Kimi Code CLI, Amp, Antigravity +7 more[22m  [90m│[39m
[90m│[39m  [2m  [2msymlinked:[22m[2m Qwen Code[22m                                                       [90m│[39m
[90m│[39m  [2m[22m                                                                             [90m│[39m
[90m├───────────────────────────────────────────────────────────────────────────────╯[39m

[90m│[39m
[90m└[39m  [32mDone![39m[2m  Review skills before use; they run with full agent permissions.[22m


```

---

## Assistant (Code · x-ai/grok-code-fast-1:optimized:free · 3.2s)

_Thinking:_

The installation was successful. The skill "svelte-core-bestpractices" has been installed globally.

I've installed the svelte-core-bestpractices skill. It's now available globally.

---

## User

my current agent system using playwright to browse and collect data from targeted web link. I found a skills that could help browse internet (here's the link : "https://skills.sh/tool-belt/skills/web-search"). what if agent using skills instead of use playwright. is it possible ?  

---

## Assistant (Ask · x-ai/grok-code-fast-1:optimized:free · 9.2s)

_Thinking:_

The user has an agent system using Playwright to browse and collect data from targeted web links. They found a skill for web search at https://skills.sh/tool-belt/skills/web-search, and ask if it's po...titles must start with a present participle (gerund) verb form (eConsidering, considering, considering -> Considering).

 titles must start with present participle verbs like "Considering", "Exploring", etc., present participle verbs ending in -ing.

Titles must startwith present participle verbs ending in -ing, like "Considering", "Evaluating", etc. titlesmust startwith present participle verbs ending incomplete sentences sentence fragments sentence fragments sentence fragments sentence fragments sentence bullets must be concise 1-2 sentences bullets must be concise 1-2 sentences bullets must  Typo fixed: titles must start with present participle verbs ending in -ing, like "Considering", "Evaluating", "Summarizing", etc.

**Tool: webfetch**

**Input:**
```json
{
  "url": "https://skills.sh/tool-belt/skills/web-search",
  "format": "markdown"
}
```

**Output:**
```
web-search by tool-belt/skills

[](https://vercel.com "Made with love by Vercel")[Skills](/)

[PicksNew](/picks)[Official](/official)[Audits](/audits)[Docs](/docs)

[skills](/)/[tool-belt](/tool-belt)/[skills](/tool-belt/skills)/web-search

# web-search

Installation

`$ npx skills add https://github.com/tool-belt/skills --skill web-search`

SKILL.md

# Web Search & Extraction

Search the web and extract content via [inference.sh](https://inference.sh) CLI.

![Web Search & Extraction](/api/image-proxy?url=https%3A%2F%2Fcloud.inference.sh%2Fapp%2Ffiles%2Fu%2F4mg21r6ta37mpaz6ktzwtt8krr%2F01kgndqjxd780zm2j3rmada6y8.jpeg&s=f197e968713412ee)

## Quick Start

> Requires inference.sh CLI (`infsh`). [Install instructions](https://raw.githubusercontent.com/inference-sh/skills/refs/heads/main/cli-install.md)

```bash
infsh login

# Search the web
infsh app run tavily/search-assistant --input '{"query": "latest AI developments 2024"}'
```

## Available Apps

### Tavily

App

App ID

Description

Search Assistant

`tavily/search-assistant`

AI-powered search with answers

Extract

`tavily/extract`

Extract content from URLs

### Exa

App

App ID

Description

Search

`exa/search`

Smart web search with AI

Answer

`exa/answer`

Direct factual answers

Extract

`exa/extract`

Extract and analyze web content

## Examples

### Tavily Search

```bash
infsh app run tavily/search-assistant --input '{
  "query": "What are the best practices for building AI agents?"
}'
```

Returns AI-generated answers with sources and images.

### Tavily Extract

```bash
infsh app run tavily/extract --input '{
  "urls": ["https://example.com/article1", "https://example.com/article2"]
}'
```

Extracts clean text and images from multiple URLs.

### Exa Search

```bash
infsh app run exa/search --input '{
  "query": "machine learning frameworks comparison"
}'
```

Returns highly relevant links with context.

### Exa Answer

```bash
infsh app run exa/answer --input '{
  "question": "What is the population of Tokyo?"
}'
```

Returns direct factual answers.

### Exa Extract

```bash
infsh app run exa/extract --input '{
  "url": "https://example.com/research-paper"
}'
```

Extracts and analyzes web page content.

## Workflow: Research + LLM

```bash
# 1. Search for information
infsh app run tavily/search-assistant --input '{
  "query": "latest developments in quantum computing"
}' > search_results.json

# 2. Analyze with Claude
infsh app run openrouter/claude-sonnet-45 --input '{
  "prompt": "Based on this research, summarize the key trends: <search-results>"
}'
```

## Workflow: Extract + Summarize

```bash
# 1. Extract content from URL
infsh app run tavily/extract --input '{
  "urls": ["https://example.com/long-article"]
}' > content.json

# 2. Summarize with LLM
infsh app run openrouter/claude-haiku-45 --input '{
  "prompt": "Summarize this article in 3 bullet points: <content>"
}'
```

## Use Cases

-   **Research**: Gather information on any topic
-   **RAG**: Retrieval-augmented generation
-   **Fact-checking**: Verify claims with sources
-   **Content aggregation**: Collect data from multiple sources
-   **Agents**: Build research-capable AI agents

## Related Skills

```bash
# Full platform skill (all 250+ apps)
npx skills add inference-sh/skills@infsh-cli

# LLM models (combine with search for RAG)
npx skills add inference-sh/skills@llm-models

# Image generation
npx skills add inference-sh/skills@ai-image-generation
```

Browse all apps: `infsh app list`

## Documentation

-   [Adding Tools to Agents](https://inference.sh/docs/agents/adding-tools) - Equip agents with search
-   [Building a Research Agent](https://inference.sh/blog/guides/research-agent) - LLM + search integration guide
-   [Tool Integration Tax](https://inference.sh/blog/tools/integration-tax) - Why pre-built tools matter

Weekly Installs

14.2K

Repository

[tool-belt/skills](https://github.com/tool-belt/skills "tool-belt/skills")

GitHub Stars

344

First Seen

6 days ago

Security Audits

[

Gen Agent Trust HubPass

](/tool-belt/skills/web-search/security/agent-trust-hub)[

SocketWarn

](/tool-belt/skills/web-search/security/socket)[

SnykWarn

](/tool-belt/skills/web-search/security/snyk)

Installed on

claude-code11.3K

amp9.8K

codex9.8K

gemini-cli9.8K

kimi-cli9.8K

opencode9.8K
```

---

## Assistant (Ask · x-ai/grok-code-fast-1:optimized:free · 11.9s)

_Thinking:_

The skill "web-search" from tool-belt/skills provides web search and extraction capabilities via the inference.sh CLI.

Yes, it's possible for your agent to use this skill instead of Playwright for certain tasks, but not as a complete replacement.

- **What the web-search skill offers**: It provides AI-powered web search, URL content extraction, and summarization via Tavily/Exa APIs. It can extract clean text from specific URLs (including potentially PDFs) and answer questions based on web data.

- **Comparison to Playwright**:
  - Playwright is browser automation for navigating dynamic sites, handling JavaScript, clicking elements, and scraping structured data (e.g., your IDX announcement tables).
  - The skill excels at extraction and search but lacks interactive browsing capabilities.

- **Feasibility in your system**:
  - You could replace PDF text extraction (currently using PyMuPDF) with the skill's extract functions, assuming you feed it the PDF URLs.
  - For initial page scraping (getting announcement lists), Playwright is still needed unless the IDX site provides an API or you switch to search-based discovery.
  - Integration: Install the skill (`npx skills add https://github.com/tool-belt/skills --skill web-search`) and use it via CLI calls (e.g., `infsh app run tavily/extract`) in your Python code, or integrate Tavily/Exa Python clients directly.

If your goal is to simplify extraction, this skill could work well for that part. For full replacement, it's not suitable due to the browser automation gap. Would you like me to help integrate it?

---

