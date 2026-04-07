---
name: "research-lit"
description: "Search and analyze research papers, find related work, summarize key ideas. Use when user says \"find papers\", \"related work\", \"literature review\", \"what does this paper say\", or needs to understand academic papers."
---

# Research Literature Review

Research topic: $ARGUMENTS

## Constants

- **PAPER_LIBRARY** — Local directory containing the user's paper packages. Check these paths in order:
  1. `papers/` in the current project directory
  2. Custom path specified by user in `AGENTS.md` under `## Paper Library`
- **MAX_LOCAL_PAPERS = 20** — Maximum number of local paper packages to scan. Prefer `metadata.yaml` and `paper/paper.md`; only read raw PDFs when Markdown is unavailable.
- **ARXIV_DOWNLOAD = false** — When `true`, download top 3-5 most relevant arXiv PDFs to PAPER_LIBRARY after search. When `false` (default), only fetch metadata (title, abstract, authors) via arXiv API — no files are downloaded.
- **ARXIV_MAX_DOWNLOAD = 5** — Maximum number of PDFs to download when `ARXIV_DOWNLOAD = true`.

> 💡 Overrides:
> - `/research-lit "topic" — paper library: ~/my_papers/` — custom local PDF path
> - `/research-lit "topic" — sources: zotero, local` — only search Zotero + local paper packages
> - `/research-lit "topic" — sources: zotero` — only search Zotero
> - `/research-lit "topic" — sources: web` — only search the web (skip all local)
> - `/research-lit "topic" — arxiv download: true` — download top relevant arXiv PDFs
> - `/research-lit "topic" — arxiv download: true, max download: 10` — download up to 10 PDFs

## Data Sources

This skill checks multiple sources **in priority order**. All are optional — if a source is not configured or not requested, skip it silently.

### Source Selection

Parse `$ARGUMENTS` for a `— sources:` directive:
- **If `— sources:` is specified**: Only search the listed sources (comma-separated). Valid values: `zotero`, `obsidian`, `local`, `web`, `all`.
- **If not specified**: Default to `all` — search every available source in priority order.

Examples:
```
/research-lit "diffusion models"                        → all (default)
/research-lit "diffusion models" — sources: all         → all
/research-lit "diffusion models" — sources: zotero      → Zotero only
/research-lit "diffusion models" — sources: zotero, web → Zotero + web
/research-lit "diffusion models" — sources: local       → local paper packages only
/research-lit "topic" — sources: obsidian, local, web   → skip Zotero
```

### Source Table

| Priority | Source | ID | How to detect | What it provides |
|----------|--------|----|---------------|-----------------|
| 1 | **Zotero** (via MCP) | `zotero` | Try calling any `mcp__zotero__*` tool — if unavailable, skip | Collections, tags, annotations, PDF highlights, BibTeX, semantic search |
| 2 | **Obsidian** (via MCP) | `obsidian` | Try calling any `mcp__obsidian-vault__*` tool — if unavailable, skip | Research notes, paper summaries, tagged references, wikilinks |
| 3 | **Local paper packages** | `local` | `metadata.yaml`, `paper/paper.md`, `paper/paper.pdf` under PAPER_LIBRARY | Structured metadata, Markdown, PDFs, optional LaTeX/code assets |
| 4 | **Web search** | `web` | Always available (WebSearch) | arXiv, Semantic Scholar, Google Scholar |

> **Graceful degradation**: If no MCP servers are configured, the skill still works with local paper packages + web search. Zotero and Obsidian are pure additions.

## Workflow

### Step 0a: Search Zotero Library (if available)

**Skip this step entirely if Zotero MCP is not configured.**

Try calling a Zotero MCP tool (e.g., search). If it succeeds:

1. **Search by topic**: Use the Zotero search tool to find papers matching the research topic
2. **Read collections**: Check if the user has a relevant collection/folder for this topic
3. **Extract annotations**: For highly relevant papers, pull PDF highlights and notes — these represent what the user found important
4. **Export BibTeX**: Get citation data for relevant papers (useful for `/paper-write` later)
5. **Compile results**: For each relevant Zotero entry, extract:
   - Title, authors, year, venue
   - User's annotations/highlights (if any)
   - Tags the user assigned
   - Which collection it belongs to

> 📚 Zotero annotations are gold — they show what the user personally highlighted as important, which is far more valuable than generic summaries.

### Step 0b: Search Obsidian Vault (if available)

**Skip this step entirely if Obsidian MCP is not configured.**

Try calling an Obsidian MCP tool (e.g., search). If it succeeds:

1. **Search vault**: Search for notes related to the research topic
2. **Check tags**: Look for notes tagged with relevant topics (e.g., `#diffusion-models`, `#paper-review`)
3. **Read research notes**: For relevant notes, extract the user's own summaries and insights
4. **Follow links**: If notes link to other relevant notes (wikilinks), follow them for additional context
5. **Compile results**: For each relevant note:
   - Note title and path
   - User's summary/insights
   - Links to other notes (research graph)
   - Any frontmatter metadata (paper URL, status, rating)

> 📝 Obsidian notes represent the user's **processed understanding** — more valuable than raw paper content for understanding their perspective.

### Step 0c: Scan Local Paper Packages

Before searching online, check if the user already has relevant papers locally:

