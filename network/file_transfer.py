import os
import math
import base64
import time
import mimetypes

from network.message_sender import send_file
from network.broadcast import my_info
from network.token_utils import generate_token, validate_token
from ui.utils import print_success, print_error, print_verbose, print_prompt
import config

# Tracks incoming file transfers
# Structure: { fileid: {filename, filesize, filetype, chunks, total_chunks, from_user, accepted } }
pending_files = {}

def send_file_offer(file_path, to_user):
    """
    Sends FILE_OFFER to target peer.
    """
    filename = os.path.basename(file_path)
    filesize = os.path.getsize(file_path)
    filetype, _ = mimetypes.guess_type(file_path)
    if not filetype:
        filetype = "application/octet-stream"
    fileid = os.urandom(4).hex()
    timestamp = int(time.time())

    token = generate_token(my_info["user_id"], ttl=3600, scope="file")

    message = (
        f"TYPE: FILE_OFFER\n"
        f"FROM: {my_info['user_id']}\n"
        f"TO: {to_user}\n"
        f"FILENAME: {filename}\n"
        f"FILESIZE: {filesize}\n"
        f"FILETYPE: {filetype}\n"
        f"FILEID: {fileid}\n"
        f"DESCRIPTION: Sent via LSNP\n"
        f"TIMESTAMP: {timestamp}\n"
        f"TOKEN: {token}\n\n"
    )

    send_file(message, to_user)
    return fileid


def send_file_chunks(file_path, to_user, fileid, chunk_size=256):
    """
    Sends FILE_CHUNK messages for the given file.
    """
    with open(file_path, "rb") as f:
        file_data = f.read()

    total_chunks = math.ceil(len(file_data) / chunk_size)
    token = generate_token(my_info["user_id"], ttl=3600, scope="file")

    for i in range(total_chunks):
        chunk_data = file_data[i * chunk_size:(i + 1) * chunk_size]
        encoded_data = base64.b64encode(chunk_data).decode()

        message = (
            f"TYPE: FILE_CHUNK\n"
            f"FROM: {my_info['user_id']}\n"
            f"TO: {to_user}\n"
            f"FILEID: {fileid}\n"
            f"CHUNK_INDEX: {i}\n"
            f"TOTAL_CHUNKS: {total_chunks}\n"
            f"CHUNK_SIZE: {chunk_size}\n"
            f"TOKEN: {token}\n"
            f"DATA: {encoded_data}\n\n"
        )

        send_file(message, to_user)


def handle_file_offer(msg_dict):
    """
    Called when a FILE_OFFER is received.
    """
    if not validate_token(msg_dict.get("TOKEN"), expected_scope="file"):
        if config.verbose_mode:
            print_verbose(f"[{time.time()}] Invalid/expired token for FILE_OFFER from {msg_dict['FROM']}")
        return

    fileid = msg_dict["FILEID"]
    filename = msg_dict["FILENAME"]
    filesize = int(msg_dict["FILESIZE"])
    filetype = msg_dict["FILETYPE"]

    # Ask user in non-verbose mode
    if not config.verbose_mode:
        print(f"User {msg_dict['FROM']} is sending you a file do you accept? (y/n)")
        choice = input("> ").strip().lower()
        accepted = choice.startswith("y")
    else:
        accepted = True  # auto-accept in verbose mode for debugging

    pending_files[fileid] = {
        "filename": filename,
        "filesize": filesize,
        "filetype": filetype,
        "chunks": {},
        "total_chunks": None,
        "from_user": msg_dict["FROM"],
        "accepted": accepted
    }

    if config.verbose_mode:
        print_verbose(f"[FILE_OFFER] {msg_dict['FROM']} -> {filename} ({filesize} bytes), accepted={accepted}")

def handle_file_chunk(msg_dict):
    """
    Called when a FILE_CHUNK is received.
    """
    if not validate_token(msg_dict.get("TOKEN"), expected_scope="file"):
        if config.verbose_mode:
            print_verbose(f"[{time.time()}] Invalid/expired token for FILE_CHUNK from {msg_dict['FROM']}")
        return

    fileid = msg_dict["FILEID"]
    if fileid not in pending_files:
        if config.verbose_mode:
            print_verbose(f"Ignoring chunk for unknown file {fileid}")
        return

    file_info = pending_files[fileid]
    if not file_info.get("accepted", False):
        if config.verbose_mode:
            print_verbose(f"Ignoring chunk for rejected file {fileid}")
        return

    index = int(msg_dict["CHUNK_INDEX"])
    total = int(msg_dict["TOTAL_CHUNKS"])
    data = base64.b64decode(msg_dict["DATA"])

    file_info["chunks"][index] = data
    file_info["total_chunks"] = total

    if len(file_info["chunks"]) == total:
        file_data = b"".join(file_info["chunks"][i] for i in range(total))
        with open(file_info["filename"], "wb") as f:
            f.write(file_data)

        if not config.verbose_mode:
            print(f"File transfer of {file_info['filename']} is complete")
        else:
            print_verbose(f"[FILE_COMPLETE] {file_info['filename']} ({file_info['filesize']} bytes) saved")

        send_file_received(file_info["from_user"], fileid)
        del pending_files[fileid]


def send_file_received(to_user, fileid):
    """
    Sends FILE_RECEIVED confirmation.
    """
    timestamp = int(time.time())
    message = (
        f"TYPE: FILE_RECEIVED\n"
        f"FROM: {my_info['user_id']}\n"
        f"TO: {to_user}\n"
        f"FILEID: {fileid}\n"
        f"STATUS: COMPLETE\n"
        f"TIMESTAMP: {timestamp}\n\n"
    )
    send_file(message, to_user)


def handle_incoming(msg_dict):
    """
    Dispatch for FILE_* messages.
    """
    msg_type = msg_dict["TYPE"]

    if msg_type == "FILE_OFFER":
        handle_file_offer(msg_dict)
    elif msg_type == "FILE_CHUNK":
        handle_file_chunk(msg_dict)
    elif msg_type == "FILE_RECEIVED":
        if config.verbose_mode:
            print_verbose(f"[FILE_RECEIVED] {msg_dict['FROM']} confirmed file {msg_dict['FILEID']} received.")
        # Non-verbose: print nothing
