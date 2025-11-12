import socket
import threading
import json
import hashlib  # MỚI: Thư viện để băm mật khẩu
import os       # MỚI: Để kiểm tra file accounts.json có tồn tại không

HOST = '0.0.0.0'
PORT = 12345
ACCOUNTS_FILE = 'accounts.json' # MỚI: Tên file lưu tài khoản

clients_lock = threading.Lock()
clients = {}  # socket -> nickname (Giữ nguyên)

# MỚI: Thêm một lock riêng cho việc đọc/ghi file tài khoản
# Điều này ngăn chặn 2 người đăng ký cùng lúc làm hỏng file JSON
accounts_lock = threading.Lock()

# --- MỚI: Các hàm xử lý tài khoản ---

def hash_password(password):
    """Băm mật khẩu bằng SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(hashed_password, user_password):
    """Kiểm tra mật khẩu người dùng nhập có khớp với hash đã lưu không."""
    return hashed_password == hashlib.sha256(user_password.encode()).hexdigest()

def load_accounts():
    """Đọc file tài khoản một cách an toàn (thread-safe)."""
    with accounts_lock:
        if not os.path.exists(ACCOUNTS_FILE):
            return {}  # Trả về dict rỗng nếu file chưa tồn tại
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {} # Trả về dict rỗng nếu file bị lỗi hoặc rỗng

def save_accounts(accounts):
    """Ghi file tài khoản một cách an toàn (thread-safe)."""
    with accounts_lock:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=4)

# --- Các hàm mạng (Giữ nguyên) ---

def send_json(sock, obj):
    try:
        data = json.dumps(obj, ensure_ascii=False) + '\n'
        sock.sendall(data.encode())
    except Exception as e:
        print(f"Send error: {e}")

def broadcast(obj, exclude_sock=None):
    with clients_lock:
        # Dùng list() để tạo bản sao, tránh lỗi "dictionary changed size during iteration"
        for s in list(clients.keys()):
            if s is exclude_sock:
                continue
            try:
                send_json(s, obj)
            except:
                pass # Bỏ qua nếu gửi lỗi

# --- HÀM `handle_client` (Được cập nhật nhiều nhất) ---

def handle_client(conn, addr):
    print(f"[NEW] {addr} connected.")
    buffer = ""
    nickname = None
    authenticated = False # MỚI: Biến trạng thái

    try:
        while True:
            data = conn.recv(4096).decode()
            if not data:
                break # Client ngắt kết nối
            
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue # Bỏ qua nếu JSON không hợp lệ

                mtype = msg.get("type")

                # --- MỚI: LOGIC CHƯA XÁC THỰC ---
                if not authenticated:
                    if mtype == "register":
                        content = msg.get("content", {})
                        user = content.get("username")
                        pw = content.get("password")
                        
                        if not user or not pw:
                            send_json(conn, {"type":"system", "content":"REGISTER_FAIL: Thiếu username hoặc password."})
                            continue

                        accounts = load_accounts()
                        if user in accounts:
                            send_json(conn, {"type":"system", "content":"REGISTER_FAIL: Tên đăng nhập đã tồn tại."})
                        else:
                            accounts[user] = hash_password(pw)
                            save_accounts(accounts)
                            send_json(conn, {"type":"system", "content":"REGISTER_SUCCESS: Đăng ký thành công."})

                    elif mtype == "login":
                        content = msg.get("content", {})
                        user = content.get("username")
                        pw = content.get("password")

                        if not user or not pw:
                            send_json(conn, {"type":"system", "content":"LOGIN_FAIL: Thiếu username hoặc password."})
                            continue

                        accounts = load_accounts()
                        if user not in accounts:
                            send_json(conn, {"type":"system", "content":"LOGIN_FAIL: Tên đăng nhập không tồn tại."})
                        elif not check_password(accounts.get(user), pw):
                            send_json(conn, {"type":"system", "content":"LOGIN_FAIL: Sai mật khẩu."})
                        else:
                            # === ĐĂNG NHẬP THÀNH CÔNG ===
                            authenticated = True
                            nickname = user
                            
                            # Thêm vào danh sách client
                            with clients_lock:
                                clients[conn] = nickname
                            
                            print(f"{nickname} logged in from {addr}")
                            
                            # Gửi tin nhắn chào mừng (chỉ cho client này)
                            send_json(conn, {"type":"system", "content":"LOGIN_SUCCESS"})
                            
                            # Thông báo cho những người khác (thay thế cho 'join' cũ)
                            broadcast({"type":"system","content":f"{nickname} đã vào phòng."}, exclude_sock=conn)
                    
                    else:
                        # Gửi tin nhắn không phải login/register khi chưa đăng nhập
                        send_json(conn, {"type":"system", "content":"Bạn cần đăng nhập hoặc đăng ký trước."})
                
                # --- LOGIC ĐÃ XÁC THỰC (Giống code cũ của bạn) ---
                else:
                    if mtype == "msg":
                        text = msg.get("content", "")
                        frm = clients.get(conn, "Unknown") # Sẽ luôn lấy đúng nickname
                        print(f"[MSG] {frm}: {text}")
                        broadcast({"type":"msg","from":frm,"to":"all","content":text})
                    
                    elif mtype == "private":
                        to = msg.get("to")
                        text = msg.get("content","")
                        frm = clients.get(conn, "Unknown") # Sẽ luôn lấy đúng nickname
                        
                        recip = None
                        with clients_lock:
                            for s,n in clients.items():
                                if n == to:
                                    recip = s
                                    break
                        if recip:
                            send_json(recip, {"type":"private","from":frm,"to":to,"content":text})
                        else:
                            send_json(conn, {"type":"system","content":f"User {to} không tồn tại hoặc offline."})
                    
                    elif mtype == "join":
                        # Bỏ qua, vì "join" đã được xử lý lúc đăng nhập
                        pass
    
    except Exception as e:
        print(f"Client handler error ({nickname}): {e}")
    
    finally:
        # Khối finally này sẽ chạy dù client ngắt kết nối
        # hay có lỗi xảy ra. Nó sẽ dọn dẹp client.
        # Code này của bạn đã rất tốt, giữ nguyên.
        with clients_lock:
            if conn in clients:
                left_name = clients.pop(conn)
                broadcast({"type":"system","content":f"{left_name} đã rời."})
                print(f"{left_name} ({addr}) disconnected")
        conn.close()

# --- HÀM `start()` (Giữ nguyên) ---

def start():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"Server listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = srv.accept()
            # daemon=True để thread tự tắt khi chương trình chính tắt
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("Shutting down server.")
    finally:
        srv.close()

if __name__ == "__main__":
    start()