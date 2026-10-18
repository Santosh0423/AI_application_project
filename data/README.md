# Data Directory

Knowledge base for the RAG pipeline.

| Path | Contents | In Git? |
|---|---|---|
| `sources.json` | List of the 33 official pages used (authority, title, URL) | ✅ |
| `raw/*.md` | Text of each page, downloaded by `scripts/fetch_sources.py`. Each file starts with a header holding its title, URL, authority and download date | ✅ |
| `index/` | Vector index (`vectors.npy` + `chunks.json`) built by `scripts/ingest.py` | ❌ generated |
| `profile.json` | The user's saved profile (memory) | ❌ personal, generated |

## Data governance

- All documents are **public, official guidance** from Migri, DVV, Kela, Vero and InfoFinland. They contain no personal data.
- The user profile only stores coarse categories (citizenship group, student status, length of stay, city). It stays on the user's computer and is git-ignored.
- No secrets, API keys or large files are stored here (the whole `raw/` folder is under 1 MB).

## Updating the knowledge base

```bash
python scripts/fetch_sources.py   # download the latest versions of the pages
python scripts/ingest.py          # rebuild the vector index
```
