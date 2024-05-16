import threading
import binascii
import hashlib
import socket
import random
import json
import time
import struct

address = '1PAEqpfAC5ZeZwg4UBDAsNiVizbBNhGuHV'
server_address = ('public-pool.io', 21496)
response = b''
target = ''
job_id = ''
prevhash = ''
coinb1 = ''
coinb2 = ''
merkle_branch = ''
version = ''
nbits = ''
ntime = ''
clean_jobs = ''
merkle_root = ''
sub_details = ''
extranonce1 = ''
extranonce2 = ''
extranonce2_size = 0
difficulty = 0.001
difficulty_ok = 0
target_max =   "0000003e8b300000000000000000000000000000000000000000000000000000"
target_miner = "00003e8b30000000000000000000000000000000000000000000000000000000"
id_max = 1
partial_header = ""


def target_to_difficulty(target):
    # hedef (target) değerini zorluk (difficulty) değerine dönüştürme
    #print("Function target:", target)
    max_target = 0xFFFF * 2 ** (8 * (0x1D - 3))
    return max_target / int(target, 16)

def difficulty_to_target(difficulty):
    # hedef (target) değerini zorluk (difficulty) değerine dönüştürme
    max_target = 0xFFFF * 2 ** (8 * (0x1D - 3))
    return max_target / difficulty

def rev(item):
    item = item[::-1]
    item = ''.join([item[i:i + 2][::-1] for i in range(0, len(item), 2)])
    return item
def rev8(item):
    item = item[::-1]
    item = ''.join([item[i:i + 8][::-1] for i in range(0, len(item), 8)])
    return item

def worker(sock):
    global id_max, partial_header, job_id, extranonce2, ntime, address, target
    hash_count = 0
    star_time = time.time()
    nonce = hex(random.randint(0, 2 ** 32 - 1))[2:].zfill(8)  # nnonve   #hex(int(nonce,16)+1)[2:]
    nonce_int = int(nonce, 16)
    while True:

        nonce_int = nonce_int + 1

        header = partial_header + struct.pack("<L", nonce_int)

        hash = hashlib.sha256(hashlib.sha256(header).digest()).digest()
        hash = binascii.hexlify(hash[::-1])

        hash_count += 1
        if int(hash_count % 3000000) == 0:
           m_time = time.time() - star_time
           hash_rate = hash_count / (m_time + 1) / 1000
           # print("Hash_count(k):", hash_count/1000, "Last nonce:", int(nonce,16))
           print("Last nonce:", str(nonce), "Hash rate:", int(hash_rate), "k per second")
        # if target_to_difficulty(hash) > difficulty:
        #     id_max = id_max + 1
        #     print("=============Submit============", nonce, hash[::-1])
        #     payload = bytes('{"params": ["' + address + '", "' + job_id + '", "' + extranonce2 \
        #                     + '", "' + ntime + '", "' + hex(nonce_int)[2:].zfill(8) + '"], "id": ' + str(id_max) + ', "method": "mining.submit"}\n', 'utf-8')
        #     sock.sendall(payload)
        #     print("Send:", payload)

def receive_all(socket):
    # Alınacak veriyi tutmak için boş bir tampon oluştur
    all_data = b""
    while True:
        # Veri al
        data = socket.recv(1024)
        if len(data) < 1024:
            all_data += data
            break
        # Alınan veriyi tampona ekle
        all_data += data
    return all_data

