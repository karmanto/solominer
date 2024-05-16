package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	maxCycle     = 100000
	randomNonce  = true
)

func logg(msg string) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	ioutil.WriteFile("miner.log", []byte(fmt.Sprintf("%s %s\n", timestamp, msg)), 0644)
}

func calculateHashrate(nonce int, lastUpdated time.Time) time.Time {
	if nonce%1000000 == 999999 {
		now := time.Now()
		hashrate := 1000000 / now.Sub(lastUpdated).Seconds()
		fmt.Printf("\r%s hash/s", strconv.FormatFloat(hashrate, 'f', 6, 64))
		return now
	}
	return lastUpdated
}

func bitcoinMiner() {
	var (
		jobID            string
		coinb1           string
		coinb2           string
		merkleBranch     []string
		nbits            string
		ntime            string
		prevHashLE       string
		ntimeLE          uint32
		nbitsLE          uint32
		extranonce2Size  int
		extranonce1      string
		address          string
		firstStart       = true
	)

	for {
		stat, _ := ioutil.ReadFile("stat.txt")
		if s, _ := strconv.Atoi(string(stat)); s == os.Args[1] {
			firstStart = false
			ioutil.WriteFile("stat.txt", []byte(os.Args[1]), 0644)

			data, _ := ioutil.ReadFile("data.txt")
			lines := strings.Split(string(data), "\n")
			jobID = lines[0]
			coinb1 = lines[2]
			coinb2 = lines[3]
			merkleBranch = strings.Split(lines[4], ",")
			nbits = lines[6]
			ntime = lines[7]
			prevHashLE = lines[9]
			versionLE, _ := strconv.Atoi(lines[10])
			ntimeLE = uint32(ntimeLE)
			nbitsLE = uint32(nbitsLE)
			extranonce2Size, _ = strconv.Atoi(lines[13])
			extranonce1 = lines[14]
			address = lines[15]
		}

		if !firstStart {
			target := nbits[2:] + strings.Repeat("00", int(nbits[:2], 16)-3)
			target = strings.Repeat("0", 64-len(target)) + target
			extranonce2 := fmt.Sprintf("%016x", rand.Int63n(1<<64-1))

			coinbase := coinb1 + extranonce1 + extranonce2 + coinb2
			coinbaseHashBin := sha256.Sum256([]byte(coinbase))

			merkleRoot := coinbaseHashBin[:]
			for _, h := range merkleBranch {
				hBytes, _ := hex.DecodeString(h)
				merkleRoot = append(merkleRoot, hBytes...)
				merkleRoot = sha256.Sum256(merkleRoot[:]).[:]
			}

			merkleRootHex := hex.EncodeToString(merkleRoot)
			merkleRootHex = reverseHex(merkleRootHex)

			partialHeader := make([]byte, 20)
			binary.LittleEndian.PutUint32(partialHeader, uint32(versionLE))
			copy(partialHeader[4:], []byte(prevHashLE))
			copy(partialHeader[8:], []byte(merkleRootHex))
			binary.LittleEndian.PutUint32(partialHeader[16:], ntimeLE)
			binary.LittleEndian.PutUint32(partialHeader[20:], nbitsLE)

			var nNonce int
			var cycleBack int

			lastUpdated := time.Now()

			for {
				var nonce string
				if randomNonce {
					nonce = fmt.Sprintf("%08x", rand.Int31n(1<<32-1))
				} else {
					nonce = fmt.Sprintf("%08x", nNonce)
				}

				nonceLE := make([]byte, 4)
				binary.LittleEndian.PutUint32(nonceLE, uint32(nonce))

				blockheader := append(partialHeader, nonceLE...)
				hash := sha256.Sum256(blockheader)
				hash = sha256.Sum256(hash[:])
				hashHex := hex.EncodeToString(hash[:])

				if strings.HasPrefix(hashHex, "00000000") {
					numZeros := len(hashHex) - len(strings.TrimLeft(hashHex, "0"))
					logg(fmt.Sprintf("[*] Zero length : %d New hash: %s target: %s extranonce %s nonce %s", numZeros, hashHex, target, extranonce2, nonce))
					fmt.Printf("\r%s Zero length: %d hash: %s extranonce %s ", time.Now(), numZeros, hashHex, extranonce2)
				} else if strings.HasPrefix(hashHex, "0000") && randomNonce {
					now := time.Now()
					numZeros := len(hashHex) - len(strings.TrimLeft(hashHex, "0"))
					fmt.Printf("\r%s Zero length: %d hash: %s extranonce %s nonce %s", now, numZeros, hashHex, extranonce2, nonce)
				}

				if !randomNonce {
					lastUpdated = calculateHashrate(nNonce, lastUpdated)
				}

				if hashHex < target {
					logg("[*] Block solved.")
					logg(fmt.Sprintf("[*] Block hash: %s", hashHex))
					logg(fmt.Sprintf("[*] Blockheader: %s", blockheader))
					payload := fmt.Sprintf("{\"params\": [\"%s\", \"%s\", \"%s\", \"%s\", \"%s\"], \"id\": 1, \"method\": \"mining.submit\"}\n", address, jobID, extranonce2, ntime, nonce)
					logg(fmt.Sprintf("[*] Payload: %s", payload))

					sock, _ := net.Dial("tcp", "solo.ckpool.org:3333")
					sock.Write([]byte(payload))
					ret := make([]byte, 1024)
					sock.Read(ret)
					sock.Close()
					logg(fmt.Sprintf("[*] Pool response: %s", ret))
				}

				nNonce++

				if cycleBack == maxCycle {
					break
				}

				cycleBack++
			}
		}
	}
}

func main() {
	bitcoinMiner()
}

func reverseHex(s string) string {
	b, _ := hex.DecodeString(s)
	for i := len(b)/2 - 1; i >= 0; i-- {
		opp := len(b) - 1 - i
		b[i], b[opp] = b[opp], b[i]
	}
	return hex.EncodeToString(b)
}
