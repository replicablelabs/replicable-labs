#!/usr/bin/env bash
# Local Postgres (:5433) + Qdrant (:6333) + Neo4j (:7687). No Docker. Data lives under <lab>/.data (gitignored),
# except Neo4j (Homebrew's own data dir). 5432 is deliberately NOT used (often an ssh tunnel).
#   scripts/services.sh install | start | stop | status
set -euo pipefail
LAB="$(cd "$(dirname "$0")/.." && pwd)"; D="$LAB/.data"
PG_BIN="$(brew --prefix postgresql@16)/bin"; PGDATA="$D/pg"; PGPORT=5433
QD_VER="${QDRANT_VERSION:-v1.20.2}"; QD_BIN="$D/qdrant-bin/qdrant"
export JAVA_HOME="$(brew --prefix openjdk@21)/libexec/openjdk.jdk/Contents/Home"
NEO_PW="${NEO4J_PASSWORD:-agentone-local}"

install() {
  brew list postgresql@16 >/dev/null 2>&1 || brew install postgresql@16
  brew list neo4j >/dev/null 2>&1 || brew install neo4j
  if [ ! -x "$QD_BIN" ]; then  # Qdrant has no Homebrew formula: official release binary
    mkdir -p "$D/qdrant-bin"; t="$(mktemp -d)"
    curl -fsSL -o "$t/q.tgz" "https://github.com/qdrant/qdrant/releases/download/$QD_VER/qdrant-aarch64-apple-darwin.tar.gz"
    tar -xzf "$t/q.tgz" -C "$D/qdrant-bin"; rm -rf "$t"
  fi
  if [ ! -d "$PGDATA" ]; then "$PG_BIN/initdb" -D "$PGDATA" -A trust -U "$USER" >/dev/null; fi
}
start() {
  mkdir -p "$D/qdrant-run" "$D/qdrant-storage"
  "$PG_BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1 || "$PG_BIN/pg_ctl" -D "$PGDATA" -l "$D/pg.log" -o "-p $PGPORT -k /tmp" -w start
  "$PG_BIN/psql" -h localhost -p $PGPORT -d postgres -tc "select 1 from pg_database where datname='agentone'" | grep -q 1 \
    || "$PG_BIN/createdb" -h localhost -p $PGPORT agentone
  if ! nc -z localhost 6333 2>/dev/null; then
    (cd "$D/qdrant-run" && QDRANT__STORAGE__STORAGE_PATH="$D/qdrant-storage" QDRANT__SERVICE__ENABLE_STATIC_CONTENT=false \
      nohup "$QD_BIN" > "$D/qdrant.log" 2>&1 &)
  fi
  if [ ! -f "$D/.neo4j-pw-set" ]; then neo4j-admin dbms set-initial-password "$NEO_PW" >/dev/null 2>&1 && touch "$D/.neo4j-pw-set" || true; fi
  neo4j status >/dev/null 2>&1 || neo4j start
  status
}
stop() {
  neo4j stop || true
  pkill -f "$QD_BIN" || true
  "$PG_BIN/pg_ctl" -D "$PGDATA" stop || true
}
status() { for p in "postgres:$PGPORT" "qdrant:6333" "neo4j:7687"; do n=${p%%:*}; nc -z localhost ${p##*:} 2>/dev/null && echo "up    $p" || echo "DOWN  $p"; done; }
"${1:-status}"
