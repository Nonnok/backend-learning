import os
import socket
import uuid
import json
import threading
import shutil

import functions
import operations
import errors

# TCP通信設定
server_port = 9001 #upload/download
status_port = 9002 # status only
server_address = "0.0.0.0"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

sock.bind((server_address, server_port))
sock.listen()

status_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
status_sock.bind((server_address, status_port))
status_sock.listen()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_ROOT = os.path.join(BASE_DIR, "tmp")

state_lock = threading.Lock()

# IPアドレス
ip_jobs = {}
# ジョブの状態を保存/クライアントへのレスポンスに使用
jobs = {}
# ジョブごとのロック
send_locks = {}

# 辞書の要素削除
def del_dict_items(dict, key):
    try:
        del dict[key]
    except KeyError:
        pass

# 任意のdictを送る
def safe_send_packet(conn, job_id, dict, media_type=None, payload=None):
    with state_lock:
        send_lock = send_locks.get(job_id)
    if send_lock is None:
        return False
    with send_lock:
        functions.send_mmp_packet(conn, dict, media_type, payload)
    return True

# jobのスナップショットを送る
def safe_send_job_status(conn, job_id, media_type=None, payload=None):
    with state_lock:
        send_lock = send_locks.get(job_id)
        job_snapshot = jobs.get(job_id)

    if send_lock is None or job_snapshot is None:
        return False

    with send_lock:
        functions.send_mmp_packet(conn, job_snapshot, media_type, payload)
    return True

print(f"\nstarting up upload/download on {server_port}:{server_address}\n")
print(f"\nstarting up status on {status_port}:{server_address}\n")

# upload/download: 複数クライアントのコネクションを受け付ける
def conn_loop():
    while True:
        conn, addr = sock.accept()
        print(f"+ [accept_client] {addr[0]}:{addr[1]}")

        threading.Thread(
            target = file_processing,
            args = (conn, addr),
            daemon = True
        ).start()

# status: 別ポートでステータス確認専用コネクションを受け付ける
def status_conn_loop():
    while True:
        conn, addr = status_sock.accept()
        threading.Thread(
            target=handle_status_connection,
            args = (conn, addr),
            daemon=True
        ).start()


# check status
def handle_status_connection(conn, addr):
    try:
        while True:
            header = functions.recv_exact(conn, functions.MMP_HEADER_SIZE)
            json_size, media_type_size, payload_size = functions.unpack_mmp_header(header)

            if json_size > functions.MAX_JSON_SIZE or json_size <= 0:
                err = errors.get_err_response("BAD_REQUEST", "Invalid header: json_size out of range.")
                functions.send_mmp_packet(conn, err, None, None)
                return

            if media_type_size > 0:
                err = errors.get_err_response("BAD_REQUEST", "Invalid header: media_type_size must be 0 for status requests.")
                functions.send_mmp_packet(conn, err, None, None)
                return

            if payload_size > 0:
                err = errors.get_err_response("BAD_REQUEST", "Invalid header: payload_size must be 0 for status requests.")
                functions.send_mmp_packet(conn, err, None, None)
                return

            json_data = functions.recv_exact(conn, json_size).decode("utf-8")
            req = json.loads(json_data)

            if req.get("request_type") != "status":
                err = errors.get_err_response("BAD_REQUEST", "request_type must be 'status'.")
                functions.send_mmp_packet(conn, err, None, None)
                continue

            req_job_id = req.get("job_id")
            if not req_job_id:
                err = errors.get_err_response("BAD_REQUEST", "job_id is required.")
                functions.send_mmp_packet(conn, err, None, None)
                continue

            with state_lock:
                job_snapshot = jobs.get(req_job_id)
                ip_job_id = ip_jobs.get(addr[0])

            if job_snapshot is None:
                err = errors.get_err_response("JOB_ID_NOT_FOUND", "job_id does not exist.")
                functions.send_mmp_packet(conn, err, None, None)
                continue

            if ip_job_id != req_job_id:
                err = errors.get_err_response("JOB_ID_MISMATCH", "job_id is not associated with this IP.")
                functions.send_mmp_packet(conn, err, None, None)
                continue

            functions.send_mmp_packet(conn, job_snapshot, None, None)

    except (OSError, ConnectionError, json.JSONDecodeError, UnicodeDecodeError):
        return
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()



