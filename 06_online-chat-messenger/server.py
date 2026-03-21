# server.py
import time
import socket
import secrets
import threading
import functions

TCP_PORT = 9001
UDP_PORT = 9002
server_address = "0.0.0.0"

tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

tcp_sock.bind((server_address, TCP_PORT))
tcp_sock.listen()

udp_sock.bind((server_address, UDP_PORT))

rooms = {}
token_to_room = {}

lock = threading.Lock()

HEADER_SIZE = 32
CHECK_INTERVAL = 1
TIMEOUT = 20

print(f"starting up on {TCP_PORT}:{server_address}")

# TCP手続き受け入れループ
def tcp_loop():
    while True:
        connection, address = tcp_sock.accept()

        threading.Thread(
            target = handle_tcp_client,
            args = (connection, address),
            daemon = True
        ).start()

# ルームの作成/参加
def handle_tcp_client(connection, address):
    # ヘッダーを読む
    header = functions.recv_exact(connection, HEADER_SIZE)

    room_name_len, operation, state, payload_len = functions.parse_tcp_header(header)

    # bodyを読む
    body = functions.recv_exact(connection, room_name_len + payload_len)

    room, username = functions.parse_tcp_body(body, room_name_len)
    print(f"[Request] received - room name: {room} / username: {username}")

    # ルームの作成と参加を分岐する
    if operation == 1:
        message = "accept create room"
        response_header = functions.create_tcrp_header(0, 0, 1, len(message))
        functions.send_tcrp_packet(connection, response_header, message.encode())
        create_room(connection, room, username)
    elif operation == 2:
        message = "accept join room"
        response_header = functions.create_tcrp_header(0, 0, 1, len(message))
        functions.send_tcrp_packet(connection, response_header, message.encode())
        join_room(connection, room, username)


# ルームを作成
def create_room(connection, room, username):
    token = secrets.token_hex(8)

    if room in rooms:
        message = "[Failure] Room already exists."
        print(message)
        response_header = functions.create_tcrp_header(0, 0, 3, len(message))
        functions.send_tcrp_packet(connection, response_header, message.encode())
        connection.close()
        return

    with lock:
        rooms[room] = {
            "host": token,
            "members": {
                token: {
                    "username": username,
                    "address": None, # UDP通信のアドレスは不明であるため
                    "last_seen": time.time()
                }
            }
        }

        token_to_room[token] = room

    response_header = functions.create_tcrp_header(0, 0, 2, len(token))
    functions.send_tcrp_packet(connection, response_header, token.encode())
    print(f"+ create [{room}] room success. +")
    connection.close()

# ルームに参加
def join_room(connection, room, username):
    if room not in rooms:
        message = f"[Failure] The room {room} is not found."
        print(message)
        response_header = functions.create_tcrp_header(0, 0, 3, len(message))
        functions.send_tcrp_packet(connection, response_header, message.encode())
        connection.close()
        return

    token = secrets.token_hex(8)

    with lock:
        rooms[room]["members"][token] = {
            "username": username,
            "address": None,
            "last_seen": time.time(),
        }

        token_to_room[token] = room

    response_header = functions.create_tcrp_header(0, 0, 2, len(token))
    functions.send_tcrp_packet(connection, response_header, token.encode())
    print(f"+ join [{room}] room  success. +")
    connection.close()


# メッセージの送信
def send_msg(payload, room):
    with lock:
        if room not in rooms:
            return
        members = list(rooms[room]["members"].values())
    for member in members:
        if member["address"] is None:
            continue
        try:
            udp_sock.sendto(payload, member["address"])
        except OSError:
            pass


# UDPチャットループ
def udp_loop():
    while True:
        data, address = udp_sock.recvfrom(4370)

        try:
            room, token, message = functions.parse_udp_data(data)
        except Exception as err:
            print(err)
            continue

        if token not in token_to_room:
            print(f"[Failure] The Token [{token}] is not define.")
            continue

        official_room = token_to_room[token]
        if room != official_room:
            print("[Failure] Invalid room for token.")
            continue

        with lock:
            if room not in rooms:
                continue
            if token not in rooms[room]["members"]:
                continue

            member = rooms[room]["members"][token]
            username = member["username"]


            # 初回アクセスのIPアドレス登録
            if member["address"] is None:
                member["address"] = address

            elif member["address"] != address:
                print("[Failure] Invalid address for token.")
                continue

            # 最終アクセス時間の更新
            member["last_seen"] = time.time()


        if message == "+ joined":
            text = f"+ {username} joined."

        elif message == f"- {username} left.":
            if token == rooms[room]["host"]:
                print(f"- [{username}], the host of [{room}], has timed out.")
                text = "- the room closed."
            else:
                text = message

        else:
            text = f"{username}: {message}"

        send_msg(text.encode(), room)

        print(f"> {text}")

        # ユーザの退出処理
        if message == f"- {username} left.":
            # ホストだった場合、ルームを閉じる。
            if token == rooms[room]["host"]:
                with lock:
                    targets = list(rooms[room]["members"].keys())
                    for target in targets:
                        del token_to_room[target]
                    del rooms[room]
            else:
                with lock:
                    del rooms[room]["members"][token]
                    del token_to_room[token]


# タイムアウトしたユーザの削除
# タイムアウトしたのがホストだった場合、ルームを閉じる。
def del_timeout_user():

    while True:
        time.sleep(CHECK_INTERVAL)
        now = time.time()

        host_timeout = None
        member_timeouts = []

        # タイムアウトユーザの収集
        with lock:
            for room, room_info in rooms.items():
                host = room_info["host"]
                members = room_info["members"]

                for token, info in list(members.items()):
                    if now - info["last_seen"] > TIMEOUT:
                        if token == host:
                            host_timeout = (room, token, info["username"])
                            member_timeouts.clear()
                            break
                        if now - info["last_seen"] > TIMEOUT:
                            member_timeouts.append(
                                (room, token, info["username"])
                            )
                if host_timeout:
                    break

        # 通知
        if host_timeout:
            _, _, username = host_timeout
            print(f"- [{username}], the host of [{room}], has timed out.\n  So the room will be closed.")
            send_msg("- The room has closed.".encode(), room)

        else:
            for room, token, username in member_timeouts:
                udp_sock.sendto("- You have timed out.".encode(), rooms[room]["members"][token]["address"])
                msg = f"- {username} is timeout."
                send_msg(msg.encode(), room)
                print(msg)


        # 削除処理
        with lock:
            if host_timeout:
                room, token, username = host_timeout
                targets = list(members.keys())
                for target in targets:
                    del token_to_room[target]
                del rooms[room]

            else:
                for room, token, username in member_timeouts:
                    if room not in rooms:
                        continue

                    members = rooms[room]["members"]

                    if token in members:
                        del members[token]
                        del token_to_room[token]



threading.Thread(target=tcp_loop, daemon = True).start()
threading.Thread(target = del_timeout_user, daemon = True).start()
try:
    udp_loop()
except KeyboardInterrupt:
    with lock:
        token_to_room.clear()
        rooms.clear()
        tcp_sock.close()
        udp_sock.close()
    print("\n---- end ----")