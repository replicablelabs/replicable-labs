"""Knowledge graph: Neo4j. (:Entity {key,label}) -[:REL {relation, card_id}]-> (:Entity). Every edge records its source card.
Relationship type is generic (:REL) with the verb stored as a property, so no APOC is needed for dynamic types."""
from __future__ import annotations
import re
from neo4j import GraphDatabase
from .models import Triple

class Neo4jGraph:
    def __init__(self, uri: str, user: str, password: str, driver=None):
        self.d = driver or GraphDatabase.driver(uri, auth=(user, password))
        self._run("CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE")

    def close(self) -> None: self.d.close()

    def _run(self, query: str, **params) -> list[dict]:
        return [r.data() for r in self.d.execute_query(query, parameters_=params).records]

    def add_triples(self, card_id: str, triples: list[Triple]) -> None:
        rows = [{"s": t.subject, "sk": t.subject.lower(), "rel": t.relation, "o": t.object, "ok": t.object.lower()} for t in triples]
        self._run("""UNWIND $rows AS r
                     MERGE (a:Entity {key: r.sk}) ON CREATE SET a.label = r.s
                     MERGE (b:Entity {key: r.ok}) ON CREATE SET b.label = r.o
                     CREATE (a)-[:REL {relation: r.rel, card_id: $card_id}]->(b)""", rows=rows, card_id=card_id)

    def delete_card(self, card_id: str) -> None:
        self._run("MATCH ()-[r:REL {card_id: $c}]->() DELETE r", c=card_id)
        self._run("MATCH (e:Entity) WHERE NOT (e)--() DELETE e")   # drop orphan entities

    def link_entities(self, query: str, exclude=()) -> list[str]:
        """Entity linking: entity keys appearing as whole words in the query (Cypher CONTAINS prefilter + word-boundary check)."""
        rows = self._run("""MATCH (e:Entity) WHERE $q CONTAINS e.key
                            AND EXISTS { MATCH (e)-[r:REL]-() WHERE NOT r.card_id IN $ex }
                            RETURN e.key AS key""", q=query.lower(), ex=list(exclude))
        q = query.lower()
        return sorted(r["key"] for r in rows if re.search(rf"(?<!\w){re.escape(r['key'])}(?!\w)", q))

    def neighborhood(self, seeds: list[str], hops: int, exclude=()) -> list[dict]:
        """Triples whose both ends lie within `hops` of a seed (undirected reach), skipping edges of excluded cards."""
        hops = int(hops)   # Cypher cannot parameterise path length; it is an int we validated
        return self._run(f"""MATCH (s:Entity) WHERE s.key IN $seeds
                             MATCH (s)-[rs:REL*0..{hops}]-(n:Entity) WHERE ALL(r IN rs WHERE NOT r.card_id IN $ex)
                             WITH collect(DISTINCT n) AS reach
                             UNWIND reach AS a
                             MATCH (a)-[r:REL]->(b) WHERE b IN reach AND NOT r.card_id IN $ex
                             RETURN a.label AS subject, r.relation AS relation, b.label AS object, r.card_id AS card_id,
                                    a.key AS subject_key, b.key AS object_key
                             ORDER BY card_id, subject_key, relation, object_key""", seeds=seeds, ex=list(exclude))

    def stats(self) -> tuple[int, int]:
        n = self._run("MATCH (e:Entity) RETURN count(e) AS n")[0]["n"]
        return n, self._run("MATCH ()-[r:REL]->() RETURN count(r) AS n")[0]["n"]

    def edges(self) -> list[dict]:
        return self._run("""MATCH (a:Entity)-[r:REL]->(b:Entity)
                            RETURN a.label AS subject, r.relation AS relation, b.label AS object, r.card_id AS card_id
                            ORDER BY card_id, subject, relation, object""")

    def triples_of(self, card_id: str) -> list[Triple]:
        return [Triple(subject=r["subject"], relation=r["relation"], object=r["object"]) for r in
                self._run("""MATCH (a:Entity)-[r:REL {card_id: $c}]->(b:Entity)
                             RETURN a.label AS subject, r.relation AS relation, b.label AS object""", c=card_id)]
