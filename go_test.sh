#!/bin/bash

check_internet() {
  curl -s --head --fail google.com > /dev/null
  return $?
}

check_force_restart() {
  if [ -f "$DIRECTORY/forceRestart.txt" ]; then
    if [ "$(cat "$DIRECTORY/forceRestart.txt")" -eq 1 ]; then
      echo "0" > "$DIRECTORY/forceRestart.txt"
      return 1
    fi
  fi
  return 0
}

run_python_files() {
  if [ -f "$DIRECTORY/.env" ]; then
    export $(grep -v '^#' "$DIRECTORY/.env" | xargs)
  fi

  python3 "$DIRECTORY/go_solo_listener.py" &
  listener_pid=$!

  sleep 2

  for i in $(seq 1 $1)
  do
    core=$(( (i-1) % 4 ))
    
    taskset -c $core "$DIRECTORY/go_solo_block" $i &
    pids[${i}]=$!
  done
}

kill_python_files() {
  kill $listener_pid

  for pid in ${pids[*]}; do
    kill $pid
  done
}

on_exit() {
  echo "Menghentikan semua proses Python..."
  kill_python_files
  exit
}

trap on_exit SIGINT

DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

while true; do
  if check_internet && check_force_restart; then
    printf "\rInternet tersedia dan forceRestart tidak aktif. Menjalankan file Python dan Go...                                                                                                        "
    run_python_files $1
    while check_internet && check_force_restart; do
      sleep 5
    done
    kill_python_files
    printf "\rKoneksi internet terputus atau forceRestart aktif. Menghentikan file Python dan Go...                                                                                                    "
  else
    sleep 5
  fi
done
