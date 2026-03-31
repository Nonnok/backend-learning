import os
import json
import uuid
import subprocess

import functions


# --------
# 引数入力
# --------
# 解像度変更の引数取得
def prompt_resize_args():
    print("[ Resolution preset ]")
    print("2160p | 1440p | 1080p | 720p | 480p")
    print("* Please enter numbers only. *")
    while True:
        try:
            resolution = int(input("> select: "))
            if resolution in (2160, 1440, 1080, 720, 480):
                break
        except ValueError:
            pass
        print("[Failed] invalid input.")
    return [resolution]

# アスペクト比変更の引数取得
def prompt_aspect_ratio_args():
    print("[ Aspect preset ]")
    print("16:9 | 9:16 | 1:1 | 4:3 ")
    while True:
        aspect_ratio = input("> select: ")
        if aspect_ratio in ("16:9", "9:16", "1:1", "4:3"):
            break
        print("[Failed] invalid input.")
    return [aspect_ratio]

# 指定された時間範囲からGIFもしくはWEBMを作成の引数取得
def prompt_export_clip_args():
    while True:
        try:
            start_time = float(input("> start time: "))
            if start_time < 0:
                print("[Failed] Please enter a number greater than or equal to 0.")
                continue
            break
        except ValueError:
            print("[Failed] invalid input.")
            pass
    while True:
        try:
            duration = float(input("> duration: "))
            if duration <= 0:
                print(f"[Failed] duration must be > 0.")
                continue
            break
        except ValueError:
            print("[Failed] invalid input.")
    while True:
        format = str(input("> gif or webm: "))
        if format in ("gif", "webm"):
            break
        print("[Failed] Please enter 'gif' or 'webm'.")
        pass
    return (start_time, duration, format)



# --------
# 処理実行
# --------
# ファイル名取得
def get_output_file_name(media_type, work_dir):
    output_file_name = f"{str(uuid.uuid4())}.{media_type}"
    output_path = os.path.join(work_dir, output_file_name)
    return output_path, output_file_name


# ファイルサイズの圧縮
def compress(file_name, work_dir):
    output_path, output_file_name = get_output_file_name("mp4", work_dir)
    operation_arr = [
        "ffmpeg",
        "-i", file_name,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]

    err = do_operation(operation_arr)
    if err is not None:
        return err, None, "err_msg"

    return output_path, output_file_name, "mp4"


# ------------
# 解像度の変更
def resize(file_name, size, work_dir):
    output_path, output_file_name = get_output_file_name("mp4", work_dir)
    operation_arr = ["ffmpeg", "-i", file_name, "-vf", f"scale=-2:{size}",output_path]

    err = do_operation(operation_arr)

    if err is not None:
        return err, None, "err_msg"

    return output_path, output_file_name, "mp4"


# ------------------
# アスペクト比の変更
def aspect_ratio(file_name, ratio, work_dir):
    output_path, output_file_name = get_output_file_name("mp4", work_dir)

    w_ratio, h_ratio = map(int, ratio.split(":"))
    target = f"{w_ratio}/{h_ratio}"

    vf = (
        "pad="
        f"w='if(gte(iw/ih,{target}), iw, ih*{target})':"
        f"h='if(gte(iw/ih,{target}), iw*{h_ratio}/{w_ratio}, ih)':"
        "x='(ow-iw)/2':"
        "y='(oh-ih)/2':"
    )

    operation_arr = ["ffmpeg", "-i", file_name, "-vf", vf, output_path]

    err = do_operation(operation_arr)
    if err is not None:
        return err, None, "err_msg"


    return output_path, output_file_name, "mp4"


# --------------------------------
# 動画ファイルを音声ファイルに変換
def video_to_audio(file_name, work_dir):
    output_path, output_file_name = get_output_file_name("mp3", work_dir)
    operation_arr = ["ffmpeg", "-i", file_name, output_path]

    err = do_operation(operation_arr)


    if err is not None:
        return err, None, "err_msg"
    return output_path, output_file_name, "mp3"


# -------------------------------------------
# 指定された時間範囲からGIFもしくはWEBMを作成
def export_clip(file_name, start_time, duration, format, work_dir):
    output_path, output_file_name = get_output_file_name(format, work_dir)

    # WEBM生成
    if format == "webm":
        operation_arr = [
            "ffmpeg", "-y",
            "-i", file_name,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c:v", "libvpx-vp9",
            "-crf", "32",
            "-b:v", "0",
            output_path
        ]
        err = do_operation(operation_arr)
        if err is not None:
            return err, None, "err_msg"

    # GIF生成
    if format == "gif":
        palette = os.path.join(work_dir, f"{str(uuid.uuid4())}_palette.png")
        vf = "fps=15,scale=480:-2:flags=lanczos"

        try:
            cmd1 = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-t", str(duration),
                "-i", file_name,
                "-vf", f"{vf},palettegen",
                palette
            ]
            err = do_operation(cmd1)
            if err is not None:
                return err, None, "err_msg"

            cmd2 = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-t", str(duration),
                "-i", file_name,
                "-i", palette,
                "-lavfi", f"{vf}[x];[x][1:v]paletteuse",
                output_path
            ]
            err = do_operation(cmd2)
            if err is not None:
                return err, None, "err_msg"
        finally:
            functions.del_file(palette)


    return output_path, output_file_name, format


# --------
# FFmpeg実行
def do_operation(operation_arr):
    try:
        subprocess.run(operation_arr, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as err:
        if isinstance(err.cmd, (list, tuple)):
            cmd_str = " ".join(map(str, err.cmd))
        else:
            cmd_str = str(err.cmd)
        return {
            "status": "error",
            "return_code": err.returncode,
            "cmd": truncate_text(cmd_str, max_chars=1000),
            "stderr": truncate_text(err.stderr, max_chars=3000),
        }
    return None

# ファイル形式の対応チェック
def probe_input(file_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-of", "json",
        file_path
    ]
    try:
        r = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return json.loads(r.stdout) if r.stdout else {}
    except subprocess.CalledProcessError as e:
        return None

# エラーテキストの切り取り
def truncate_text(s: str | None, max_chars: int = 6000) -> str:
    if not s:
        return ""
    if len(s) <= max_chars:
        return s

    head = max_chars // 2
    tail = max_chars - head
    return s[:head] + "\n... [truncated] ...\n" + s[-tail:]


# ------------
# 処理情報一覧
# ------------

operations_dict = {
    1: {
        "about": "Compress video size",
        "args": None,
        "operation": compress,
    },
    2: {
        "about": "Change resolution",
        "args": prompt_resize_args,
        "operation": resize,
    },
    3: {
        "about": "Change aspect ratio",
        "args": prompt_aspect_ratio_args,
        "operation": aspect_ratio,
    },
    4: {
        "about": "Convert video to audio",
        "args": None,
        "operation": video_to_audio,
    },
    5: {
        "about": "Create GIF or WEBM within a specified time range",
        "args": prompt_export_clip_args,
        "operation": export_clip,
    },
}