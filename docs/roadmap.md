# Lerni - Roadmap

## Phase 1: MVP (Core System)

**Goal**: Fully functional local study system without AI

### Data Layer
- [ ] SQLite database setup (`~/.lerni/lerni.db`)
- [ ] Topic model with metadata JSON
- [ ] TopicVersion model (immutable snapshots)
- [ ] Review model with SM-2 state

### Feynman Workflow
- [ ] `study new` - Full 4-step flow
- [ ] `study new --quick` - Quick capture (step 1 only)
- [ ] `study edit` - Minor edits without versioning
- [ ] `study snapshot` - Create new version

### Review System
- [ ] SM-2 algorithm implementation
- [ ] `study review` - Review session workflow
- [ ] `study skip` - Skip and reschedule
- [ ] `study today` - Daily summary

### Organization
- [ ] `study list` - List with filters (domain, tag, due)
- [ ] `study search` - Full-text search
- [ ] `study show` / `study history` - View topic and versions
- [ ] `study meta` - Update metadata
- [ ] `study link` / `study unlink` - Topic relationships

### Notifications
- [ ] `study notify` - macOS notification
- [ ] `study notify --setup` - Cron setup instructions

---

## Phase 2: AI Agents

**Goal**: Optional AI-assisted coaching

### Infrastructure
- [ ] AISession model for transcript storage
- [ ] API key configuration (Anthropic/OpenAI)
- [ ] Prompt file loading and variable substitution

### Beginner Agent
- [ ] Socratic mode - Probing questions
- [ ] ELI5 mode - Confused beginner roleplay
- [ ] Analogy mode - Push for real-world examples
- [ ] 3-5 turn session management

### Expert Agent
- [ ] Rigor levels 1-5
- [ ] Gap identification
- [ ] Grade suggestion

### CLI Integration
- [ ] `--ai` flag for review command
- [ ] `--mode` and `--rigor` options
- [ ] `study coach` - Standalone agent sessions
- [ ] `study sessions` / `study session` - View transcripts

---

## Phase 3: Analytics & Export

**Goal**: Insights and data portability

- [ ] `study stats` - Global statistics
- [ ] `study stats <id>` - Per-topic analytics
- [ ] Grade trend visualization (ASCII charts)
- [ ] `study export --all` - Full JSON backup
- [ ] `study import` - Restore from backup
- [ ] `study export-graph` - Knowledge graph JSON

---

## Phase 4: Visualization

**Goal**: Rich visual interfaces

- [ ] Plotly HTML reports for grade progression
- [ ] Neo4j export for graph visualization
- [ ] launchd integration (persistent notifications)
- [ ] Configurable reminder times

---

## Phase 5: Future Ideas

**Documented for later consideration**:

### Native Apps
- macOS menu bar app (quick review access)
- iOS companion app (review on mobile)
- Interactive mindmap UI

### Additional Agents
- **Interviewer Agent** - Technical interview simulation
- **Connector Agent** - Suggests links between topics

### Advanced Features
- Rich media support (images, LaTeX)
- Local LLM support (ollama) for offline AI
- Collaborative features (share topic packs)
