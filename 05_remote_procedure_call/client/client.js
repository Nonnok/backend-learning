// モジュールインポート
const net = require('net');
const readline= require('node:readline');

const SOCKET_PATH = '/tmp/socket_file';
let requestId = 0;

// CLIの対話実現セット
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

// UNIXソケットに接続する
const client = net.createConnection(SOCKET_PATH, () => {
  console.log('Connected to server');
  askMethod();
});

function parseParam(input) {
  return input.split(',').map(p => {
    p = p.trim();
    if(!isNaN(p)) return Number(p);
    if(p === 'true') return true;
    if(p === 'false') return false;
    return p;
  });
}

function askMethod() {
  requestId++;
  rl.question('Method name: ', (method) => {
    rl.question('Params ( , separated ): ', (paramInput) => {
      const params = parseParam(paramInput);

      const request = {
        method: method,
        params: params,
        id: requestId
      };

      client.write(JSON.stringify(request) + '\n');
    });
  });
}

let buffer = '';

client.on('data', (data) => {
  buffer += data.toString();

  while(buffer.includes('\n')) {
    const [line, ...rest] = buffer.split('\n');
    buffer = rest.join('\n');

    const response = JSON.parse(line);
    console.log('Response: ', response);
  }
  askMethod();
});

client.on('error', (error) => {
  console.error('Error：', error.message);
});