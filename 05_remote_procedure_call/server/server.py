import socket
import os
import json
import functions

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server_address = '/tmp/socket_file'

try:
    os.unlink(server_address)
except FileNotFoundError:
    pass

print( f'Starting up on {server_address}' )

sock.bind(server_address)
sock.listen(1)

# RPC関数のハッシュマップ
FUNCTION_TABLE = {
    'floor': functions.floor,
    'nroot': functions.nroot,
    'reverse': functions.reverse,
    'validAnagram': functions.validAnagram,
    'sort': functions.sort,
}


while True:
    connection, client_address = sock.accept()
    print('Client connected.')

    buffer = ""
    while True:
        data = connection.recv(4096)
        if not data:
            break

        buffer += data.decode('utf-8')

        while '\n' in buffer:
            line, buffer = buffer.split('\n', 1)

            try:
                request = json.loads(line)
                method_name = request['method']
                params = request['params']
                request_id = request['id']

                function = FUNCTION_TABLE.get(method_name)

                if not function:
                    response = {
                        'error': f'Method [{method_name}] is not found.',
                        'id': request_id
                    }
                else:
                    try:
                        result = function(*params)
                        response = {
                            'result': result,
                            'result_type': type(result).__name__,
                            'id': request_id
                        }
                    except Exception as error:
                        response = {
                            'error': str(error),
                            'id': request_id
                        }
            except Exception as error:
                response = {
                    'error': str(error),
                    'id': request_id
                }
            connection.sendall((json.dumps(response) + '\n').encode())
    connection.close()
    print("Client disconnected")