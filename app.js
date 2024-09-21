const net = require('net');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');

dotenv.config({ path: path.resolve(__dirname, '.env') });

let isConnected = false;

const jsonArray = (jsonString) => {
    const jsonStringArray = jsonString.toString().split("\n");
    const jsonData = jsonStringArray.map(str => {
    try {
        return JSON.parse(str);
    } catch (error) {
        return null; 
    }
    }).filter(item => item !== null);

    return jsonData;
}

const rev8 = (item) => {
    item = item.split('').reverse().join('');
    item = item.match(/.{1,8}/g).map(part => part.split('').reverse().join('')).join('');
    
    return item;
}

function main() {
    const address = process.env.ADDRESS || '1NStyxyH5hFc3Bj7d4D2VKktx2bqdVuEBF';
    let hasExtraNonce = false;
    let extranonce1 = '';
    let extranonce2_size = 8;

    if (isConnected) {
        console.log("Connection is already active, skipping new attempt.");
        return;
    }

    console.log("Starting socket connection...");
    isConnected = true;
    hasExtraNonce = false;

    const client = new net.Socket();
    
    client.connect(3333, 'solo.ckpool.org', () => {
        console.log("Connected to the server.");
        client.write('{"id": 1, "method": "mining.subscribe", "params": []}\n');
    });

    client.on('data', (data) => {
        if (!hasExtraNonce) {
            const jsonData = jsonArray(data);
            const foundExtranonceData = jsonData.find(obj => obj.id === 1);
            if (foundExtranonceData) {
                extranonce1 = foundExtranonceData.result[1];
                extranonce2_size = foundExtranonceData.result[2];
                client.write(`{"params": ["${address}", "password"], "id": 2, "method": "mining.authorize"}\n`);
                hasExtraNonce = true;
            } 
        } else {
            const jsonData = jsonArray(data);
            const foundExtranonceData = jsonData.find(obj => obj.id === null);
            if (foundExtranonceData) {
                const [job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs] = foundExtranonceData.params;
                const prevHashLE = rev8(prevhash);
                const versionLE = parseInt(version, 16);
                const ntimeLE = parseInt(ntime, 16);
                const nbitsLE = parseInt(nbits, 16);
                const now = new Date();
                let dataWrite = job_id + "\n";
                dataWrite += prevhash + "\n";
                dataWrite += coinb1 + "\n";
                dataWrite += coinb2 + "\n";
                dataWrite += merkle_branch.join(",") + "\n";
                dataWrite += version + "\n";
                dataWrite += nbits + "\n";
                dataWrite += ntime + "\n";
                dataWrite += clean_jobs.toString() + "\n";
                dataWrite += prevHashLE + "\n";
                dataWrite += versionLE.toString() + "\n";
                dataWrite += ntimeLE.toString() + "\n";
                dataWrite += nbitsLE.toString() + "\n";
                dataWrite += extranonce2_size.toString() + "\n";
                dataWrite += extranonce1 + "\n";
                dataWrite += now.getFullYear() + '-' +
                            String(now.getMonth() + 1).padStart(2, '0') + '-' +
                            String(now.getDate()).padStart(2, '0') + ' ' +
                            String(now.getHours()).padStart(2, '0') + ':' +
                            String(now.getMinutes()).padStart(2, '0') + ':' +
                            String(now.getSeconds()).padStart(2, '0');
                fs.writeFile('data.txt', dataWrite, () => {});
            }
        }
    });

    client.on('error', (err) => {
        console.error("Socket error: ", err.message);
        client.destroy();
    });

    client.on('close', (hadError) => {
        console.log(hadError ? "Connection closed due to error." : "Connection closed by server.");
        isConnected = false; 
        restartConnection();
    });
}

function restartConnection() {
    console.log("Restarting connection in 5 seconds...");
    setTimeout(main, 5000);
}

main();
