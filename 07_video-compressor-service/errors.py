ERRORS = {
    "BAD_REQUEST": {
        "code": 1001,
        "solution": [
          "Check request JSON fields and types.",
          "Restart the client and retry."
        ],
    },
    "UNSUPPORTED_MEDIA_TYPE": {
        "code": 1002,
        "solution": [
          "Convert the file to a supported format (e.g., mp4) and retry.",
          "Confirm the media_type is correct(e.g., mp4, webm, mov)."
        ],
    },
    "PAYLOAD_TOO_LARGE": {
        "code": 1003,
        "solution": [
          "Use a smaller file (must be < 1TB)",
          "Trim the video or lower bitrate, then retry."
        ],
    },
    "IP_OVERLAP": {
        "code": 2001,
        "solution": [
            "Wait until the previous job from the same IP finishes, then retry.",
            "Or run the client from a different IP address."
        ],
    },
    "JOB_ID_NOT_FOUND": {
        "code": 2002,
        "solution": [
            "Restart the client and create a new job.",
            "Do not reuse an old job_id."
        ],
    },
    "JOB_ID_MISMATCH": {
        "code": 2003,
        "solution": [
            "Restart the client and use the job_id returned by the server for this connection only."
        ],
    },
    "FFMPEG_FAILED": {
        "code": 3001,
        "solution": [
            "Try a different input file or format (mp4 is recommended).",
            "Check that the input file is not corrupted.",
            "If you manage the server, verify ffmpeg is installed and available in PATH."
        ],
    },
    "INTERNAL_ERROR": {
        "code": 9000,
        "solution": [
            "Retry later.",
            "If the problem persists, check server logs."
        ],
    },
}

# エラーレスポンス
def get_err_response(name: str, message: str | None = None, detail=None) -> dict:
    meta = ERRORS.get(name, ERRORS["INTERNAL_ERROR"])
    err = {
        "status": "error",
        "error": {
              "code": meta["code"],
              "name": name,
              "message": message or name,
              "solution": meta["solution"],
        },
    }
    if detail is not None:
        err["error"]["detail"] = detail
    return err