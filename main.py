from dotenv import dotenv_values
from neo4j import GraphDatabase

config = dotenv_values(".env")

AURA_URI = config["URI"]
AURA_USER = "neo4j"
AURA_PASSWORD = config["PASSWORD"]


def add_node(session, node_properties):
    """
    Adds a node to the Neo4j database with the given properties.
    """
    create_node_query = """
    CREATE (n:Person {name: $name, age: $age, city: $city})
    RETURN n
    """
    result = session.run(create_node_query, **node_properties)
    return result.single()


with GraphDatabase.driver(AURA_URI, auth=(AURA_USER, AURA_PASSWORD)) as driver:
    with driver.session() as session:

        node_properties = {"name": "John Doe", "age": 30, "city": "New York"}
        # Add a node to the database
        node = add_node(session, node_properties)
        print(f"Node created: {node['n']}")
