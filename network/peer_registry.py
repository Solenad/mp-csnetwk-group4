peer_list = []


def get_peer_list():
    return peer_list


def add_peer(peer):
    if peer not in peer_list:
        peer_list.append(peer)
