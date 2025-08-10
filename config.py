verbose_mode = False
TOKEN_TTL = {
    "broadcast": 3600,  # POST/LIKE
    "chat": 7200,  # DM
    "file": 14400,  # FILE_*
    "game": 10800,  # TICTACTOE_*
    "group": 86400,  # GROUP_*
    "follow": 3600,  # FOLLOW/UNFOLLOW
}
followed_users = set()
liked_posts = set()
active_file_transfers = {}  # Outgoing file transfers
incoming_files = {}  # Incoming file transfers
pending_file_offer = None
