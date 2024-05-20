# Distributed under the MIT/X11 software license, see the accompanying
# file license http://www.opensource.org/licenses/mit-license.php.



from signal import signal, SIGINT
import context as ctx 
import threading
import binascii
import hashlib
import logging
import random
import socket
import time
import json
import sys
import time
from datetime import datetime
import struct
import os



def load_env(file_path):
    script_dir = os.path.dirname(os.path.abspath(__file__)) 
    env_path = os.path.join(script_dir, file_path) 
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

load_env('.env')



maxCycle = int(os.getenv("CYCLE", "100000"))
random_nonce = os.getenv("RANDOM_NONCE") == '1'
address = os.getenv("ADDRESS", "1NStyxyH5hFc3Bj7d4D2VKktx2bqdVuEBF")
dir = os.getenv("DIRECTORY", "")



def handler(signal_received, frame):
    # Handle any cleanup here
    ctx.fShutdown = True
    # print('Terminating miner, please wait..')



def logg(msg):
    # basic logging 
    filename = dir + '/miner.log'
    # if len(sys.argv) > 1:
    #     filename = 'miner' + sys.argv[1] + '.log'
    logging.basicConfig(level=logging.INFO, filename=filename, format='%(asctime)s %(message)s') # include timestamp
    logging.info(msg)



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
    # handle shutdown 
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
            except Exception as e:
                logg("ThreadHandler()")
                logg(e)
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
    exitStat = False

    while ctx.updatedPrevHash is None and not exitStat:
        pass

    while not exitStat:
        target = (ctx.nbits[2:]+'00'*(int(ctx.nbits[:2],16) - 3)).zfill(64)
        ctx.extranonce2 = hex(random.randint(0,2**64-1))[2:].zfill(2*ctx.extranonce2_size) 

        coinbase = ctx.coinb1 + ctx.extranonce1 + ctx.extranonce2 + ctx.coinb2
        coinbase_hash_bin = hashlib.sha256(hashlib.sha256(binascii.unhexlify(coinbase)).digest()).digest()

        merkle_root = coinbase_hash_bin
        for h in ctx.merkle_branch:
            merkle_root = hashlib.sha256(hashlib.sha256(merkle_root + binascii.unhexlify(h)).digest()).digest()

        merkle_root = binascii.hexlify(merkle_root).decode()

        #little endian
        merkle_root = ''.join([merkle_root[i]+merkle_root[i+1] for i in range(0,len(merkle_root),2)][::-1])
        # partialheader = ctx.versionLE + ctx.prevHashLE + merkle_root + ctx.ntimeLE + ctx.nbitsLE

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
                exitStat = True
                break

            if ctx.prevhash != ctx.updatedPrevHash:
                ctx.updatedPrevHash = ctx.prevhash
                break 

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
                num_zeros = len(hash) - len(hash.lstrip('0'))
                logg('[*] Zero length : {} New hash: {} target: {} extranonce {} nonce {}'.format(num_zeros, hash, target, ctx.extranonce2, nonce))
                print("\r%s Zero length: %s hash: %s extranonce %s "%(now, num_zeros, hash, ctx.extranonce2))
            elif hash.startswith('0000') and random_nonce:
                now = datetime.now()
                num_zeros = len(hash) - len(hash.lstrip('0'))
                sys.stdout.write("\r%s Zero length: %s hash: %s extranonce %s "%(now, num_zeros, hash, ctx.extranonce2))
                sys.stdout.flush()

            if not random_nonce:
                # hash meter, only works with regular nonce.
                last_updated = calculate_hashrate(nNonce, last_updated)

            if hash < target :
                logg('[*] Block solved.'.format())
                logg('[*] Block hash: {}'.format(hash))
                logg('[*] Blockheader: {}'.format(blockheader))            
                payload = bytes('{"params": ["'+address+'", "'+ctx.job_id+'", "'+ctx.extranonce2 \
                    +'", "'+ctx.ntime+'", "'+nonce+'"], "id": 1, "method": "mining.submit"}\n', 'utf-8')
                logg('[*] Payload: {}'.format(payload))
                ctx.sock.sendall(payload)
                ret = ctx.sock.recv(1024)
                logg('[*] Pool response: {}'.format(ret))
                return True
            
            # increment nonce by 1, in case we don't want random 
            nNonce +=1

            if cycleBack == maxCycle :
                break

            cycleBack +=1



def block_listener(t):
    firstLoad = True
    exitStat = False

    while not exitStat:
        last_change_time = time.time() 
        breakStat = False
        breakStat2 = False

        try:
            # init a connection to ckpool 
            sock  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('solo.ckpool.org', 3333))
            # send a handle subscribe message 
            sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
            lines = sock.recv(1024).decode().split('\n')
            response = json.loads(lines[0])
            ctx.sub_details,ctx.extranonce1,ctx.extranonce2_size = response['result']
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
            ctx.job_id, ctx.prevhash, ctx.coinb1, ctx.coinb2, ctx.merkle_branch, ctx.version, ctx.nbits, ctx.ntime, ctx.clean_jobs = responses[0]['params']

            ctx.prevHashLE = rev8(ctx.prevhash)
            ctx.versionLE = int(ctx.version, 16)
            ctx.ntimeLE = int(ctx.ntime, 16)
            ctx.nbitsLE = int(ctx.nbits, 16)

            # do this one time, will be overwriten by mining loop when new block is detected
            if firstLoad:
                firstLoad = False
                ctx.updatedPrevHash = ctx.prevhash

            # set sock 
            ctx.sock = sock 

            while True:
                t.check_self_shutdown()
                if t.exit:
                    exitStat = True
                    break

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

                    if responses[0]['params'][1] != ctx.prevhash:
                        # new block detected on network 
                        # update context job data 
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
