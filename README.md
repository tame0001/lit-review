# Literature Review & Knowledge Synthesis System

A personal research cockpit combining **Zotero**, **Obsidian**, and **Scite.ai** for fast Quarto citation and research gap discovery.

## Setup Requirements

### 1. Obsidian Vault Symlink
This repository expects a symlink named `obsidian` pointing to your private Obsidian vault (stored in your Dropbox or local drive):

```bash
# In the root of this repository:
ln -s "/path/to/your/Dropbox/vault" obsidian
```

*Note: The actual path to your vault is kept private and never hard-coded in the repository configuration.*

### 2. Credentials & Secrets
All API credentials (Zotero, Scite.ai, GenAI) are retrieved securely from the Linux system keyring (`lit-review` service). Zero plain-text keys are stored in this repository.

To set your credentials using your Linux terminal:
```bash
keyring set lit-review ZOTERO_LIBRARY_ID
keyring set lit-review ZOTERO_API_KEY
keyring set lit-review SCITE_API_KEY
```

---

# Note to myself (Legacy / Roadmap)

- Migrate from virtual environment to uv
- Reorganize folder. Functionality should be in utils / backend.
- Complete todo list in [here](main.py)
- Scite.ai has API [docs](https://api.scite.ai/docs)
