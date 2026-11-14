# Literature Review & Knowledge Synthesis System

A personal research cockpit combining **Zotero**, **Obsidian**, and **Scite.ai** for fast Quarto citation and research gap discovery.

## System Architecture

```mermaid
flowchart LR
    subgraph Storage["1. Storage & Second Brain"]
        Zotero["Zotero Desktop\n(PDFs & 4-Color Highlights)"]
        Vault["Obsidian Vault (Dropbox)\n(01-Literature, 02-Concepts, 03-Research-Gaps)"]
    end

    subgraph Service["2. lit-review Backend (This Repo)"]
        Backend["FastAPI / MCP Server\n(ZoteroService + SciteService + ObsidianService)"]
    end

    subgraph Writing["3. Writing Projects (Independent)"]
        Quarto["Quarto Manuscripts (.qmd)\n(e.g. ~/github/dissertation/)"]
    end

    Zotero <--> Backend
    Vault <--> Backend
    Backend -.->|API / MCP / Clipboard| Quarto
```

---

## 📁 Obsidian Vault Structure (The 3 Folders)

Actual manuscript drafts (**Quarto `.qmd` files**) live in independent project repositories outside Obsidian, allowing clean collaboration and version control with co-authors. Obsidian is strictly organized into 3 folders:

1. **`01-Literature/` (Atomic Paper Notes)**:
   - One note per paper named `@citekey.md`.
   - Contains YAML frontmatter, 4-color highlighted quotes, Zotero PDF page deep-links, and protected user reading notes.
2. **`02-Concepts/` (Idea & Method Hubs)**:
   - Topic and technology notes (e.g. `[[Transformer]]`, `[[Hyperspectral]]`).
   - Backlinks panel automatically pools all papers utilizing or discussing that concept.
3. **`03-Research-Gaps/` (Synthesis & Discovery)**:
   - Dataview summary tables pooling `## ⚠️ Limitations` and Scite contrasting debates to reveal unaddressed research questions.

---

## 🎨 PDF Highlighting Color Protocol

When reading papers in Zotero's PDF reader, use this color-coding scheme:

|     Color     | Hex Code  | Category              | What to Highlight                                  | Target Section in Obsidian          |
| :-----------: | :-------: | :-------------------- | :------------------------------------------------- | :---------------------------------- |
| 🟡 **Yellow** | `#ffd400` | **Core Findings**     | Main numerical findings, takeaways, or conclusions | `## 💡 Quick Finding`               |
| 🟢 **Green**  | `#5fb236` | **Methodology**       | Models, algorithms, experimental setups, datasets  | `## 🔬 Methodology & Setup`         |
|  🔴 **Red**   | `#ff6666` | **Limitations**       | Unresolved weaknesses, assumptions, research gaps  | `## ⚠️ Limitations & Research Gaps` |
| 🟣 **Purple** | `#a28ae5` | **Quotes for Citing** | High-impact verbatim quotes for Quarto papers      | `## 📌 Highlighted Quotes`          |
|  🔵 **Blue**  | `#2ea8e5` | **Context**           | Background problem statement or industry stats     | `## 📌 Highlighted Quotes`          |

---

## Setup Requirements

### 1. Obsidian Vault Symlink

This repository expects a symlink named `obsidian` pointing to your private Obsidian vault (stored in your Dropbox or local drive):

```bash
# In the root of this repository:
ln -s "/path/to/your/Dropbox/vault" obsidian
```

_Note: The actual path to your vault is kept private and never hard-coded in the repository configuration._

### 2. Credentials & Secrets

All API credentials (Zotero, Scite.ai, GenAI) are retrieved securely from the Linux system keyring (`lit-review` service). Zero plain-text keys are stored in this repository.

To set your credentials using your Linux terminal:

```bash
keyring set lit-review ZOTERO_LIBRARY_ID
keyring set lit-review ZOTERO_API_KEY
keyring set lit-review SCITE_API_KEY
keyring set lit-review GENAI_API_KEY
```

---

## 📊 Unread Paper Priority Scoring

Unread papers in Zotero are ranked continuously from **high to low** (no rigid tiers) using the following formula:

$$\text{Priority Score} = S_{\text{relevance}} + S_{\text{citations}} + S_{\text{recency}} + S_{\text{bonus}}$$

| Component | Range | Calculation | Purpose |
| :--- | :---: | :--- | :--- |
| **1. LLM Relevance** | **0 – 50 pts** | Purdue GenAI (`gemma4:26b-a4b`) evaluates Title + Abstract against your active topic in [`research_focus.json`](research_focus.json) (`1–5` scale $\times 10$). | Floats papers most relevant to your current research to the top. |
| **2. Citation Count** | **0 – 35 pts** | Logarithmic scaling of total citations: $\min(35,\; 11.5 \times \log_{10}(\text{citations} + 1))$. | Gives strong weight to influential papers without letting 10,000-cite surveys completely dominate. |
| **3. Recency** | **0 – 15 pts** | 0–1 yr old: `15` \| 2–3 yrs: `10` \| 4–5 yrs: `5` \| >5 yrs: `0`. | Keeps your reading list current with recent publications. |
| **4. Manual Bonus** | **Adjustable** | User-defined boost or penalty (e.g., `+20` for advisor-recommended papers, `-10` to deprioritize). | Overrides automation whenever you want to bump a specific paper up or down. |

### Updating Your Current Research Topic
You can update your active research focus anytime in two ways:
1. **Manually:** Edit [`research_focus.json`](research_focus.json) in the repository root.
2. **Via Web App / API:** `GET` / `PUT /api/config/research-focus`.
