package main

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io/ioutil"
	"math/big"
	mrand "math/rand"
	"os"
	"strconv"
	"strings"
	"time"
)

func logg(msg string, dir string) {
	file, err := os.OpenFile(dir + "/miner.log", os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return
	}
	defer file.Close()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	logMessage := fmt.Sprintf("%s %s\n", timestamp, msg)
	_, err = file.WriteString(logMessage)
	if err != nil {
		return
	}
}

func calculateHashrate(nonce int, lastUpdated time.Time) time.Time {
	if nonce%1000000 == 999999 {
		now := time.Now()
		hashrate := 1000000 / now.Sub(lastUpdated).Seconds()
		hashrateInt := int64(hashrate)
		fmt.Printf("\r%s hash/s", strconv.FormatInt(hashrateInt, 10))
		return now
	}
	
	return lastUpdated
}

func checkStat(argmnt int, dir string) bool {
	for {
		content, err1 := ioutil.ReadFile(dir + "/stat.txt")
		if err1 == nil {
			contentStr := string(content)
			num, err2 := strconv.Atoi(contentStr)
			if err2 == nil {
				if num == argmnt - 1 {
					return true
				} else {
					return false
				}
			}
		}
	}
}

func getData(dir string) string {
	for {
		content, err := ioutil.ReadFile(dir + "/data.txt")
		if err == nil {
			contentStr := string(content)
			return contentStr
		}
	}
}

func generateExtranonce2(size int) (string, error) {
	max := new(big.Int).Lsh(big.NewInt(1), uint(8*size))
	n, err := rand.Int(rand.Reader, max)
	if err != nil {
		return "", err
	}

	extranonce2 := hex.EncodeToString(n.Bytes())
	for len(extranonce2) < 2*size {
		extranonce2 = "0" + extranonce2
	}

	return extranonce2, nil
}

func doubleSHA256(hexString string) (string, error) {
	data, err := hex.DecodeString(hexString)
	if err != nil {
		return "", err
	}

	hash1 := sha256.Sum256(data)
	hash2 := sha256.Sum256(hash1[:])
	return hex.EncodeToString(hash2[:]), nil
}

func reverseBytes(hexString string) (string, error) {
	b, err := hex.DecodeString(hexString)
	if err != nil {
		return "", err
	}

	for i := 0; i < len(b)/2; i++ {
		j := len(b) - i - 1
		b[i], b[j] = b[j], b[i]
	}

	return hex.EncodeToString(b), nil
}

