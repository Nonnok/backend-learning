import os
import json
import uuid

import errors

MAX_SEGMENT_SIZE = 1400
MAX_JSON_SIZE = 65535
MAX_MEDIA_TYPE_SIZE = 4
MAX_PAYLOAD_SIZE = 10 ** 12 # 1TB


# 指定サイズまでデータを受け取る
def recv_exact(conn, size):
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise ConnectionError
        data += chunk
    return data

# 非対応データの読み捨て
def discard_exact(conn, size: int):
    """Receive and discard exactly `size` bytes(no disk I/O)."""
    remaining = size
    while remaining > 0:
        chunk = conn.recv(min(MAX_SEGMENT_SIZE, remaining))
        if not chunk:
            raise ConnectionError
        remaining -= len(chunk)

# 非対応ペイロードの読み捨て
def discard_payload_exact(conn, size: int):
    """Discard payload bytes without writing to disk."""
    discard_exact(conn, size)

# ------------
# ファイル操作
# ------------

# 指定サイズのファイルを受信する
def recv_file_exact(conn, size, media_type, save_dir="."):
    remaining = size
    file_id = str(uuid.uuid4())
    os.makedirs(save_dir, exist_ok=True)

    tmp_path = os.path.join(save_dir, f"{file_id}.tmp")
    output_path = os.path.join(save_dir, f"{file_id}.{media_type}")

    try:
        with open(tmp_path, "wb") as file:
            while remaining > 0:
                curr_size = min(MAX_SEGMENT_SIZE, remaining)
                chunk = recv_exact(conn, curr_size)
                if not chunk:
                    raise IOError("[ Failed ] file ended before expected size.")
                file.write(chunk)
                remaining -= len(chunk)

        if os.path.exists(tmp_path):
            os.rename(tmp_path, output_path)
            print(f"[Success] {format_file_size(size)} file receive.")
            print(f"[ Saved ] {output_path}")

            return output_path
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# 指定サイズのファイルを送信する
def send_file_exact(conn, size, file_path):
    remaining = size
    with open(file_path, "rb") as file:
        while remaining > 0:
            curr_size = min(MAX_SEGMENT_SIZE, remaining)
            chunk = file.read(curr_size)
            if not chunk:
                raise IOError("[ Failed ] file ended before expected size.")
            conn.sendall(chunk)
            remaining -= len(chunk)
    print(f"[Success] {format_file_size(size)} file sent.")


# 指定のファイルを削除する
def del_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"[deleted] {file_path}")
    else:
        print(f"[Failed] {file_path} not found.")



# ファイルサイズの変換
def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]

    i = 0
    size = float(size_bytes)

    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1

    return f"{size:.2f} {units[i]}"


# ------------------------------
# MMP（Multiple Media Protocol）
# ------------------------------
MMP_HEADER_SIZE = 8
JSON_SIZE = 2
MEDIA_TYPE_SIZE = 1
PAYLOAD_SIZE = 5

# MMPヘッダーの作成
def pack_mmp_header(json_binary_size, media_type_size, payload_size):

    json_size_binary = json_binary_size.to_bytes(JSON_SIZE, "big")

    media_type_size_binary = media_type_size.to_bytes(MEDIA_TYPE_SIZE, "big")

    payload_size_binary = payload_size.to_bytes(PAYLOAD_SIZE, "big")

    header = (
        json_size_binary
        + media_type_size_binary
        + payload_size_binary
    )

    return header


# MMPヘッダーの解釈
def unpack_mmp_header(header):
    json_size = int.from_bytes(header[0:2], "big")
    media_type_size = int.from_bytes(header[2:3], "big")
    payload_size = int.from_bytes(header[3:], "big")

    return (json_size, media_type_size, payload_size)

# MMPヘッダーのバリデーション (upload/download)
def check_mmp_header_recv_file(conn, json_size, media_type_size, payload_size):
    if json_size > MAX_JSON_SIZE or json_size <= 0:
        err = errors.get_err_response("BAD_REQUEST", "Invalid header: json_size out of range.")
        send_mmp_packet(conn, err, None, None)
        return False

    if media_type_size not in (1, 2, 3, 4):
        err = errors.get_err_response("BAD_REQUEST", "invalid header: media_type_size must be 1, 2, 3, 4.")
        send_mmp_packet(conn, err, None, None)
        return False

    if payload_size > MAX_PAYLOAD_SIZE:
        err = errors.get_err_response("PAYLOAD_TOO_LARGE")
        send_mmp_packet(conn, err, None, None)
        return False

    if payload_size <= 0:
        err = errors.get_err_response("BAD_REQUEST", "Invalid header: payload_size must be > 0.")
        send_mmp_packet(conn, err, None, None)
        return False

    return True


# MMPパケットの作成/送信
def send_mmp_packet(conn, dict_data, media_type, payload):
    json_data_binary = json.dumps(dict_data).encode("utf-8")

    # JSONサイズのバリデーション
    if len(json_data_binary) > MAX_JSON_SIZE:
        try:
            if isinstance(dict_data, dict) and "error" in dict_data and isinstance(dict_data["error"], dict):
                dict2 = json.loads(json.dumps(dict_data))
                dict2["error"].pop("detail", None)
                json_data_binary = json.dumps(dict2).encode("utf-8")
        except Exception:
            pass

    if len(json_data_binary) > MAX_JSON_SIZE:
        err = errors.get_err_response("INTERNAL_ERROR", "Response JSON too large to send.")
        json_data_binary = json.dumps(err).encode("utf-8")


    if media_type is None:
        media_type_binary = b""
        media_type_size = 0
    else:
        media_type_binary = media_type.encode("utf-8")
        media_type_size = len(media_type_binary)

        if media_type_size > MAX_MEDIA_TYPE_SIZE:
            err = errors.get_err_response("BAD_REQUEST", "media_type_size must be within 4 bytes.")
            json_data_binary = json.dumps(err).encode("utf-8")

            media_type_binary = b""
            media_type_size = 0
            payload = None
            payload_size = 0

    if payload is None:
        payload_size = 0
    else:
        payload_size = os.path.getsize(payload)

        # 1TB以上のファイルは受け付けない。
        if payload_size >= MAX_PAYLOAD_SIZE:
            err = errors.get_err_response("PAYLOAD_TOO_LARGE")
            json_data_binary = json.dumps(err).encode("utf-8")

            media_type_binary = b""
            media_type_size = 0
            payload = None
            payload_size = 0


    json_data_size = len(json_data_binary)

    header = pack_mmp_header(json_data_size, media_type_size, payload_size)

    conn.sendall(header)
    conn.sendall(json_data_binary)

    if media_type_size:
        conn.sendall(media_type_binary)

    if payload_size:
        send_file_exact(conn, payload_size, payload)