1. **Locate packages**: Treat `PAPER_LIBRARY` as a package library, not a bare PDF dump. Prefer this order:
   - `papers/**/metadata.yaml`
   - `papers/**/paper/paper.md`
   - `papers/**/paper/paper.pdf`
   - fallback legacy files: `papers/**/*.pdf`

   Prefer the helper scanner when available:
   ```
   SCRIPT=$(find skills/skills-codex/research-lit/scripts ~/.codex/skills/research-lit/scripts ~/.agents/skills/research-lit/scripts -name "scan_local_paper_packages.py" 2>/dev/null | head -1)
   [ -n "$SCRIPT" ] && python3 "$SCRIPT" --root papers --query "QUERY" --limit 20 --ensure-markdown
   ```
   If the script is unavailable, emulate the same priority manually.

2. **De-duplicate against Zotero**: If Step 0a found papers, skip local packages already covered by Zotero. Match by DOI first, then arXiv ID, then normalized title, and only then by filename/path.

3. **Read local assets in the right order**:
   - Use `metadata.yaml` first for `title`, `authors`, `year`, `venue`, `doi`, `arxiv`, and `abstract`
   - Use `paper/paper.md` as the primary text source for relevance filtering and summarization
   - If a relevant candidate has `paper/paper.pdf` but no `paper/paper.md`, try `pdf-to-md` first to generate Markdown
   - Only read the raw PDF directly when Markdown conversion is unavailable or fails

4. **Filter by relevance**: Match the research topic against package-level signals first:
   - `foldername`, package path, and filename
   - `title` and `abstract` from `metadata.yaml`
   - opening sections from `paper/paper.md`
   Skip clearly unrelated papers before doing any expensive PDF work.

5. **Use `pdf-to-md` lazily, not for the whole library**:
   - Only attempt Markdown conversion for top local candidates that are actually relevant
   - Do not bulk-convert every PDF in `papers/`
   - If `MINERU_API_TOKEN` is missing or conversion fails, fall back to reading the PDF directly

6. **Summarize relevant packages**: For each relevant local paper package (up to MAX_LOCAL_PAPERS):
   - Prefer `metadata.yaml` + `paper/paper.md`
   - Read raw PDF pages only as a fallback
   - Extract: title, authors, year, venue, core contribution, relevance to topic
   - Note which assets are available: `metadata`, `markdown`, `pdf`, `latex`, `repo`
   - Flag papers that are directly related vs tangentially related

7. **Build local knowledge base**: Compile summaries into a "papers you already have" section. This becomes the starting point — external search fills the gaps.

> 📚 If no local papers are found, skip to Step 1. If the user has a comprehensive local collection, the external search can be more targeted (focus on what's missing).

### Step 1: Search (external)
- Use WebSearch to find recent papers on the topic
- Check arXiv, Semantic Scholar, Google Scholar
- Focus on papers from last 2 years unless studying foundational work
- **De-duplicate**: Skip papers already found in Zotero, Obsidian, or local library

**arXiv API search** (always runs, no download by default):

Locate the fetch script and search arXiv directly:
```bash
# Try to find arxiv_fetch.py
SCRIPT=$(find tools/ -name "arxiv_fetch.py" 2>/dev/null | head -1)
# If not found, check ARIS install
[ -z "$SCRIPT" ] && SCRIPT=$(find ~/.codex/skills/arxiv/ -name "arxiv_fetch.py" 2>/dev/null | head -1)

# Search arXiv API for structured results (title, abstract, authors, categories)
python3 "$SCRIPT" search "QUERY" --max 10
```

If `arxiv_fetch.py` is not found, fall back to WebSearch for arXiv (same as before).

The arXiv API returns structured metadata (title, abstract, full author list, categories, dates) — richer than WebSearch snippets. Merge these results with WebSearch findings and de-duplicate.

**Optional PDF download** (only when `ARXIV_DOWNLOAD = true`):

After all sources are searched and papers are ranked by relevance:
```bash
# Download top N most relevant arXiv papers
python3 "$SCRIPT" download ARXIV_ID --dir papers/
```
- Only download papers ranked in the top ARXIV_MAX_DOWNLOAD by relevance
- Skip papers already in the local library
- 1-second delay between downloads (rate limiting)
- Verify each PDF > 10 KB

### Step 2: Analyze Each Paper
For each relevant paper (from all sources), extract:
- **Problem**: What gap does it address?
- **Method**: Core technical contribution (1-2 sentences)
- **Results**: Key numbers/claims
- **Relevance**: How does it relate to our work?
- **Source**: Where we found it (Zotero/Obsidian/local/web) — helps user know what they already have vs what's new

### Step 3: Synthesize
- Group papers by approach/theme
- Identify consensus vs disagreements in the field
- Find gaps that our work could fill
- If Obsidian notes exist, incorporate the user's own insights into the synthesis

### Step 4: Output
Present as a structured literature table:

```
| Paper | Venue | Method | Key Result | Relevance to Us | Source |
|-------|-------|--------|------------|-----------------|--------|
```

Plus a narrative summary of the landscape (3-5 paragraphs).

If Zotero BibTeX was exported, include a `references.bib` snippet for direct use in paper writing.

### Step 5: Save (if requested)
- Save paper PDFs to `papers/`
- Update related work notes in project memory
- If Obsidian is available, optionally create a literature review note in the vault

## Key Rules
- Always include paper citations (authors, year, venue)
- Distinguish between peer-reviewed and preprints
- Be honest about limitations of each paper
- Note if a paper directly competes with or supports our approach
- **Never fail because a MCP server is not configured** — always fall back gracefully to the next data source
- Zotero/Obsidian tools may have different names depending on how the user configured the MCP server (e.g., `mcp__zotero__search` or `mcp__zotero-mcp__search_items`). Try the most common patterns and adapt.
