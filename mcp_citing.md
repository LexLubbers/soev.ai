## MCP citation integration (reuse LibreChat file-search UI)

### Goal
Make an MCP tool produce output that LibreChat renders with the existing file-search citation UI (inline anchors + Sources with page numbers), without further changes to LibreChat.

### What to emit from the MCP tool
1) Inline anchors in the assistant text
- Single source: append `\ue202turn0file{index}` after the sentence.
- Multiple sources: wrap in composite block `\ue200\ue202turn0file{a}\ue202turn0file{b}\ue201`.
- Mention the filename/title in the sentence before the anchor.
- **Important**: These are **literal escape sequences** (6 characters: backslash, u, e, 2, 0, 2), NOT Unicode characters.
  - In Python: use **raw strings** `r"\ue202"` or **double backslashes** `"\\ue202"`
  - In JSON: use double backslashes `"\\ue202"`

2) Artifact resource carrying sources
- `resource.uri`: `artifact://file_search`
- `resource.mimeType`: `application/json`
- `resource.text` (JSON):
  - `fileCitations: true`
  - `sources: Array<{ type: 'file'; fileId: string; fileName?: string; relevance: number; pages?: number[]; pageRelevance?: Record<string, number>; metadata?: { url?: string; [k: string]: unknown } }>`

Example JSON payload:
```json
{
  "fileCitations": true,
  "sources": [
    {
      "type": "file",
      "fileId": "pdf_abc123",
      "fileName": "Soil Report 2024.pdf",
      "relevance": 0.87,
      "pages": [12, 13],
      "pageRelevance": { "12": 0.90, "13": 0.78 },
      "metadata": { "url": "" }
    },
    {
      "type": "file",
      "fileId": "url_7f3e",
      "fileName": "RIVM nitrate thresholds",
      "relevance": 0.79,
      "pages": [],
      "pageRelevance": {},
      "metadata": { "url": "https://example.org/nitrates" }
    }
  ]
}
```

Notes
- PDFs: fill `pages` and `pageRelevance`.
- Websites: leave `pages` empty; put the link in `metadata.url`.
- `fileId` should be stable per source for the session.
- Emit a single `artifact://file_search` resource per tool call so indices align with `turn0`.

### Where anchors go
- Use `turn0` in all anchors for a single MCP tool call: `\ue202turn0file0`, `\ue202turn0file1`, etc.
- The order of `sources` defines the `{index}` numbers you cite.
- The `\ue202` is a literal 6-character escape sequence, not a Unicode character.

### MCP tool response shape (Python sketch)
```python
import json

# Use raw strings (r"") to preserve backslashes as literal characters
MARK = r"\ue202"
COMPOSITE_START = r"\ue200"
COMPOSITE_END = r"\ue201"

INSTRUCTIONS = (
    "Mention the source title, then append an anchor marker immediately after the sentence.\n"
    f"- Single: {MARK}turn0file{{index}}\n"
    f"- Multiple: {COMPOSITE_START}{MARK}turn0file{{a}}{MARK}turn0file{{b}}{COMPOSITE_END}\n"
    "Do not use markdown footnotes or links. Keep anchors next to the supported sentence.\n"
)

def build_sources(records):
    sources = []
    for idx, r in enumerate(records):
        title = (r.get("title") or f"Document {idx+1}")[:120]
        url = ""
        links = r.get("links")
        if isinstance(links, list) and links and isinstance(links[0], dict):
            url = links[0].get("url", "")
        score = float(r.get("score", 0.75))
        pages = r.get("pages") or []
        page_relevance = r.get("page_relevance") or {}
        sources.append({
            "type": "file",
            "fileId": r.get("id") or f"doc_{idx}",
            "fileName": title,
            "relevance": score,
            "pages": pages,
            "pageRelevance": page_relevance,
            "metadata": {"url": url},
        })
    return sources

def draft_text(records):
    lines = [INSTRUCTIONS, "Retrieved context:"]
    for idx, r in enumerate(records):
        title = r.get("title") or f"Document {idx+1}"
        snippet = (r.get("chunk_content") or "")[:400]
        lines.append(f'- From "{title}": {snippet} {MARK}turn0file{idx}')
    return "\n\n".join(lines)

def format_response(records):
    content = []
    text_block = draft_text(records)
    content.append({"type": "text", "text": text_block})

    artifact_payload = {
        "fileCitations": True,
        "sources": build_sources(records),
    }
    try:
        payload_text = json.dumps(artifact_payload, ensure_ascii=False)
    except Exception as e:
        # Log and degrade gracefully: proceed without the artifact if JSON encoding fails
        payload_text = ""

    if payload_text:
        content.append({
            "type": "resource",
            "resource": {
                "uri": "artifact://file_search",
                "name": "file_citations",
                "mimeType": "application/json",
                "text": payload_text,
            },
        })

    return {"content": content}
```

### Error handling
- Validate inputs and log useful errors; avoid empty `except` blocks.
- If the artifact payload cannot be encoded, return only the text content.

### Quality checklist
- Anchors use `turn0` and match the array order in `sources`.
- PDFs include `pages` and `pageRelevance`; websites include `metadata.url`.
- Only one `artifact://file_search` resource per tool call.
- Text demonstrates anchor usage so the LLM continues the pattern in replies.

### Advanced (optional)
- If you need MCP and native file_search to have separate citation “turns,” we can introduce a dedicated MCP marker type later. The minimal integration above works well in mixed chats and is recommended first.


