#!/bin/sh

for d in src/bygg example/ examples/* ; do
  echo
  echo "=== Running mypy in $d ==="
  if [ -d "$d" ] ; then
    .venv/bin/mypy "$d"
  fi
done
