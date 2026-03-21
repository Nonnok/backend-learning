# client.py
import sys
import socket
import threading
import functions


TCP_PORT = 9001
UDP_PORT = 9002
server_address = "127.0.0.1"
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

stop_event = threading.Event()

print("-" * 30)
print("start up Online-Chat-Messenger")
print("-" * 30)

username = input("> User name: ") # ユーザネーム

HEADER_SIZE = 32


# ルーム作成/参加
def tcp_room_manage():

    print("[ Please Choose ]")
    print("- 1: Create a new chat room.")
    print("- 2: Join Chat room.")
    while True:
        # 正しい入力がなされるまで繰り返し
        try:
            operation = int(input("> enter 1 or 2: ")) # 操作コード
            if operation in (1, 2):
                break
        except ValueError:
            pass
        print("[Failue] invalid input. you can enter 1 or 2.")

    room_name = input("> Room name: ") # チャットルームの名前

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.connect((server_address, TCP_PORT))

    header = functions.create_tcrp_header(len(room_name), operation, 0, len(username))
    functions.send_tcrp_packet(tcp_sock, header, room_name.encode() + username.encode())

    token = tcp_request(tcp_sock)
    if token == "failed":
        print("- Request failed. Exit the program.")
        end_chat()

    return room_name, token

def tcp_request(sock):
    # ステータスコード
    RESPONSE = 1
    SUCCESS = 2
    while True:
        response_header = functions.recv_exact(sock, HEADER_SIZE)
        _, _, state, data_len = functions.parse_tcp_header(response_header)
        data = functions.recv_exact(sock, data_len).decode("utf-8")

        if state == SUCCESS:
            token = data
            sock.close()
            return token
        elif state == RESPONSE:
            print(data)
        else:
            print(data)
            return "failed"



# UDP 受信
def receive_loop():
    while not stop_event.is_set():
        try:
            data, address = udp_sock.recvfrom(4096)
            data_str = data.decode("utf-8")

            print(data_str)

            if data_str == "- The room has closed.":
                end_chat()
            if data_str == "- You have timed out.":
                end_chat()

        except OSError as err:
            print(err)
            break

# UDP 送信
def send_loop(room, token):
    print(f"* chat started on {room}")

    # サーバに参加を通知
    header = functions.udp_protocol_header(room, token)
    accept_msg = functions.create_udp_packet(header, room, token, "+ joined")
    udp_sock.sendto(accept_msg, (server_address, UDP_PORT))

    while not stop_event.is_set():
        try:
            msg = input()
            if len(msg.encode()) > 4096:
                print("[Failue] The message is too long.")
                continue

            header = functions.udp_protocol_header(room, token)
            payload = functions.create_udp_packet(header, room, token, msg)

            udp_sock.sendto(payload, (server_address, UDP_PORT))

        except OSError as err:
            print(err)
            break

# チャット終了
def end_chat():
    stop_event.set()
    udp_sock.close()
    print("\n---- end ----")
    sys.exit()


# メイン処理
room, token = tcp_room_manage()

threading.Thread(
    target = receive_loop,
    daemon=True
).start()

try:
    send_loop(room, token)
except KeyboardInterrupt:
    # 退出をサーバに通知
    header = functions.udp_protocol_header(room, token)
    payload = functions.create_udp_packet(header, room, token, f"- {username} left.")
    # ソケットを閉じ、システムを終了する
    udp_sock.sendto(payload, (server_address, UDP_PORT))
    end_chat()