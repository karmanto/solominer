# Distributed under the MIT/X11 software license, see the accompanying
# file license http://www.opensource.org/licenses/mit-license.php.



import socket
import time
import json
import time
from datetime import datetime
import os
import threading



def load_env(file_path):
    with open(file_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

load_env('.env')



address = os.getenv("ADDRESS", "1NStyxyH5hFc3Bj7d4D2VKktx2bqdVuEBF")
dir = os.getenv("DIRECTORY", "")
threadExists = False
sendResultFinish = False
sendResultPending = False



def logg(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(dir + 'miner.log', 'a') as file:
        file.write(f'{timestamp} {msg}\n')



def rev8(item):
    item = item[::-1]
    item = ''.join([item[i:i + 8][::-1] for i in range(0, len(item), 8)])
    return item



def handle_result(sock):
    global threadExists
    global sendResultFinish
    global sendResultPending

    while threadExists:
        try:
            f = open(dir + "result.txt", "r")
            result = f.read()
            f.close()
            if result and len(result.splitlines()) >= 5:
                f = open(dir + "result.txt", "w")
                f.write("")
                f.close()
                f = open(dir + "stat.txt", "w")
                f.write("999")
                f.close()

                lines = result.splitlines()
                blockheader = lines[0]
                job_id = lines[1]
                extranonce2 = lines[2]
                ntime = lines[3]
                nonce = lines[4]

                logg('[*] Block solved on jobId {}.'.format(job_id))
                logg('[*] Blockheader: {}'.format(blockheader))

                payload = bytes('{"params": ["' + address + '", "' + job_id + '", "' + extranonce2 \
                                + '", "' + ntime + '", "' + nonce + '"], "id": 1, "method": "mining.submit"}\n', 'utf-8')
                logg('[*] Payload: {}'.format(payload))

                sendResultPending = True

                try:
                    sock.sendall(payload)
                    ret = sock.recv(1024)
                    logg('[*] Pool response: {}'.format(ret))
                except:
                    pass

                sendResultFinish = True
                break

        except:
            pass



def block_listener():
    global threadExists
    global sendResultFinish
    global sendResultPending

    while True:
        sendResultFinish = False
        threadExists = False
        sendResultPending = False
        f = open(dir + "stat.txt", "w")
        f.write("999")
        f.close()
        f = open(dir + "result.txt", "w")
        f.write("")
        f.close()
        f = open(dir + "data.txt", "w")
        f.write("")
        f.close()

        time.sleep(5)

        last_change_time = time.time() 
        breakStat = False
        breakStat2 = False
        extranonce2_size = 8
        extranonce1 = ""

        try: 
            sock  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('solo.ckpool.org', 3333))
            sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
            lines = sock.recv(1024).decode().split('\n')
            response = json.loads(lines[0])
            sub_details,extranonce1,extranonce2_size = response['result']
            intExtraNonce2_size = int(extranonce2_size)
            if intExtraNonce2_size > 20:
                extranonce2_size = 8
            else:
                sock.sendall(b'{"params": ["'+address.encode()+b'", "password"], "id": 2, "method": "mining.authorize"}\n')
                response = b''
                while response.count(b'\n') < 4 and not(b'mining.notify' in response):
                    response += sock.recv(1024)
                    if time.time() - last_change_time > 30:
                        breakStat = True
                        sock.close()
                        break
        except:
            breakStat = True
            sock.close()

        
        if not breakStat:
            last_change_time = time.time() 
            try:
                responses = [json.loads(res) for res in response.decode().split('\n') if len(res.strip())>0 and 'mining.notify' in res]
                job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = responses[0]['params']
                prevHashLE = rev8(prevhash)
                versionLE = int(version, 16)
                ntimeLE = int(ntime, 16)
                nbitsLE = int(nbits, 16)
                f = open(dir + "data.txt", "w")
                f.write(job_id + "\n")
                f.write(prevhash + "\n")
                f.write(coinb1 + "\n")
                f.write(coinb2 + "\n")
                f.write(",".join(merkle_branch) + "\n")
                f.write(version + "\n")
                f.write(nbits + "\n")
                f.write(ntime + "\n")
                f.write(str(clean_jobs) + "\n")
                f.write(prevHashLE + "\n")
                f.write(str(versionLE) + "\n")
                f.write(str(ntimeLE) + "\n")
                f.write(str(nbitsLE) + "\n")
                f.write(str(extranonce2_size) + "\n")
                f.write(extranonce1)
                f.close()
                f = open(dir + "stat.txt", "w")
                f.write("0")
                f.close()
            except:
                sock.close()
                continue

            while True:
                if not threadExists:
                    threadExists = True
                    result_thread = threading.Thread(target=handle_result, args=(sock,))
                    result_thread.start()

                response = b''
                while response.count(b'\n') < 4 and not(b'mining.notify' in response):
                    if not sendResultPending:
                        response += sock.recv(1024)

                    if time.time() - last_change_time > 1200 or sendResultFinish:
                        breakStat2 = True
                        break

                
                if not breakStat2 :
                    last_change_time = time.time() 
                    try:
                        responses = [json.loads(res) for res in response.decode().split('\n') if len(res.strip())>0 and 'mining.notify' in res]    
                        if responses[0]['params'][1] != prevhash:
                            job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = responses[0]['params']
                            prevHashLE = rev8(prevhash)
                            versionLE = int(version, 16)
                            ntimeLE = int(ntime, 16)
                            nbitsLE = int(nbits, 16)
                            f = open(dir + "data.txt", "w")
                            f.write(job_id + "\n")
                            f.write(prevhash + "\n")
                            f.write(coinb1 + "\n")
                            f.write(coinb2 + "\n")
                            f.write(",".join(merkle_branch) + "\n")
                            f.write(version + "\n")
                            f.write(nbits + "\n")
                            f.write(ntime + "\n")
                            f.write(str(clean_jobs) + "\n")
                            f.write(prevHashLE + "\n")
                            f.write(str(versionLE) + "\n")
                            f.write(str(ntimeLE) + "\n")
                            f.write(str(nbitsLE))
                            f.write(str(extranonce2_size) + "\n")
                            f.write(extranonce1)
                            f.close()
                            f = open(dir + "stat.txt", "w")
                            f.write("0")
                            f.close()
                    except:
                        sock.close()
                        break 
                
                else:
                    sock.close()
                    break

block_listener()
