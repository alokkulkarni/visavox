# Cross-service test suites

Unit tests live next to their package (`tools/*/tests`, `services/*/tests`). This folder holds the suites that span services (CLAUDE.md rule 11, SDD §14):

| Folder | Marker | What it proves |
|---|---|---|
| `tests/contract/` | `contract` | OpenAPI, LiveKit avatar contract (SDD §7.3) and Connect event schemas |
| `tests/media/` | `media` | A/V offset, fps, LSE-C/D lip-sync, identity similarity, watermark detection (NFR-Q, TRU-03) |
| `tests/e2e/` | `e2e` | Full flows against a deployed cell and the Visavox test Connect instance |
| `tests/load/` | `load` | Concurrent sessions and 2× headroom (NFR-A2) |

Fixtures use synthetic faces and voices only (CLAUDE.md rule 23).