# İstemciye gelen cevapları dinleyen iş parçacığı
def receive_messages(sock):
    global response, client, target, merkle_root, difficulty, id_max, target_miner, difficulty_ok, partial_header
    global job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs, sub_details, extranonce1, extranonce2, extranonce2_size

    while True:
        response = receive_all(client)
        responses = response.decode().split('\n')
        if(len(responses[0]) > 0):
            print("responses", responses)

            for line in responses:
                if("mining.set_difficulty" in line):
                   print("Line:", line)
                   response = json.loads(line)
                   difficulty = float(response['params'][0])
                   target_miner = format(int(difficulty_to_target(difficulty)))
                   print("difficulty:", difficulty, "Target: ", difficulty_to_target(difficulty), "target_hex_64bit", format(int(difficulty_to_target(difficulty)), '064x'))
                   if(difficulty_ok == 0):
                       message = b'{"id":  ' + str(
                        id_max).encode() + b', "method": "mining.suggest_difficulty", "params": [0.0001]}\n'
                       # {"id": 3, "method": "mining.suggest_difficulty", "params": [0.0001]}
                       id_max = id_max + 1
                       client.sendall(message)
                       print("Send:", message)
                       difficulty_ok = 1
                elif("mining.notify" in line and "}" in line ):
                    print("Line:", line)
                    print("====================================New job==================================")
                    lines = json.loads(line)
                    job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = lines['params']
                    target = (nbits[2:] + '00' * (int(nbits[:2], 16) - 3)).zfill(64)
                    print("Target:", target)
                    extranonce2 = hex(random.randint(0, 2 ** 32 - 1))[2:].zfill(2 * extranonce2_size)  # create random
                    coinbase = coinb1 + extranonce1 + extranonce2 + coinb2
                    print("coinbase:", coinbase)
                    coinbase_hash_bin = hashlib.sha256(hashlib.sha256(binascii.unhexlify(coinbase)).digest()).digest()

                    merkle_root = coinbase_hash_bin
                    for h in merkle_branch:
                        merkle_root = hashlib.sha256(
                            hashlib.sha256(merkle_root + binascii.unhexlify(h)).digest()).digest()

                    merkle_root = binascii.hexlify(merkle_root).decode()

                    # little endian
                    merkle_root = ''.join(
                        [merkle_root[i] + merkle_root[i + 1] for i in range(0, len(merkle_root), 2)][::-1])

                    prevhash = rev8(prevhash)
                    version_int = int(version, 16)
                    time = int(ntime, 16)
                    bits = int(nbits, 16)

                    partial_header = struct.pack("<L", version_int) \
                                     + bytes.fromhex(prevhash)[::-1] \
                                     + bytes.fromhex(merkle_root)[::-1] \
                                     + struct.pack("<LL", time, bits)

                    print("Version_l:    ", str(struct.pack("<L", version_int).hex()).zfill(64))
                    print("prev_block_l: ", str(bytes.fromhex(prevhash)[::-1].hex()).zfill(64))
                    print("markle_root_l:", str(bytes.fromhex(merkle_root[::-1]).hex()).zfill(64))
                    print("Time_l:", str(struct.pack("<L", time).hex()).zfill(64))
                    print("bits_l:", str(struct.pack("<L", bits).hex()).zfill(64))

                    worker1 = threading.Thread(target=worker, args=(client,))
                    worker1.start()


# Sunucuya bağlan
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(server_address)

message = b'{"id": 1, "method": "mining.subscribe", "params": ["NerdMinerV2"]}\n'
client.sendall(message)
print("Send:", message)

lines = client.recv(1024).decode().split('\n')
response = json.loads(lines[0])
sub_details, extranonce1, extranonce2_size = response['result']
print("Response:", response)
print("sub_details, extranonce1, extranonce2_size:", sub_details, extranonce1, extranonce2_size)

message = b'{"params": ["' + address.encode() + b'", "password"], "id": 2, "method": "mining.authorize"}\n'
client.sendall(message)
print("Send:", message)

#response = receive_all(client)
#print("Response:", response)
#lines = response.decode().split('\n')
#response = json.loads(lines[0])


#message = b'{"id": 3, "method": "mining.suggest_difficulty"", "params": ["0.0001"]}\n\n'
#client.sendall(message)
#print("Send:", message)

# İstemci tarafında cevapları dinlemek için yeni bir iş parçacığı başlat
receive_thread = threading.Thread(target=receive_messages, args=(client,))
receive_thread.start()