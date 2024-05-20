# Distributed under the MIT/X11 software license, see the accompanying
# file license http://www.opensource.org/licenses/mit-license.php.



import binascii
import hashlib
import logging
import random
import socket
import time
import sys
import time
from datetime import datetime
import struct
import os



def load_env(file_path):
    with open(file_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

load_env('.env')



maxCycle = int(os.getenv("CYCLE", "100000"))
random_nonce = os.getenv("RANDOM_NONCE") == '1'
dir = os.getenv("DIRECTORY", "")
address = os.getenv("ADDRESS", "1NStyxyH5hFc3Bj7d4D2VKktx2bqdVuEBF")



def logg(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(dir + '/miner.log', 'a') as file:
        file.write(f'{timestamp} {msg}\n')


def calculate_hashrate(nonce, last_updated):
  if nonce % 1000000 == 999999:
    now             = time.time()
    hashrate        = round(1000000/(now - last_updated))
    sys.stdout.write("\r%s hash/s"%(str(hashrate)))
    sys.stdout.flush()
    return now
  else:
    return last_updated



def bitcoin_miner():
    job_id = ""
    coinb1 = ""
    coinb2 = ""
    merkle_branch = []
    nbits = ""
    ntime = ""
    prevHashLE = ""
    versionLE = 0
    ntimeLE = 0
    nbitsLE = 0
    extranonce2_size = 0
    extranonce1 = ""
    address = ""
    firstStart = True

    while True:
        f = open(dir + "/stat.txt", "r")
        stat = f.read()
        f.close()
        if stat and int(stat) == int(sys.argv[1]) - 1 :
            firstStart = False
            f = open(dir + "/stat.txt", "w")
            f.write(str(sys.argv[1]))
            f.close()

            f = open(dir + "/data.txt", "r")
            data = f.read()
            f.close()
            lines = data.splitlines()
            job_id = lines[0]
            coinb1 = lines[2]
            coinb2 = lines[3]
            merkle_branch = lines[4].split(",")
            nbits = lines[6]
            ntime = lines[7]
            prevHashLE = lines[9]
            versionLE = int(lines[10])
            ntimeLE = int(lines[11])
            nbitsLE = int(lines[12])
            extranonce2_size = int(lines[13])
            extranonce1 = lines[14]

        if not firstStart:
            target = (nbits[2:]+'00'*(int(nbits[:2],16) - 3)).zfill(64)
            extranonce2 = hex(random.randint(0,2**64-1))[2:].zfill(2*extranonce2_size) 

            coinbase = coinb1 + extranonce1 + extranonce2 + coinb2
            coinbase_hash_bin = hashlib.sha256(hashlib.sha256(binascii.unhexlify(coinbase)).digest()).digest()

            merkle_root = coinbase_hash_bin
            for h in merkle_branch:
                merkle_root = hashlib.sha256(hashlib.sha256(merkle_root + binascii.unhexlify(h)).digest()).digest()

            merkle_root = binascii.hexlify(merkle_root).decode()

            #little endian
            merkle_root = ''.join([merkle_root[i]+merkle_root[i+1] for i in range(0,len(merkle_root),2)][::-1])

            partialheader = struct.pack("<L", versionLE) \
                                + bytes.fromhex(prevHashLE)[::-1] \
                                + bytes.fromhex(merkle_root) \
                                + struct.pack("<L", ntimeLE) \
                                + struct.pack("<L", nbitsLE)

            nNonce = 0
            cycleBack = 0

            last_updated = int(time.time())

            while True: 
                if random_nonce:
                    nonce = hex(random.randint(0,2**32-1))[2:].zfill(8) # nNonce   #hex(int(nonce,16)+1)[2:]
                else:
                    nonce = hex(nNonce)[2:].zfill(8)

                nonceLE = struct.pack("<L", int(nonce, 16))

                blockheader = partialheader + nonceLE
                hash = hashlib.sha256(hashlib.sha256(blockheader).digest()).digest()
                hash = binascii.hexlify(hash[::-1]).decode()

                # Logg all hashes that start with 8 zeros or more
                
                if hash.startswith('00000000'): 
                    now = datetime.now()
                    num_zeros = len(hash) - len(hash.lstrip('0'))
                    logg('[*] Zero length : {} New hash: {} target: {} extranonce {} nonce {}'.format(num_zeros, hash, target, extranonce2, nonce))
                    print("\r%s Zero length: %s hash: %s extranonce %s "%(now, num_zeros, hash, extranonce2))
                elif hash.startswith('0000') and random_nonce:
                    now = datetime.now()
                    num_zeros = len(hash) - len(hash.lstrip('0'))
                    sys.stdout.write("\r%s Zero length: %s hash: %s extranonce %s nonce %s"%(now, num_zeros, hash, extranonce2, nonce))
                    sys.stdout.flush()

                if not random_nonce:
                    # hash meter, only works with regular nonce.
                    last_updated = calculate_hashrate(nNonce, last_updated)

                if hash < target :
                    logg('[*] Block solved.'.format())
                    logg('[*] Block hash: {}'.format(hash))
                    logg('[*] Blockheader: {}'.format(blockheader))            
                    payload = bytes('{"params": ["'+address+'", "'+job_id+'", "'+extranonce2 \
                        +'", "'+ntime+'", "'+nonce+'"], "id": 1, "method": "mining.submit"}\n', 'utf-8')
                    logg('[*] Payload: {}'.format(payload))

                    try:
                        sock  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect(('solo.ckpool.org', 3333))
                        sock.sendall(payload)
                        ret = sock.recv(1024)
                        sock.close()
                        logg('[*] Pool response: {}'.format(ret))
                    except:
                        pass
                
                # increment nonce by 1, in case we don't want random 
                nNonce +=1

                if cycleBack == maxCycle :
                    break

                cycleBack +=1



bitcoin_miner()
