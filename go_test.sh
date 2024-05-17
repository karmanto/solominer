#!/bin/bash

# Fungsi untuk memeriksa koneksi internet
check_internet() {
  curl -s --head --fail google.com > /dev/null
  return $?
}

# Fungsi untuk menjalankan file Python
run_python_files() {
  python3 go_solo_listener.py &
  listener_pid=$!

  sleep 2

  for i in $(seq 1 $1)
  do
    ./go_solo_block $i &
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
    echo "Internet tersedia. Menjalankan file Python dan Go..."
    run_python_files $1
    while check_internet; do
      sleep 5
    done
    echo ""
    echo "Koneksi internet terputus. Menghentikan file Python dan Go..."
    kill_python_files
  else
    # echo "Menunggu koneksi internet..."
    sleep 5
  fi
done
