#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
jar_path="target/limpador-pc-1.0.0.jar"

if ! command -v java >/dev/null 2>&1; then
  echo "Java 21 nao foi encontrado no PATH. Instale o JDK 21 e tente novamente." >&2
  exit 1
fi

if [[ ! -f "$jar_path" ]]; then
  if ! command -v mvn >/dev/null 2>&1; then
    echo "O JAR nao existe e Maven nao foi encontrado no PATH." >&2
    exit 1
  fi
  mvn clean package
fi

exec java -jar "$jar_path"
