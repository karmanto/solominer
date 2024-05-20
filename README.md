# Solo Bitcoin Mining with Python and Go

This repository contains a setup for solo mining Bitcoin using a Python listener and a Go-based miner. The mining pool used is [solo.ckpool.org](http://solo.ckpool.org). This guide will walk you through the setup and execution steps for the solo mining process.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- Python 3.x
- Go (Golang) 1.x

## Setup Instructions

1. **Clone the Repository**:

   ```sh
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Build the Go Miner**:

   ```sh
   go build go_solo_block.go
   ```

3. **Create and Configure the Environment File**:

   - Copy the example environment file:
     ```sh
     cp .env.example .env
     ```
   - Open `.env` in your favorite text editor and update the `ADDRESS` with your Bitcoin address and set the `DIRECTORY` path where you want to store log and data files. This directory setting helps avoid errors when running the miner as a cron job.

4. **Run the Mining Process**:
   - Start the mining process with the desired number of workers (e.g., 8 workers):
     ```sh
     sh go_test.sh 8
     ```

## Testing Hashrate

Before you start actual mining, you can test the hashing speed by configuring the environment file.

1. Open the `.env` file.
2. Uncomment the `RANDOM_NONCE` line and set its value to `0`.
3. Comment out the `CYCLE` line.

When `RANDOM_NONCE` is set to `0`, the script will display the hashrate for each worker.

## Additional Notes

- **Logging**: The Python listener logs important events and errors in the `miner.log` file located in the directory specified in the `.env` file.
- **Directory Path**: Ensure the directory path specified in the `.env` file is correct and writable. This is crucial for the smooth operation of the cron job and file handling.
