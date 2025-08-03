# [CSNETWK] Local Social Networking Protocol

Implementation of LSNP over UDP for CSNETWK.
Includes peer discovery, messaging, file sharing, group chat, and game support.

## Authors
DIZON, Rohann Gabriel D.  
FABRICANTE, Jeruel I.  
PEROL, Francine Nicole T.

## Features
- [x] Peer discovery (PING, PROFILE)
- [x] Simultaneous send/receive
- [ ] Messaging (POST, DM, FOLLOW, UNFOLLOW)
- [ ] Token validation
- [ ] File sharing
- [ ] Group messaging
- [ ] Tic Tac Toe game

## Setup

1. Clone the repository:
```bash
git clone https://github.com/Solenad/mp-csnetwk-group4.git
```

2. Install Python dependencies:
```bash
pip install -r dependencies.txt
```

3. Run `main.py` (server):
```bash
python main.py
```

## Usage
Check for list of commands:
```bash
>> help

Available commands:
 - exit
 - whoami
 - peers
 - send
 - groups
 - help
```

## Command Registry

| Command     | Description                                                                 |
|-------------|-----------------------------------------------------------------------------|
| `exit`      | Gracefully shuts down the application.                                       |
| `whoami`    | Displays your current LSNP identity (UUID, name, profile info).             |
| `peers`     | Lists all known active peers with their name, UUID, IP, and last seen time. |
| `send`      | Initiates a direct message (DM) to a selected peer. *(To be implemented)*   |
| `groups`    | Displays groups the user is part of. *(To be implemented)*                  |
| `help`      | Displays the list of available commands with brief descriptions.            |



## License
This project is licensed under the MIT License. Copyright (c) 2025 roe
