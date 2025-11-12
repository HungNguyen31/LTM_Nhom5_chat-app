import socket, threading, json
import tkinter as tk
import tkinter.scrolledtext as st
from tkinter import messagebox  # MỚI: Cần cho popup lỗi

SERVER_PORT = 12345

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Desktop")
        self.sock = None
        self.buffer = ""
        self.nickname = None

        # --- MỚI: Khung Đăng nhập (Hiển thị ban đầu) ---
        self.login_frame = tk.Frame(root)
        
        # Hàng IP Server
        ip_frame = tk.Frame(self.login_frame)
        tk.Label(ip_frame, text="Server IP:").pack(side=tk.LEFT, padx=5, pady=5)
        self.ip_entry = tk.Entry(ip_frame, width=20)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(side=tk.LEFT)
        ip_frame.pack()

        # Hàng Username
        user_frame = tk.Frame(self.login_frame)
        tk.Label(user_frame, text="Username:").pack(side=tk.LEFT, padx=5, pady=5)
        self.user_entry = tk.Entry(user_frame, width=20)
        self.user_entry.pack(side=tk.LEFT)
        user_frame.pack()

        # Hàng Password
        pass_frame = tk.Frame(self.login_frame)
        tk.Label(pass_frame, text="Password:").pack(side=tk.LEFT, padx=5, pady=5)
        self.pass_entry = tk.Entry(pass_frame, width=20, show="*")
        self.pass_entry.pack(side=tk.LEFT)
        pass_frame.pack()

        # Hàng Nút Bấm
        btn_frame = tk.Frame(self.login_frame)
        tk.Button(btn_frame, text="Login", command=self.attempt_login).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Register", command=self.attempt_register).pack(side=tk.LEFT, padx=5)
        btn_frame.pack(pady=10)

        # Hàng Trạng thái
        self.login_status_label = tk.Label(self.login_frame, text="", fg="red")
        self.login_status_label.pack()

        # Hiển thị khung đăng nhập
        self.login_frame.pack(padx=10, pady=10)

        # --- MỚI: Khung Chat (Tạo ra nhưng bị ẩn) ---
        self.chat_frame = tk.Frame(root)
        
        self.text_area = st.ScrolledText(self.chat_frame, state='disabled', width=70, height=20)
        self.text_area.pack(padx=5, pady=5)

        bottom = tk.Frame(self.chat_frame)
        self.msg_entry = tk.Entry(bottom, width=50)
        self.msg_entry.pack(side=tk.LEFT, padx=(0,5))
        self.msg_entry.bind("<Return>", lambda e: self.send_msg())
        tk.Button(bottom, text="Send", command=self.send_msg).pack(side=tk.LEFT)
        bottom.pack(padx=5, pady=5)
        
        # chat_frame sẽ được .pack() sau khi đăng nhập thành công


    # --- MỚI: Hàm kết nối 1 lần ---
    def connect_to_server(self):
        """Chỉ kết nối socket và khởi động thread, không gửi 'join'"""
        if self.sock: # Đã kết nối rồi
            return True
            
        ip = self.ip_entry.get().strip()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, SERVER_PORT))
            
            # Khởi động thread nhận ngay lập tức
            threading.Thread(target=self.receive_loop, daemon=True).start()
            self.show_login_status("Đã kết nối, đang chờ xác thực...")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Không thể kết nối: {e}")
            self.sock = None # reset
            return False

    # --- MỚI: Hàm xử lý nút Login ---
    def attempt_login(self):
        user = self.user_entry.get().strip()
        pw = self.pass_entry.get().strip()
        if not user or not pw:
            messagebox.showerror("Lỗi", "Hãy nhập username và password")
            return
        
        # Kết nối nếu chưa
        if not self.connect_to_server():
            return
        
        # Gửi tin nhắn Login
        self.nickname = user # Tạm lưu nickname
        self.send_json({
            "type": "login",
            "from": None,
            "to": "server",
            "content": {"username": user, "password": pw}
        })

    # --- MỚI: Hàm xử lý nút Register ---
    def attempt_register(self):
        user = self.user_entry.get().strip()
        pw = self.pass_entry.get().strip()
        if not user or not pw:
            messagebox.showerror("Lỗi", "Hãy nhập username và password")
            return
        
        if not self.connect_to_server():
            return

        # Gửi tin nhắn Register
        self.send_json({
            "type": "register",
            "from": None,
            "to": "server",
            "content": {"username": user, "password": pw}
        })

    # --- MỚI: Các hàm helper cho UI ---
    def show_login_status(self, message):
        self.login_status_label.config(text=message, fg="red" if "FAIL" in message else "blue")

    def switch_to_chat_ui(self):
        """Ẩn đăng nhập, hiện chat."""
        self.login_frame.pack_forget() # Ẩn khung đăng nhập
        self.chat_frame.pack(padx=5, pady=5) # Hiển thị khung chat
        self.root.title(f"Chat - Đã đăng nhập: {self.nickname}") # Cập nhật tiêu đề cửa sổ

    # --- CÁC HÀM CŨ (gần như giữ nguyên) ---

    def send_json(self, obj):
        if not self.sock:
            messagebox.showerror("Lỗi", "Chưa kết nối tới server!")
            return
        try:
            data = json.dumps(obj, ensure_ascii=False) + '\n'
            self.sock.sendall(data.encode())
        except Exception as e:
            self.append_text(f"[Lỗi gửi] {e}\n")

    def send_msg(self):
        text = self.msg_entry.get().strip()
        if not text: return
        
        # Code send_msg của bạn rất tốt, giữ nguyên
        obj = {"type":"msg","from": self.nickname, "to":"all", "content": text}
        
        # Server mới của chúng ta thực ra không quan tâm "from" ở đây
        # nhưng gửi cũng không sao.
        
        self.send_json(obj)
        self.msg_entry.delete(0, tk.END)

    def append_text(self, text):
        # Hàm này của bạn đã dùng state='normal'/'disabled' rất chuẩn
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, text)
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def receive_loop(self):
        try:
            while True:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                self.buffer += data
                while '\n' in self.buffer:
                    line, self.buffer = self.buffer.split('\n', 1)
                    try:
                        msg = json.loads(line)
                    except:
                        continue
                    # Gửi tin nhắn đến hàm xử lý trên main thread
                    self.root.after(0, self.handle_message, msg)
        except Exception as e:
            self.root.after(0, self.append_text, f"\n[Mất kết nối] {e}\n")
        finally:
            if self.sock:
                self.sock.close()
                self.sock = None

    def handle_message(self, msg):
        mtype = msg.get("type")
        
        # --- MỚI: Cập nhật `handle_message` ---
        if mtype == "system":
            content = msg.get("content","")
            
            if content == "LOGIN_SUCCESS":
                self.switch_to_chat_ui() # <--- THAY ĐỔI QUAN TRỌNG
            elif content.startswith("LOGIN_FAIL") or content.startswith("REGISTER_FAIL"):
                self.show_login_status(content) # Hiển thị lỗi trên màn hình login
            elif content == "REGISTER_SUCCESS":
                self.show_login_status("Đăng ký thành công! Giờ hãy đăng nhập.")
            else:
                # Đây là các tin nhắn hệ thống khác (ví dụ: "abc đã vào phòng")
                self.append_text(f"[SYSTEM] {content}\n")
                
        elif mtype == "msg":
            frm = msg.get("from","")
            content = msg.get("content","")
            self.append_text(f"{frm}: {content}\n")
        elif mtype == "private":
            frm = msg.get("from","")
            content = msg.get("content","")
            self.append_text(f"[PVT]{frm}: {content}\n")
        else:
            self.append_text(f"[Unknown message] {msg}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()