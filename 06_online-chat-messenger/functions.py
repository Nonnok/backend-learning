# functions.py

# TCRPヘッダーの作成
def create_tcrp_header(room_name_length, operation, state, data_length):
    return (
        room_name_length.to_bytes(1, "big")
        + operation.to_bytes(1, "big")
        + state.to_bytes(1, "big")
        + data_length.to_bytes(29, "big")
    )

# TCP全文受信
def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError
        data += chunk
    return data

# TCRP全文送信
def send_tcrp_packet(connection, header, body):
    connection.sendall(header)
    connection.sendall(body)

# TCRPのヘッダーを読む
def parse_tcp_header(header):
    room_name_len = header[0]
    operation = header[1]
    state = header[2]
    payload_len = int.from_bytes(header[3:32], "big")

    return room_name_len, operation, state, payload_len

# TCRPのボディーを読む
def parse_tcp_body(body, room_name_len):
    room = body[:room_name_len].decode("utf-8")
    payload = body[room_name_len:].decode("utf-8")

    return room, payload

# UDPプロトコルの作成
def udp_protocol_header(room_name, token):
    return (
        len(room_name).to_bytes(1, "big")
        + len(token).to_bytes(1, "big")
    )

# UDPパケットの作成
def create_udp_packet(header, room_name, token, msg):
    return (
        header
        + room_name.encode()
        + token.encode()
        + msg.encode()
    )

# UDPパケットの解析
def parse_udp_data(data):
    room_len = data[0]
    token_len = data[1]
    curr_position = 2 + room_len

    room = data[2:curr_position].decode("utf-8")
    token = data[curr_position:curr_position + token_len].decode("utf-8")
    message = data[curr_position + token_len:].decode("utf-8")

    return room, token, message