"""Relational store: PostgreSQL. Cards, attempts, and `meta` (pins the embedder). The source of truth for card identity."""
from __future__ import annotations
import psycopg
from psycopg.rows import dict_row
from .models import Attempt, Card

SCHEMA = """
create table if not exists meta(key text primary key, value text not null);
create table if not exists cards(
  id text primary key, question text not null, answer text not null,
  prerequisite_of text references cards(id) on delete set null,
  created_at timestamptz not null default now());
create table if not exists attempts(
  id bigserial primary key, card_id text not null references cards(id) on delete cascade,
  user_answer text not null, score double precision not null check (score between 0 and 1),
  verdict text not null, feedback text not null, at timestamptz not null default now());
create index if not exists ix_attempts_card on attempts(card_id);
"""

class PostgresCards:
    def __init__(self, url: str):
        self.conn = psycopg.connect(url, autocommit=True, row_factory=dict_row)
        self.conn.execute(SCHEMA)

    def close(self) -> None: self.conn.close()

    def get_meta(self, key: str) -> str | None:
        r = self.conn.execute("select value from meta where key=%s", (key,)).fetchone()
        return r["value"] if r else None

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute("insert into meta values(%s,%s) on conflict (key) do update set value=excluded.value", (key, value))

    def add(self, c: Card) -> None:
        self.conn.execute("insert into cards(id,question,answer,prerequisite_of,created_at) values(%s,%s,%s,%s,%s)",
                          (c.id, c.question, c.answer, c.prerequisite_of, c.created_at))

    def delete(self, card_id: str) -> None: self.conn.execute("delete from cards where id=%s", (card_id,))
    def has(self, card_id: str) -> bool:
        return self.conn.execute("select 1 from cards where id=%s", (card_id,)).fetchone() is not None

    @staticmethod
    def _card(r) -> Card:
        return Card(id=r["id"], question=r["question"], answer=r["answer"], prerequisite_of=r["prerequisite_of"], created_at=r["created_at"])

    def get(self, card_id: str) -> Card:
        r = self.conn.execute("select * from cards where id=%s", (card_id,)).fetchone()
        if r is None: raise KeyError(card_id)
        return self._card(r)

    def all(self) -> list[Card]:
        return [self._card(r) for r in self.conn.execute("select * from cards order by created_at, id")]

    def count(self) -> int: return self.conn.execute("select count(*) as n from cards").fetchone()["n"]

    def record(self, a: Attempt) -> None:
        self.conn.execute("insert into attempts(card_id,user_answer,score,verdict,feedback,at) values(%s,%s,%s,%s,%s,%s)",
                          (a.card_id, a.user_answer, a.score, a.verdict, a.feedback, a.at))

    def attempts(self, card_id: str | None = None) -> list[Attempt]:
        rows = (self.conn.execute("select * from attempts where card_id=%s order by id", (card_id,)) if card_id
                else self.conn.execute("select * from attempts order by id")).fetchall()
        return [Attempt(card_id=r["card_id"], user_answer=r["user_answer"], score=r["score"], verdict=r["verdict"],
                        feedback=r["feedback"], at=r["at"]) for r in rows]

    def mean_score(self, card_id: str) -> float | None:
        return self.conn.execute("select avg(score) as m from attempts where card_id=%s", (card_id,)).fetchone()["m"]

    def next_card(self, mode: str, exclude=()) -> Card | None:
        order = "created_at, id" if mode == "study" else "coalesce(avg_s, -1), created_at, id"  # exercise: never-attempted, then weakest
        r = self.conn.execute(
            "select * from (select c.*, (select avg(score) from attempts a where a.card_id = c.id) as avg_s from cards c "
            f"where not (c.id = any(%s))) t order by {order} limit 1", (list(exclude),)).fetchone()
        return self._card(r) if r else None
