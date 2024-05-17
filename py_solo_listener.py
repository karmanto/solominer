#!/usr/bin/env python  
# Copyright (c) 2021-2022 iceland
# Copyright (c) 2022-2023 Papa Crouz
# Distributed under the MIT/X11 software license, see the accompanying
# file license http://www.opensource.org/licenses/mit-license.php.



import socket
import time
import json
import time



# Replace this with your Bitcoin Address
address = '1NStyxyH5hFc3Bj7d4D2VKktx2bqdVuEBF'



def rev8(item):
    item = item[::-1]
    item = ''.join([item[i:i + 8][::-1] for i in range(0, len(item), 8)])
    return item



def block_listener():
    f = open("stat.txt", "w")
    f.write("999")
    f.close()

    while True:
        last_change_time = time.time() 
        breakStat = False
        breakStat2 = False
        extranonce2_size = 0
        extranonce1 = ""


        try:
            # init a connection to ckpool 
            sock  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('solo.ckpool.org', 3333))
            # send a handle subscribe message 
            sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
            lines = sock.recv(1024).decode().split('\n')
            response = json.loads(lines[0])
            sub_details,extranonce1,extranonce2_size = response['result']

            if not extranonce2_size or int(extranonce2_size) > 20:
                breakStat = True
                sock.close()
            else:
                # send and handle authorize message  
                sock.sendall(b'{"params": ["'+address.encode()+b'", "password"], "id": 2, "method": "mining.authorize"}\n')
                response = b''
                while response.count(b'\n') < 4 and not(b'mining.notify' in response):
                    response += sock.recv(1024)
                    if time.time() - last_change_time > 30:
                        breakStat = True
                        sock.close()
                        break
        except:
            time.sleep(10)
            breakStat = True
            sock.close()

        
        if not breakStat:
            last_change_time = time.time() 

            responses = [json.loads(res) for res in response.decode().split('\n') if len(res.strip())>0 and 'mining.notify' in res]
            job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = responses[0]['params']

            prevHashLE = rev8(prevhash)
            versionLE = int(version, 16)
            ntimeLE = int(ntime, 16)
            nbitsLE = int(nbits, 16)

            f = open("data.txt", "w")
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
            f.write(extranonce1 + "\n")
            f.write(address)
            f.close()

            f = open("stat.txt", "w")
            f.write("0")
            f.close()

            while True:
                # check for new block 
                response = b''
                while response.count(b'\n') < 4 and not(b'mining.notify' in response):
                    response += sock.recv(1024)
                    if time.time() - last_change_time > 1200:
                        breakStat = True
                        breakStat2 = True
                        sock.close()
                        break
                
                if not breakStat2 :
                    last_change_time = time.time() 
                    responses = [json.loads(res) for res in response.decode().split('\n') if len(res.strip())>0 and 'mining.notify' in res]     

                    if responses[0]['params'][1] != prevhash:
                        # new block detected on network 
                        # update context job data 
                        job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = responses[0]['params']

                        prevHashLE = rev8(prevhash)
                        versionLE = int(version, 16)
                        ntimeLE = int(ntime, 16)
                        nbitsLE = int(nbits, 16)

                        f = open("data.txt", "w")
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
                        f.write(extranonce1 + "\n")
                        f.write(address)
                        f.close()

                        f = open("stat.txt", "w")
                        f.write("0")
                        f.close()
                
                else:
                    break

block_listener()
