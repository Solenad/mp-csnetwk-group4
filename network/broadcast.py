import socket
import base64
import os


def send_hello(my_info):
    message = (
        "LSNP/1.0\n"
        "TYPE: PROFILE\n"
        f"USER_ID: {my_info['username']}@{get_local_ip()}\n"
        f"DISPLAY_NAME: {my_info['username']}\n"
        f"STATUS: {my_info.get('status', 'Active')}\n"
    )

    if "avatar_path" in my_info:
        avatar_path = my_info["avatar_path"]
        try:
            if os.path.isfile(avatar_path):
                file_size = os.path.getsize(avatar_path)
                if file_size > 20 * 1024:  # 20KB limit
                    print(
                        f"[Warning] Avatar too large ({
                            file_size} bytes), skipping"
                    )
                else:
                    ext = os.path.splitext(avatar_path)[1].lower()
                    mime_types = {
                        ".png": "image/png",
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".gif": "image/gif",
                    }
                    avatar_type = mime_types.get(ext, "application/octet-stream")

                    with open(avatar_path, "rb") as f:
                        avatar_data = base64.b64encode(f.read()).decode("utf-8")

                    message += (
                        f"AVATAR_TYPE: {avatar_type}\n"
                        "AVATAR_ENCODING: base64\n"
                        f"AVATAR_DATA: {avatar_data}\n"
                    )
                    print(
                        f"[Debug] Included avatar ({
                            avatar_type}, {file_size} bytes)"
                    )
            else:
                print(f"[Warning] Avatar file not found: {avatar_path}")
        except Exception as e:
            print(f"[Error] Failed to process avatar: {str(e)}")

    message += "\n"

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(message.encode(), ("255.255.255.255", my_info["port"]))


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def print_profile_non_verbose(profile_data):
    print(f"{profile_data['DISPLAY_NAME']}: {profile_data['STATUS']}")
    if "AVATAR_DATA" in profile_data:
        print("[Profile picture available]")


my_info = {
    "username": "Admin",
    "hostname": socket.gethostname(),
    "port": 2425,
    "user_id": f"Admin{get_local_ip()}",
    "avatar_path": "sample.png",
}