# upload/download
def file_processing(conn, addr):
    job_id = None
    work_dir = None
    file_name = None
    output = None

    try:
        job_id = str(uuid.uuid4())

        # IPアドレスごとに処理を1つに制限
        with state_lock:
            if addr[0] in ip_jobs:
                overlap = True
            else:
                ip_jobs[addr[0]] = job_id
                overlap = False

        if overlap:
            err = errors.get_err_response(
                "IP_OVERLAP",
                f"IP[{addr[0]}] address is already in use for processing."
            )
            functions.send_mmp_packet(conn, err, None, None)
            return


        # ファイルを保存するディレクトリを作成
        work_dir = os.path.join(TMP_ROOT, job_id)
        os.makedirs(work_dir, exist_ok=True)

        # ヘッダー受信
        header = functions.recv_exact(conn, 8)
        json_size, media_type_size, payload_size = functions.unpack_mmp_header(header)

        if not functions.check_mmp_header_recv_file(conn, json_size, media_type_size, payload_size):
            return

        # データ長から、各データを受信
        try:
            json_data = functions.recv_exact(conn, json_size).decode("utf-8")
            prompts_dict = json.loads(json_data)
        except (UnicodeDecodeError, json.JSONDecodeError):
            err = errors.get_err_response("BAD_REQUEST","Invalid JSON payload.")
            functions.send_mmp_packet(conn, err, None, None)
            return

        media_type = functions.recv_exact(conn, media_type_size).decode("utf-8")

        # payload_size分のファイルを受信
        file_name = functions.recv_file_exact(conn, payload_size, media_type, save_dir=work_dir)

        # ジョブのステータスをdictで管理
        with state_lock:
            jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "error": None,
            }
            send_locks[job_id] = threading.Lock()
        safe_send_job_status(conn, job_id)

        # JSONファイル検証
        prompt_code = prompts_dict.get("prompt_code")
        if not isinstance(prompt_code, int):
            err = errors.get_err_response("BAD_REQUEST", "prompt_code must be an integer.")
            safe_send_packet(conn, job_id, err)
            return

        if prompt_code not in operations.operations_dict:
            err = errors.get_err_response("BAD_REQUEST", f"Unknown prompt_code: {prompt_code}")
            safe_send_packet(conn, job_id, err)
            return

        prompts_args = prompts_dict.get("prompt_args")

        # コードから処理関数を取得
        operation = operations.operations_dict[prompt_code]["operation"]

        # ジョブのステータスを実行中に変更
        with state_lock:
            jobs[job_id]["status"] = "processing"
        safe_send_job_status(conn, job_id)

        # ファイル形式がFFmpegに対応しているかチェック
        probe = operations.probe_input(file_name)
        if probe is None:
            err = errors.get_err_response(
                "UNSUPPORTED_MEDIA_TYPE",
                "FFmpeg could not read this file (unsupported format or corrupted)."
            )
            safe_send_packet(conn, job_id, err)
            return

        # 処理を実行
        if prompts_args == None:
            output, file_name, media_type = operation(file_name, work_dir)
        else:
            output, file_name, media_type = operation(file_name, *prompts_args, work_dir)

        # エラー処理
        if media_type == "err_msg":
            with state_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = output
            media_type = None
            err = errors.get_err_response(
                "FFMPEG_FAILED",
                "FFmpeg processing failed.",
                detail=output
            )
            # エラーレスポンスを送って終了
            safe_send_packet(conn, job_id, err)
            return


        # 完了
        else:
            with state_lock:
                jobs[job_id]["status"] = "done"
                jobs[job_id]["output_file"] = file_name

        # 結果送信 (status JSON + media_type + payload(file path))
        safe_send_job_status(conn, job_id, media_type, output)


    except ConnectionError:
        print("- [Leave] client disconnected.\n")
    except Exception as error:
        err = errors.get_err_response("INTERNAL_ERROR", "Unexpected server error.", detail=str(error))
        if not (job_id and safe_send_packet(conn, job_id, err)):
            try:
                functions.send_mmp_packet(conn, err, None, None)
            except OSError:
                pass
    finally:
        with state_lock:
            if job_id is not None:
                del_dict_items(ip_jobs, addr[0])
                del_dict_items(jobs, job_id)
                del_dict_items(send_locks, job_id)

        if work_dir is not None and os.path.isdir(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)
            print(f"- [deleted dir] {work_dir}")
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()


# 起動
threading.Thread(target=status_conn_loop, daemon=True).start()

try:
    conn_loop()
except KeyboardInterrupt:
    print("\n---close the server---\n")
    sock.close()
    status_sock.close()