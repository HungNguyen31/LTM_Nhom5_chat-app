# server.py
import socket
import threading
import json

HOST = '0.0.0.0'
PORT = 12345

clients_lock = threading.Lock()
clients = {}  # socket -> nickname

def send_json(sock, obj):
    try:
        data = json.dumps(obj, ensure_ascii=False) + '\n'
        sock.sendall(data.encode())
    except Exception as e:
        print("send error:", e)

def broadcast(obj, exclude_sock=None):
    with clients_lock:
        for s in list(clients.keys()):
            if s is exclude_sock:
                continue
            try:
                send_json(s, obj)
            except:
                pass

def handle_client(conn, addr):
    print(f"[NEW] {addr}")
    buffer = ""
    nickname = None
    try:
        while True:
            data = conn.recv(4096).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                mtype = msg.get("type")
                if mtype == "join":
                    nickname = msg.get("from", f"{addr}")
                    with clients_lock:
                        clients[conn] = nickname
                    print(f"{nickname} joined")
                    broadcast({"type":"system","content":f"{nickname} đã vào phòng."})
                elif mtype == "msg":
                    text = msg.get("content", "")
                    frm = clients.get(conn, "Unknown")
                    print(f"[MSG] {frm}: {text}")
                    broadcast({"type":"msg","from":frm,"to":"all","content":text})
                elif mtype == "private":
                    to = msg.get("to")
                    text = msg.get("content","")
                    frm = clients.get(conn, "Unknown")
                    # find recipient socket
                    with clients_lock:
                        recip = None
                        for s,n in clients.items():
                            if n == to:
                                recip = s
                                break
                    if recip:
                        send_json(recip, {"type":"private","from":frm,"to":to,"content":text})
                    else:
                        send_json(conn, {"type":"system","content":f"User {to} không tồn tại."})
                # add more types as needed
    except Exception as e:
        print("Client handler error:", e)
    finally:
        with clients_lock:
            if conn in clients:
                left_name = clients.pop(conn)
                broadcast({"type":"system","content":f"{left_name} đã rời."})
                print(f"{left_name} disconnected")
        conn.close()

def start():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"Server listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("Shutting down server.")
    finally:
        srv.close()

if __name__ == "__main__":
    start()