func main() {
	var (
		job_id, coinb1, coinb2, nbits, ntime, prevhash, extranonce1, target, extranonce2, version, nonce string 
		merkle_branch []string
		extranonce2_size int
		lastUpdated time.Time
	)

	breakStat := false
	mineSubmitStat := false
	random_nonce_string := os.Getenv("RANDOM_NONCE")
	dir := os.Getenv("DIRECTORY")
	random_nonce := random_nonce_string == "1"
	max_cycle_string := os.Getenv("CYCLE")
	errorStat := true
	arg := os.Args[1]
	argmnt, err1 := strconv.Atoi(arg)
	max_cycle, err2 := strconv.Atoi(max_cycle_string)
	if err1 == nil && err2 == nil {
		for {
			if checkStat(argmnt, dir) {
				errorStat = true
				lines := strings.Split(getData(dir), "\n")
				if len(lines) >= 15 {
					job_id = lines[0]
					coinb1 = lines[2]
					coinb2 = lines[3]
					merkle_branch = strings.Split(lines[4], ",")
					version = lines[5]
					nbits = lines[6]
					ntime = lines[7]
					prevhash = lines[9]
					extranonce1 = lines[14]
					num4, err1 := strconv.Atoi(lines[13])
					prefix := nbits[:2]
					prefixInt, err2 := strconv.ParseInt(prefix, 16, 64)
					if err1 == nil && err2 == nil && num4 < 20 {
						err3 := ioutil.WriteFile(dir + "/stat.txt", []byte(strconv.Itoa(argmnt)), 0644)
						if err3 == nil {
							errorStat = false
							extranonce2_size = num4
							rest := nbits[2:]
							suffix := strings.Repeat("00", int(prefixInt)-3)
							target = rest + suffix
							target = fmt.Sprintf("%064s", target)
						} 
					} 
				}
			}
	
			for !errorStat {
				extranonce2_temp, err := generateExtranonce2(extranonce2_size)
				if err != nil {
					break
				}

				extranonce2 = extranonce2_temp
				coinbase := coinb1 + extranonce1 + extranonce2 + coinb2
				coinbase_hash, err := doubleSHA256(coinbase)
				if err != nil {
					break
				}

				err_hashing_merkle_branch := false
				merkle_root := coinbase_hash
				for _, merkle_single := range merkle_branch {
					hash_temp, err := doubleSHA256(merkle_root + merkle_single)
					if err != nil {
						err_hashing_merkle_branch = true
						break
					}
					merkle_root = hash_temp
				}

				if err_hashing_merkle_branch {
					break
				}

				little_endian_merkle, err1 := reverseBytes(merkle_root)
				little_endian_version, err2 := reverseBytes(version)
				little_endian_ntime, err3 := reverseBytes(ntime)
				little_endian_nbits, err4 := reverseBytes(nbits)
				little_endian_prevhash, err5 := reverseBytes(prevhash)
				if err1 != nil || err2 != nil || err3 != nil || err4 != nil || err5 != nil {
					break
				}

				partialheader := little_endian_version + little_endian_prevhash + little_endian_merkle + little_endian_ntime + little_endian_nbits
				nNonce := 0
				cycleBack := 0
				lastUpdated = time.Now()

				for {
					if random_nonce {
						randomValue := mrand.Uint32()
						nonce_temp := fmt.Sprintf("%08x", randomValue)
						nonce = nonce_temp
					} else {
						hexnNonce := strconv.FormatUint(uint64(nNonce), 16)
						nonce = fmt.Sprintf("%08s", strings.ToUpper(hexnNonce))
					}

					little_endian_nonce, err := reverseBytes(nonce)
					if err != nil {
						breakStat = true
						break
					}

					blockheader := partialheader + little_endian_nonce
					hash_temp, err := doubleSHA256(blockheader)
					if err != nil {
						breakStat = true
						break
					}

					numZeros := len(hash_temp) - len(strings.TrimRight(hash_temp, "0"))
					if numZeros >= 8 && !mineSubmitStat {
						mineSubmitStat = true
						hash, err := reverseBytes(hash_temp)
						if err != nil {
							breakStat = true
							break
						}

						logg(
							fmt.Sprintf("[*] Zero length : %d New hash: %s target: %s extranonce %s nonce %s",
							numZeros, hash, target, extranonce2, nonce), dir)

						fmt.Printf("\rZero length: %d hash: %s extranonce %s nonce %s jobid %s \n", numZeros, hash, extranonce2, nonce, job_id)
						
						intHash, _ := new(big.Int).SetString(hash, 16)
						intTarget, _ := new(big.Int).SetString(target, 16)

						if intHash.Cmp(intTarget) == -1 {
							sendString := blockheader + "\n" + job_id + "\n" + extranonce2 + "\n" + ntime + "\n" + nonce
							_ = ioutil.WriteFile(dir + "/result.txt", []byte(sendString), 0644)
						}
					} else if numZeros >= 4 && random_nonce {
						hash, err := reverseBytes(hash_temp)
						if err != nil {
							breakStat = true
							break
						}
						
						fmt.Printf("\rZero length: %d hash: %s extranonce %s nonce %s jobid %s ", numZeros, hash, extranonce2, nonce, job_id)
					}

					if !random_nonce {
						lastUpdated = calculateHashrate(nNonce, lastUpdated)
					}

					nNonce += 1
					if cycleBack == max_cycle {
						breakStat = true
						break
					}

					cycleBack += 1
				}

				if breakStat {
					breakStat = false
					break
				}

			}
	
		}
	}
}