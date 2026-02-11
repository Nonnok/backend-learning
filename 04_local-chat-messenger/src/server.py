import socket
import os
from faker import Faker

sock = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )

server_address = '/tmp/socket_file'

# ダミーデータの作成
fake = Faker()

try:
    os.unlink(server_address)
except FileNotFoundError:
    pass

print( 'Starting up on {}'.format(server_address) )

sock.bind(server_address)
sock.listen(1)

while True:
    connection, client_address = sock.accept()
    try:
        print( 'connetcion from', client_address )

        while True:
            data = connection.recv( 1024 )

            if not data:
                print( 'No data received. Closing connection.' )
                break

            data_str = data.decode('utf-8')
            if data_str:
                print( 'Received: ', data_str )
            if data_str == 'exit':
                print( 'The exit command was accepted.' )
                break

            response = fake.name()
            connection.sendall( response.encode('utf-8') )
    finally:
        print( 'closing socket' )
        connection.close()