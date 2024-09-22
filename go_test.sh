#!/bin/bash

run_node_files() {
  if [ -f "$DIRECTORY/.env" ]; then
    export $(grep -v '^#' "$DIRECTORY/.env" | xargs)
  fi

  node "$DIRECTORY/app" &
  listener_pid=$!

  sleep 2

  for i in $(seq 1 $1)
  do
    core=$(( (i-1) % 4 ))
    
    taskset -c $core "$DIRECTORY/go_solo_block" $i &
    pids[${i}]=$!
  done
}

kill_node_files() {
  kill $listener_pid

  for pid in ${pids[*]}; do
    kill $pid
  done
}

on_exit() {
  echo "Menghentikan semua proses Node..."
  kill_node_files
  exit
}

trap on_exit SIGINT

DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

run_node_files $1

while true; do
  :
done
