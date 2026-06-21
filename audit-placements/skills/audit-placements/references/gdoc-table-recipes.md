# Google Docs table recipes (the gotchas that bit us)

The MCP for Google Docs is mechanical and unforgiving — every index is character-precise, and many operations are NOT idempotent (re-running shifts indices). This file encodes the patterns that worked after multiple failures.

## Mental model

Every Google Doc is a flat sequence of characters indexed from 1. A table cell occupies a contiguous range `[cellStart, cellEnd)`. The cell's final character is always a paragraph break (`\n`) that is **structurally part of the cell** — deleting it merges cells and breaks the table.

So the **safe deletable window inside a cell** is `[cellStart, cellEnd-1)`. `cellStart` IS deletable. `cellEnd-1` is the protected `\n`.

(An earlier memory said `[cellStart+1, cellEnd-1)` — that was wrong, and produced the "stray leading char" bug. `cellStart` is fine to delete.)

## Read once, cache indices

Re-reading the full doc after every edit is expensive (the doc tool returns a multi-MB JSON for big tables). Read it ONCE after the skeleton is built and cache every cell's `(startIndex, endIndex)`:

```python
import json
DOC = '<path to cached readDocument JSON output>'
with open(DOC) as f: doc = json.load(f)

def cell_range(cell):
    start = end = None
    for el in cell.get('content', []):
        if start is None: start = el.get('startIndex')
        end = el.get('endIndex')
    return start, end

tables = [el['table'] for el in doc['body']['content'] if 'table' in el]
placements_table = tables[0]  # adjust index per your doc
for ri, row in enumerate(placements_table['tableRows']):
    for ci, cell in enumerate(row['tableCells']):
        s, e = cell_range(cell)
        print(f"R{ri}C{ci} [{s}..{e})")
```

Write a tiny helper script to a tmp file and run it once. Save the cell index map for the rest of the workflow.

## Edit bottom-up

When you edit cells, every insert / delete after position N shifts all indices > N. If you edit top-down, every cell after the first edit has stale indices.

The fix is simple: **edit from the LAST row up to the FIRST.** Indices for cells above your edit are unaffected, so the cached map stays valid.

## Cell text replace pattern

```python
# Cached: cellStart, cellEnd
mcp__google-docs__deleteRange(
    documentId=DOC_ID,
    startIndex=cellStart,
    endIndex=cellEnd - 1,   # NOT cellEnd — that would eat the trailing \n
)
mcp__google-docs__insertText(
    documentId=DOC_ID,
    index=cellStart,
    text="new cell content",
)
```

After this single replace, the cell's `endIndex` shifted by `len(new) - len(old)`. If you're processing one cell at a time bottom-up, that's fine — every cell ABOVE this one is unaffected.

## Cell image insert pattern

`insertImage` takes a 1-based character `index` (no cell-targeting parameter). If you pass an index in the middle of a cell, the image lands at the **next row's column 0** — a bug we hit twice in the SMB session.

The fix: use `cellEnd - 2` to ensure the image lands INSIDE the target cell:

```python
mcp__google-docs__insertImage(
    documentId=DOC_ID,
    index=cellEnd - 2,
    imageUrl=<gist raw URL>,
    width=<px>,   # optional but recommended — uncropped page shots overflow cells
    height=<px>,
)
```

`imageUrl` must be a public URL. `localImagePath` silently fails (don't use it). The standard workflow:

```python
# 1. Push the local PNG to a gist
gist = mcp__github__create_gist(
    description="audit-<slug>-<row>",
    files={"<row>.png": {"content": "<base64 png>"}},
    public=False,
)
# 2. Pull the raw URL with FULL commit hash (not just /raw/ — the hash is required)
raw_url = f"https://gist.githubusercontent.com/<user>/<gist_id>/raw/<commit_sha>/<row>.png"
# 3. insertImage with the raw URL
mcp__google-docs__insertImage(documentId=DOC_ID, index=cellEnd-2, imageUrl=raw_url)
```

If you forget the commit sha in the raw URL, the doc may load a stale or wrong version after the next push.

## Verify before believing

After each batch of edits, **dump the cells you touched** and visually confirm they contain what you expected. Cheap insurance:

```python
def cell_text(cell):
    parts = []
    for el in cell.get('content', []):
        for tr in (el.get('paragraph', {}).get('elements', [])):
            if 'textRun' in tr: parts.append(tr['textRun'].get('content',''))
    return ''.join(parts).strip()

def cell_images(cell):
    return sum(1 for el in cell.get('content', [])
               for tr in el.get('paragraph', {}).get('elements', [])
               if 'inlineObjectElement' in tr)
```

If `cell_images(...)` returns 0 for a row you just inserted an image into, the index was off — the image probably landed in the next row's first cell. Look for it there with `find_images.py`-style enumeration before re-inserting.

## Building the skeleton table

`insertTableWithData` is the fastest way to create the table with the header row + body rows in one call. Pass body rows as a 2D array with the static content (Surface, Cohort, Codepath, Condition) pre-populated; leave Status and Screenshot empty for the screenshot pass.

```python
mcp__google-docs__insertTableWithData(
    documentId=DOC_ID,
    index=<after-exec-summary>,
    data=[
        ["Surface", "Cohort", "Codepath / IDs", "Status", "Condition", "Screenshot"],
        ["Cart drawer top banner", "Retained SMB",
         "app/.../express_cart_banner_resolver.rb:42; express_placement_id=37",
         "", "Add 13+ items to Safeway cart as a retained SMB member", ""],
        # ...more rows
    ],
)
```

After this, immediately `readDocument` once and cache every cell's range — all later edits work from that cache.

## Don't

- **Don't `deleteRange(cellStart, cellEnd)`** — eats the cell's `\n`, breaks the table structure
- **Don't `insertImage` mid-cell** — image silently moves to next row's column 0
- **Don't edit top-down** — every edit invalidates the indices for everything below
- **Don't `localImagePath`** — silently fails; always go through gist
- **Don't trust the index map after a non-bottom-up edit** — re-read the doc if you broke the bottom-up pattern
