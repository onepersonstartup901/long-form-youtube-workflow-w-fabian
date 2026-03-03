# Video Scripting

Write structured scripts/outlines for longform YouTube videos. Scripts balance being detailed enough to stay on track while loose enough to sound natural.

## Execution Script

`execution/generate_script.py`

---

## Quick Start

```bash
# Generate a script from a topic outline
python3 execution/generate_script.py --topic "Topic Title" --outline .tmp/outlines/topic.md

# Generate from just a title (AI fills in structure)
python3 execution/generate_script.py --topic "How to X" --style conversational --length 15

# Refine an existing script
python3 execution/generate_script.py --refine .tmp/scripts/draft_v1.md
```

---

## Script Structure

Every longform video follows this skeleton:

### 1. Hook (0:00 - 0:30)
- **Pattern interrupt** — Say something unexpected
- **Promise** — What the viewer will learn/get
- **Proof** — Why you're credible on this topic
- Keep under 30 seconds. Front-load value.

### 2. Context (0:30 - 2:00)
- **Why this matters** — Frame the problem
- **Who this is for** — Qualify the audience
- **What we'll cover** — Brief roadmap (not a full outline)

### 3. Main Content (2:00 - end-2:00)
- **3-7 key segments** — Each with a clear point
- **Transitions** — Bridge segments naturally ("Now that we've covered X, let's talk about Y")
- **Retention hooks** — Every 3-5 minutes, re-engage ("Here's where it gets interesting...")
- **B-roll cues** — Mark where visuals/screen recordings should go: `[B-ROLL: description]`
- **Cut markers** — Mark intentional pauses: `[BEAT]`

### 4. CTA & Outro (last 2 min)
- **Recap** — 2-3 key takeaways
- **CTA** — Subscribe, comment prompt, next video teaser
- **End screen** — Point to related content

---

## Script Formats

### Full Script
Word-for-word. Best for:
- Complex technical topics
- Sponsored segments
- Videos under 10 min

### Bullet Outline
Key points with talking notes. Best for:
- Conversational videos
- Experienced creators
- Videos over 15 min

### Hybrid
Full script for hook/CTA, bullet outline for main content. Best for:
- Most longform content
- Balances structure with spontaneity

### Faceless (Automated Pipeline)
Machine-parseable VISUAL+NARRATION blocks for the automated video pipeline. Best for:
- Daily faceless content (narrated B-roll)
- Fully automated production via `pipeline_orchestrator.py`
- Tech/AI explainer videos

```bash
python3 execution/generate_script.py --topic "Topic" --style faceless --length 12
python3 execution/parse_script.py .tmp/{vid}/script.md -o .tmp/{vid}/parsed_script.json
```

Each `---` block maps to a Remotion segment with matched visual + narration + captions:

```markdown
## HOOK (0:00 - 0:30)

---
VISUAL_TYPE: stock_footage
VISUAL_QUERY: "developer typing code"
NARRATION: "Opening hook sentence."
---
VISUAL_TYPE: ai_generated
VISUAL_PROMPT: "Futuristic code editor, cinematic"
NARRATION: "Second hook sentence."
CAPTION_EMPHASIS: ["key phrase"]
---
```

**Block fields:**
| Field | Required | Values |
|-------|----------|--------|
| `VISUAL_TYPE` | Yes | `stock_footage`, `ai_generated` |
| `VISUAL_QUERY` | If stock_footage | Pexels/Pixabay search query |
| `VISUAL_PROMPT` | If ai_generated | Flux image generation prompt |
| `NARRATION` | Yes | Spoken text for this segment |
| `CAPTION_EMPHASIS` | No | Words to highlight in captions |

**Targets:** 50-70 blocks for a 10-12 minute video. Each block ~8-15 seconds of narration.

---

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Topic/title | Ideation phase | What the video is about |
| Outline | `.tmp/outlines/` | Optional structured outline |
| Target length | User | Minutes (default: 15) |
| Style | User | conversational / educational / storytelling |

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Script | Markdown | `.tmp/scripts/{slug}_v{n}.md` |
| Shot list | Markdown | `.tmp/scripts/{slug}_shots.md` |
| Teleprompter version | Plain text | `.tmp/scripts/{slug}_teleprompter.txt` |

---

## Style Guidelines

- **Write for the ear, not the eye** — Read it aloud. If it sounds stiff, rewrite.
- **Short sentences** — Break up dense paragraphs.
- **Active voice** — "Do this" not "This should be done"
- **Conversational markers** — "Look,", "Here's the thing,", "So,"
- **Specifics over generics** — Numbers, examples, stories
