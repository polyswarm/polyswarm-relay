PROCS=$(pgrep docker-compose)

while read p; do
  sudo kill "$p"
done <<< "$PROCS"
