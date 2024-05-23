# Distributed under the MIT/X11 software license, see the accompanying
# file license http://www.opensource.org/licenses/mit-license.php.



from signal import signal, SIGINT
import context as ctx 
import threading
import binascii
import hashlib
import random
import socket
import time
import json
import sys
import time
from datetime import datetime
import struct
import os



maxCycle = 100000
random_nonce = True
address = "1NStyxyH5hFc3Bj7d4D2VKktx2bqdVuEBF"



def handler(signal_received, frame):
    # Handle any cleanup here
    ctx.fShutdown = True
    # print('Terminating miner, please wait..')



def calculate_hashrate(nonce, last_updated):
  if nonce % 1000000 == 999999:
    now             = time.time()
    hashrate        = round(1000000/(now - last_updated))
    sys.stdout.write("\r%s hash/s"%(str(hashrate)))
    sys.stdout.flush()
    return now
  else:
    return last_updated
  

  
def rev(item):
    item = item[::-1]
    item = ''.join([item[i:i + 2][::-1] for i in range(0, len(item), 2)])
    return item



def rev8(item):
    item = item[::-1]
    item = ''.join([item[i:i + 8][::-1] for i in range(0, len(item), 8)])
    return item



def check_for_shutdown(t):
    n = t.n
    if ctx.fShutdown:
        if n != -1:
            ctx.listfThreadRunning[n] = False
            t.exit = True



class ExitedThread(threading.Thread):
    def __init__(self, arg, n):
        super(ExitedThread, self).__init__()
        self.exit = False
        self.arg = arg
        self.n = n

    def run(self):
        self.thread_handler(self.arg, self.n)
        pass

    def thread_handler(self, arg, n):
        while True:
            check_for_shutdown(self)
            if self.exit:
                break
            ctx.listfThreadRunning[n] = True
            try:
                self.thread_handler2(arg)
            except:
                pass
            ctx.listfThreadRunning[n] = False

            time.sleep(5)
            pass

    def thread_handler2(self, arg):
        raise NotImplementedError("must impl this func")

    def check_self_shutdown(self):
        check_for_shutdown(self)

    def try_exit(self):
        self.exit = True
        ctx.listfThreadRunning[self.n] = False
        pass



def bitcoin_miner(t):
    global address
    global maxCycle
    global random_nonce
    while ctx.updatedPrevHash is None:
        pass

    while True:
        target = (ctx.nbits[2:]+'00'*(int(ctx.nbits[:2],16) - 3)).zfill(64)
        ctx.extranonce2 = hex(random.randint(0,2**64-1))[2:].zfill(2*ctx.extranonce2_size) 
        coinbase = ctx.coinb1 + ctx.extranonce1 + ctx.extranonce2 + ctx.coinb2
        coinbase_hash_bin = hashlib.sha256(hashlib.sha256(binascii.unhexlify(coinbase)).digest()).digest()
        merkle_root = coinbase_hash_bin
        for h in ctx.merkle_branch:
            merkle_root = hashlib.sha256(hashlib.sha256(merkle_root + binascii.unhexlify(h)).digest()).digest()

        merkle_root = binascii.hexlify(merkle_root).decode()
        merkle_root = ''.join([merkle_root[i]+merkle_root[i+1] for i in range(0,len(merkle_root),2)][::-1])
        partialheader = struct.pack("<L", ctx.versionLE) \
                            + bytes.fromhex(ctx.prevHashLE)[::-1] \
                            + bytes.fromhex(merkle_root) \
                            + struct.pack("<L", ctx.ntimeLE) \
                            + struct.pack("<L", ctx.nbitsLE)

        nNonce = 0
        cycleBack = 0

        last_updated = int(time.time())

        while True:
            t.check_self_shutdown()
            if t.exit:
                break

            if ctx.prevhash != ctx.updatedPrevHash:
                ctx.updatedPrevHash = ctx.prevhash
                break 

            if random_nonce:
                nonce = hex(random.randint(0,2**32-1))[2:].zfill(8)
            else:
                nonce = hex(nNonce)[2:].zfill(8)

            nonceLE = struct.pack("<L", int(nonce, 16))

            blockheader = partialheader + nonceLE
            hash = hashlib.sha256(hashlib.sha256(blockheader).digest()).digest()
            hash = binascii.hexlify(hash[::-1]).decode()
            
            if hash.startswith('00000000'): 
                num_zeros = len(hash) - len(hash.lstrip('0'))
                print("\r%s Zero length: %s hash: %s extranonce %s "%(now, num_zeros, hash, ctx.extranonce2))
            elif hash.startswith('0000') and random_nonce:
                now = datetime.now()
                num_zeros = len(hash) - len(hash.lstrip('0'))
                sys.stdout.write("\r%s Zero length: %s hash: %s extranonce %s "%(now, num_zeros, hash, ctx.extranonce2))
                sys.stdout.flush()

            if not random_nonce:
                last_updated = calculate_hashrate(nNonce, last_updated)

            if hash < target :       
                payload = bytes('{"params": ["'+address+'", "'+ctx.job_id+'", "'+ctx.extranonce2 \
                    +'", "'+ctx.ntime+'", "'+nonce+'"], "id": 1, "method": "mining.submit"}\n', 'utf-8')
                print("\rpayload: %s hash: %s blockheader %s "%(payload, hash, blockheader))
                ctx.sock.sendall(payload)
                ret = ctx.sock.recv(1024)
                print("\response: %s "%(ret))
                return True
            
            nNonce +=1
            if cycleBack == maxCycle :
                break

            cycleBack +=1



