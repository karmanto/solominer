#!/bin/bash

# Fungsi untuk memeriksa koneksi internet
check_internet() {
  curl -s --head --fail google.com > /dev/null
  return $?
}

# Fungsi untuk menjalankan file Python
run_python_files() {
  local DIRECTORY=$1
  [ ! -f "$DIRECTORY/.env" ] || export $(grep -v '^#' "$DIRECTORY/.env" | xargs)

  python3 $DIRECTORY/py_solo_listener.py &
  listener_pid=$!

  sleep 2

  for i in $(seq 1 $2)
  do
    python3 $DIRECTORY/py_solo_block.py $i &
    pids[${i}]=$!
  done
}

# Fungsi untuk menghentikan file Python
kill_python_files() {
  kill $listener_pid

  for pid in ${pids[*]}; do
    kill $pid
  done
}

# Fungsi untuk menangkap sinyal SIGINT (Ctrl + C)
on_exit() {
  echo "Menghentikan semua proses Python..."
  kill_python_files
  exit
}

# Menangkap sinyal SIGINT
trap on_exit SIGINT

# Loop utama
while true; do
  if check_internet; then
    echo "Internet tersedia. Menjalankan file Python..."
    run_python_files $1
    while check_internet; do
      sleep 5
    done
    echo ""
    echo "Koneksi internet terputus. Menghentikan file Python..."
    kill_python_files
  else
    # echo "Menunggu koneksi internet..."
    sleep 5
  fi
done
