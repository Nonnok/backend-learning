import socket
import sys

sock = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )
server_address = '/tmp/socket_file'

try:
    sock.connect( server_address )
except socket.error as err:
    print(err)
    sys.exit(1)

try:
    while True:
        message = input( 'Type your message (exit to quit): ' )
        sock.sendall( message.encode('utf-8') )
        if message == 'exit':
            break

        data = sock.recv(1024).decode('utf-8')
        if data:
            print( 'The message was sent to: ' + data )
finally:
    print( "Closing current connection" )
    sock.close()