def block_listener(t):
    firstLoad = True
    global address

    while True:
        last_change_time = time.time() 
        breakStat = False
        breakStat2 = False

        try:
            sock  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('solo.ckpool.org', 3333))
            sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
            lines = sock.recv(1024).decode().split('\n')
            response = json.loads(lines[0])
            ctx.sub_details,ctx.extranonce1,ctx.extranonce2_size = response['result']
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
            ctx.job_id, ctx.prevhash, ctx.coinb1, ctx.coinb2, ctx.merkle_branch, ctx.version, ctx.nbits, ctx.ntime, ctx.clean_jobs = responses[0]['params']
            ctx.prevHashLE = rev8(ctx.prevhash)
            ctx.versionLE = int(ctx.version, 16)
            ctx.ntimeLE = int(ctx.ntime, 16)
            ctx.nbitsLE = int(ctx.nbits, 16)
            if firstLoad:
                firstLoad = False
                ctx.updatedPrevHash = ctx.prevhash

            ctx.sock = sock 
            while True:
                t.check_self_shutdown()
                if t.exit:
                    break

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

                    if responses[0]['params'][1] != ctx.prevhash:
                        ctx.job_id, ctx.prevhash, ctx.coinb1, ctx.coinb2, ctx.merkle_branch, ctx.version, ctx.nbits, ctx.ntime, ctx.clean_jobs = responses[0]['params']
                
                else:
                    break



class CoinMinerThread(ExitedThread):
    def __init__(self, arg=None):
        super(CoinMinerThread, self).__init__(arg, n=0)

    def thread_handler2(self, arg):
        self.thread_bitcoin_miner(arg)

    def thread_bitcoin_miner(self, arg):
        ctx.listfThreadRunning[self.n] = True
        check_for_shutdown(self)
        try:
            ret = bitcoin_miner(self)
        except Exception as e:
            pass
        ctx.listfThreadRunning[self.n] = False

    pass  



class NewSubscribeThread(ExitedThread):
    def __init__(self, arg=None):
        super(NewSubscribeThread, self).__init__(arg, n=1)

    def thread_handler2(self, arg):
        self.thread_new_block(arg)

    def thread_new_block(self, arg):
        ctx.listfThreadRunning[self.n] = True
        check_for_shutdown(self)
        try:
            ret = block_listener(self)
        except Exception as e:
            pass
        ctx.listfThreadRunning[self.n] = False

    pass  



def StartMining():
    subscribe_t = NewSubscribeThread(None)
    subscribe_t.start()

    miner_t = CoinMinerThread(None)
    miner_t.start()



if __name__ == '__main__':
    signal(SIGINT, handler)
    StartMining()
