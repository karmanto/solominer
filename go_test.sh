#!/bin/bash

check_internet() {
  curl -s --head --fail google.com > /dev/null
  if [ $? -ne 0 ]; then
    printf "\rKoneksi internet terputus. Menghentikan file Python dan Go...                                                                                                                            "
  fi
  return $?
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

check_time_difference() {
  last_line=$(tail -n 1 "$DIRECTORY/data.txt")

  last_time=$(date -d "$last_line" +%s 2>/dev/null)

  if [ $? -ne 0 ]; then
    printf \r"Baris terakhir bukan datetime yang valid. Restart file Python dan Go...                                                                                                                  "
    return 1
  fi

  current_time=$(date +%s)
  time_diff=$(( (current_time - last_time) / 60 ))

  if [ $time_diff -gt 20 ]; then
    printf "\rWaktu socket lebih dari 20 menit dari waktu sekarang. Restart file Python dan Go...                                                                                                      "
    return 1
  fi

  return 0
}

trap on_exit SIGINT

DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

while true; do
  if check_internet; then
    printf "\rInternet tersedia. Menjalankan file Python dan Go...                                                                                                                                     "
    run_python_files $1
    sleep 5

    while check_internet && check_time_difference; do
      sleep 5
    done

    kill_python_files
  else
    sleep 5
  fi
done
