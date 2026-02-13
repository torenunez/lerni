# Lerni

A local-first, privacy-preserving learning system that combines the **Feynman Technique** with **spaced repetition** (SM-2) to help you learn deeply and remember permanently.

## Philosophy

- **Learn by teaching**: The best way to understand something is to explain it simply
- **Forgetting is natural**: Spaced repetition fights the forgetting curve systematically
- **Privacy first**: Your learning data stays on your machine
- **AI as coach, not crutch**: Optional AI agents challenge your understanding — they never generate content for you

## How It Works

1. **Capture** — Write what you know about a topic (raw notes)
2. **Simplify** — Explain it like you're teaching someone else
3. **Identify gaps** — What's still unclear? What questions remain?
4. **Refine** — Improve your explanation with analogies and examples
5. **Review** — SM-2 algorithm schedules reviews at optimal intervals

## Features

- CLI-based workflow (`study new`, `study review`, `study today`)
- 4-step Feynman technique with version tracking
- Concept-based knowledge graph with typed relationships (parent, prerequisite, related)
- SM-2 spaced repetition scheduling
- macOS notifications for daily review reminders
- Optional AI coaching — planned for Phase 2

## Status

**Phase 1 (MVP) is complete.** Core system is functional: data layer, Feynman workflow, SM-2 review scheduling, concept graph, and CLI.

See [`docs/`](docs/) for detailed specifications:
- [Mission & Vision](docs/mission.md)
- [Technical Specification](docs/spec.md)
- [Roadmap](docs/roadmap.md)
- [Backlog](docs/todo.md)

## Tech Stack

- Python 3.11+
- SQLite (local database)
- typer (CLI)
- Anthropic Claude / OpenAI (optional, user-provided API keys)

## License

[MIT](LICENSE)
