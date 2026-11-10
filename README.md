# Note to myself

- Migrate from virtual environment to uv
- Reorganize folder. Functionality should be in utils. Create main files for lit review pipeline.
- Complete todo list in [here](main.py)
- Scite.ai has API [docs](https://api.scite.ai/docs)

# Neo4j Commands

## Creating new nodes

Creating a new paper node and assign it as a variable `p`.
Then create another journal node and assign it as a variable `j`.
Crete a relationship between node `j` and node `p`.

```bash
CREATE (p:Paper {name: $name, date:$date})
CREATE (j:Journal {name: $name})
CREATE (p)-[:PUBLISH_IN]->(j)
```

Show the entire path that link to a specific node.

```bash
MATCH p=(:Paper {doi: "10.1111/cuag.12316"})-[*]-()
RETURN p
```
