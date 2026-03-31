import sys
import time
import json
import socket
import mimetypes
import threading
from pathlib import Path

import functions
import operations

server_port = 9001
status_port = 9002
server_address = "127.0.0.1"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #upload/download
status_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #status only

stop_event = threading.Event()

job_id_ready = threading.Event()
download_path = Path.home() / "Downloads"


def end_sys():
    print("\n ---- end ----")
    stop_event.set()
    try:
        sock.close()
    except OSError:
        pass
    try:
        status_sock.close()
    except OSError:
        pass
    sys.exit()

try:
    sock.connect((server_address, server_port))
except ConnectionRefusedError:
    print("[Failed] The server is not runnning.")
    end_sys()

try:
    status_sock.connect((server_address, status_port))
except ConnectionRefusedError:
    print("[Failed] The status server is not runnning.")
    end_sys()

REQUEST_INTERVAL = 60
state = {
    "job_id": None,
}


# --------------
# リクエスト入力
def get_operation():
    # 処理一覧から各処理のナンバーと処理内容を表示
    print("[ Method List ]")
    for key, info in operations.operations_dict.items():
        print(f"- {key}: {info['about']}.")

    # 処理を取得
    while True:
        try:
            prompt_code = int(input("> input method number: "))
            if prompt_code in operations.operations_dict.keys():
                break
        except ValueError:
            pass
        print(f"[Failed] invalid input. you can enter {list(operations.operations_dict.keys())}.")

    # 処理の引数を取得
    prompt_args = operations.operations_dict[prompt_code]["args"]

    if prompt_args is None:
        prompt_args = None
    else:
        prompt_args = prompt_args()

    # 処理の種類と引数を格納
    prompts_dict = {
        "prompt_code": prompt_code,
        "prompt_args": prompt_args
    }

    return prompts_dict


# --------------
# ファイルを選択
def select_file():
    while True:
        raw = input("> input filepath: ").strip().strip('"').strip("'")
        if not raw:
            print("[Failed] empty input.")
            continue

        path = Path(raw).expanduser()

        if not path.exists():
            print(f"[Failed] file not found: {path}")
            continue
        if not path.is_file():
            print(f"[Failed] not a file: {path}")
            continue

        path = path.resolve()

        mime, _ = mimetypes.guess_type(str(path))
        if not mime:
            print("[Failed] could not guess file type from extension.")
            continue
        if not mime.startswith("video/"):
            print(f"[Failed] Only supported movie file. (got {mime})")
            continue

        media_type = mime.split("/", 1)[1]

        return media_type, str(path)




# --------------
# upload/download レスポンス受信
def receive_loop():
    while True:
        try:
            header = functions.recv_exact(sock, functions.MMP_HEADER_SIZE)
            json_size, media_type_size, payload_size = functions.unpack_mmp_header(header)

            if json_size > functions.MAX_JSON_SIZE or json_size <= 0:
                print("[Failed] An invalid JSON file size was received.")
                return

            json_data = functions.recv_exact(sock, json_size).decode("utf-8")
            dict_data = json.loads(json_data)

            if dict_data.get("status") == "error":
                print("---- Error ----")
                print(json.dumps(dict_data.get("error"), ensure_ascii=False, indent=2))
                end_sys()
                return

            if dict_data["status"] == "done":
                if media_type_size not in (1, 2, 3, 4):
                    print("[Failed] An invalid media type was received.")
                    return

                if payload_size > functions.MAX_PAYLOAD_SIZE or payload_size <= 0:
                    print("[Failed] An invalid payload size was received.")
                    return


            if state["job_id"] is None and dict_data.get("job_id"):
                state["job_id"] = dict_data["job_id"]
                job_id_ready.set()

            print("---- Response ----")
            for key, value in dict_data.items():
                if value is None:
                    continue
                print(f"[{key}] {value}")


            if media_type_size:
                media_type = functions.recv_exact(sock, media_type_size).decode("utf-8")
            else:
                media_type = None

            if payload_size and media_type:
                functions.recv_file_exact(sock, payload_size, media_type, download_path)

            if dict_data["status"] == "done":
                end_sys()
                return

        except OSError as err:
            print(err)
            end_sys()
            return

# --------------
# 定期リクエスト
def prosess_status_check():
    try:
        job_id_ready.wait()

        while not stop_event.is_set():
            time.sleep(REQUEST_INTERVAL)

            request_dict = {
                "job_id": state["job_id"],
                "request_type": "status"
            }

            functions.send_mmp_packet(status_sock, request_dict, None, None)

            header = functions.recv_exact(status_sock, functions.MMP_HEADER_SIZE)
            json_size, media_type_size, payload_size = functions.unpack_mmp_header(header)

            if json_size > functions.MAX_JSON_SIZE or json_size <= 0:
                print("[Failed] An invalid JSON file size was received.")
                return

            json_data = functions.recv_exact(status_sock, json_size).decode("utf-8")
            dict_data = json.loads(json_data)

            print("---- Status (polling) ----")
            if dict_data.get("status") == "error":
                print(json.dumps(dict_data.get("error"), ensure_ascii=False, indent=2))
                end_sys()
                return

            for key, value in dict_data.items():
                if value is None:
                    continue
                print(f"[{key}] {value}")

            if media_type_size:
                functions.discard_exact(status_sock, media_type_size)
            if payload_size:
                functions.discard_payload_exact(status_sock, payload_size)

    except (OSError, BrokenPipeError, ConnectionError):
        end_sys()


# ----------
# メイン処理
# ----------
try:
    prompt = get_operation()
    media_type, path = select_file()

    # upload/download コネクションでアップロード
    functions.send_mmp_packet(sock, prompt, media_type, path)

    threading.Thread(
        target = prosess_status_check,
        daemon=True
    ).start()

    receive_loop()

except KeyboardInterrupt:
    end_sys()
except BrokenPipeError:
    print("[Failed] The server has been closed.")
    end_sys()