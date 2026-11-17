"""Real storage: ONE SQLite file, no server, nothing held in memory.

  cards / attempts ........ ordinary tables
  triples ................. the GRAPH: each row is an edge (subject_key -> object_key) tagged with its card_id.
                            k-hop traversal = a recursive CTE. Nodes are implicit (distinct keys).
  card_vec (sqlite-vec) ... the VECTORS: vec0 virtual table, cosine KNN on disk.
  meta .................... which embedder/dimension built this file (mismatch => refuse, not silently wrong)

Production equivalents to name in an interview: Postgres + pgvector (vectors) and Neo4j / Apache AGE (graph).
"""
from __future__ import annotations
import json, re, sqlite3, struct
from pathlib import Path
import sqlite_vec
from .models import Attempt, Card, Triple

SCHEMA = """
create table if not exists meta(key text primary key, value text not null);
create table if not exists cards(
  id text primary key, question text not null, answer text not null,
  prerequisite_of text references cards(id), created_at text not null);
create table if not exists triples(
  id integer primary key autoincrement, card_id text not null references cards(id) on delete cascade,
  subject text not null, relation text not null, object text not null,
  subject_key text not null, object_key text not null);
create index if not exists ix_triples_card on triples(card_id);
create index if not exists ix_triples_s on triples(subject_key);
create index if not exists ix_triples_o on triples(object_key);
create table if not exists attempts(
  id integer primary key autoincrement, card_id text not null references cards(id),
  user_answer text not null, score real not null, verdict text not null, feedback text not null, at text not null);
"""

def _pack(v: list[float]) -> bytes: return struct.pack(f"{len(v)}f", *v)
def _unpack(b: bytes) -> list[float]: return list(struct.unpack(f"{len(b) // 4}f", b))
def _j(items) -> str: return json.dumps(sorted(items))   # bound into json_each(?) -> safe IN-lists

