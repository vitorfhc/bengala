## Codebase Overview

Bengala is a Portuguese-language Discord bot running a daily "forbidden word" game where players get muted for saying the secret word, with scoring based on unique words sent during each round.

**Stack**: Python 3.12, discord.py, aiosqlite (SQLite), APScheduler, NLTK (stopwords)
**Structure**: `bengala/` (app package with bot, config, models, scoring, NLP pipeline, async DB layer) + `tests/` (pytest + pytest-asyncio)

For detailed architecture, see [docs/CODEBASE_MAP.md](docs/CODEBASE_MAP.md).