class CardStore:
    def __init__(self, path: Path | str, embedder_name: str, dim: int):
        if str(path) != ":memory:": Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.enable_load_extension(True); sqlite_vec.load(self.db); self.db.enable_load_extension(False)
        self.db.execute("pragma foreign_keys = on"); self.db.execute("pragma journal_mode = wal")
        self.db.executescript(SCHEMA)
        meta = dict(self.db.execute("select key, value from meta").fetchall())
        if meta and (meta["embedder"], int(meta["dim"])) != (embedder_name, dim):
            raise ValueError(f"{path} was built with embedder '{meta['embedder']}' (dim {meta['dim']}), but you are using "
                             f"'{embedder_name}' (dim {dim}). Use the same --embedder, a different --db, or delete the file.")
        if not meta:
            with self.db:
                self.db.executemany("insert into meta values(?,?)", [("embedder", embedder_name), ("dim", str(dim))])
        self.db.execute(f"create virtual table if not exists card_vec using vec0("
                        f"card_id text primary key, embedding float[{dim}] distance_metric=cosine)")
        self.db.commit()

    def close(self) -> None: self.db.close()

    # ---- cards (+ vector + graph edges, atomically) ----
    def add(self, card: Card, vector: list[float], triples: list[Triple]) -> None:
        with self.db:  # one transaction: all or nothing
            self.db.execute("insert into cards values(?,?,?,?,?)",
                            (card.id, card.question, card.answer, card.prerequisite_of, card.created_at.isoformat()))
            self.db.executemany(
                "insert into triples(card_id,subject,relation,object,subject_key,object_key) values(?,?,?,?,?,?)",
                [(card.id, t.subject, t.relation, t.object, t.subject.lower(), t.object.lower()) for t in triples])
            self.db.execute("insert into card_vec(card_id, embedding) values(?,?)", (card.id, _pack(vector)))

    def has(self, card_id: str) -> bool:
        return self.db.execute("select 1 from cards where id=?", (card_id,)).fetchone() is not None

    @staticmethod
    def _card(r: sqlite3.Row) -> Card:
        return Card(id=r["id"], question=r["question"], answer=r["answer"], prerequisite_of=r["prerequisite_of"], created_at=r["created_at"])

    def get(self, card_id: str) -> Card:
        r = self.db.execute("select * from cards where id=?", (card_id,)).fetchone()
        if r is None: raise KeyError(card_id)
        return self._card(r)

    def cards(self) -> list[Card]:
        return [self._card(r) for r in self.db.execute("select * from cards order by created_at, rowid")]

    def count(self) -> int: return self.db.execute("select count(*) from cards").fetchone()[0]

    def vector_of(self, card_id: str) -> list[float] | None:
        r = self.db.execute("select embedding from card_vec where card_id=?", (card_id,)).fetchone()
        return _unpack(r[0]) if r else None

    def triples_of(self, card_id: str) -> list[Triple]:
        return [Triple(subject=r["subject"], relation=r["relation"], object=r["object"])
                for r in self.db.execute("select * from triples where card_id=? order by id", (card_id,))]

    # ---- vector side ----
    def search(self, vec: list[float], k: int, exclude=()) -> list[tuple[Card, float]]:
        rows = self.db.execute("select card_id, distance from card_vec where embedding match ? and k = ?",
                               (_pack(vec), k + len(exclude))).fetchall()
        out = [(self.get(r["card_id"]), 1 - r["distance"]) for r in rows if r["card_id"] not in set(exclude)]
        return sorted(out, key=lambda x: (-x[1], x[0].id))[:k]

    # ---- graph side ----
    def link_entities(self, query: str, exclude=()) -> list[str]:
        """Entity linking: node keys that appear (as whole words) in the query. SQL prefilter + word-boundary check."""
        rows = self.db.execute(
            "select distinct k from (select subject_key k, card_id from triples union all select object_key, card_id from triples) "
            "where instr(?, k) > 0 and card_id not in (select value from json_each(?))", (query.lower(), _j(exclude))).fetchall()
        return sorted(r["k"] for r in rows if re.search(rf"(?<!\w){re.escape(r['k'])}(?!\w)", query.lower()))

    def neighborhood(self, seeds: list[str], hops: int, exclude=()) -> list[sqlite3.Row]:
        """All triples whose both ends are within `hops` of a seed (edges treated as undirected for reach)."""
        return self.db.execute("""
            with recursive
              edges(s, o) as (select subject_key, object_key from triples
                              where card_id not in (select value from json_each(:ex))),
              reach(n, d) as (
                select value, 0 from json_each(:seeds)
                union
                select case when e.s = reach.n then e.o else e.s end, reach.d + 1
                from reach join edges e on e.s = reach.n or e.o = reach.n
                where reach.d < :hops)
            select subject, relation, object, card_id, subject_key, object_key from triples
            where card_id not in (select value from json_each(:ex))
              and subject_key in (select n from reach) and object_key in (select n from reach)
            order by id""", {"seeds": _j(seeds), "hops": hops, "ex": _j(exclude)}).fetchall()

    def stats(self) -> tuple[int, int]:
        n = self.db.execute("select count(*) from (select subject_key k from triples union select object_key from triples)").fetchone()[0]
        return n, self.db.execute("select count(*) from triples").fetchone()[0]

    def edges(self) -> list[sqlite3.Row]: return self.db.execute("select * from triples order by id").fetchall()

    # ---- attempts + scheduler ----
    def record(self, a: Attempt) -> None:
        with self.db:
            self.db.execute("insert into attempts(card_id,user_answer,score,verdict,feedback,at) values(?,?,?,?,?,?)",
                            (a.card_id, a.user_answer, a.score, a.verdict, a.feedback, a.at.isoformat()))

    def attempts(self, card_id: str | None = None) -> list[Attempt]:
        q, args = ("select * from attempts where card_id=? order by id", (card_id,)) if card_id else ("select * from attempts order by id", ())
        return [Attempt(card_id=r["card_id"], user_answer=r["user_answer"], score=r["score"], verdict=r["verdict"],
                        feedback=r["feedback"], at=r["at"]) for r in self.db.execute(q, args)]

    def mean_score(self, card_id: str) -> float | None:
        return self.db.execute("select avg(score) from attempts where card_id=?", (card_id,)).fetchone()[0]

    def next_card(self, mode: str, exclude=()) -> Card | None:
        order = "c.created_at, c.rowid" if mode == "study" else "coalesce(avg_s, -1), c.created_at, c.rowid"  # exercise: never-attempted, then weakest
        r = self.db.execute(f"select c.*, (select avg(score) from attempts a where a.card_id = c.id) avg_s from cards c "
                            f"where c.id not in (select value from json_each(?)) order by {order} limit 1", (_j(exclude),)).fetchone()
        return self._card(r) if r else None
