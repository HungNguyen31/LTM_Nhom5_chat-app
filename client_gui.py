# client_gui.py
import socket, threading, json, tkinter as tk, tkinter.scrolledtext as st, tkinter.simpledialog as sd

SERVER_PORT = 12345

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Desktop")
        self.sock = None
        self.buffer = ""
        self.nickname = None

        # UI
        top = tk.Frame(root)
        tk.Label(top, text="Server IP:").pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(top)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(side=tk.LEFT)
        tk.Label(top, text="Nick:").pack(side=tk.LEFT, padx=(10,0))
        self.nick_entry = tk.Entry(top)
        self.nick_entry.pack(side=tk.LEFT)
        tk.Button(top, text="Connect", command=self.connect).pack(side=tk.LEFT, padx=5)
        top.pack(padx=5, pady=5)

        self.text_area = st.ScrolledText(root, state='disabled', width=70, height=20)
        self.text_area.pack(padx=5, pady=5)

        bottom = tk.Frame(root)
        self.msg_entry = tk.Entry(bottom, width=50)
        self.msg_entry.pack(side=tk.LEFT, padx=(0,5))
        self.msg_entry.bind("<Return>", lambda e: self.send_msg())
        tk.Button(bottom, text="Send", command=self.send_msg).pack(side=tk.LEFT)
        bottom.pack(padx=5, pady=5)

    def connect(self):
        ip = self.ip_entry.get().strip()
        nick = self.nick_entry.get().strip()
        if not nick:
            tk.messagebox.showerror("Error", "Hãy nhập nickname")
            return
        self.nickname = nick
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, SERVER_PORT))
        except Exception as e:
            tk.messagebox.showerror("Error", f"Không kết nối: {e}")
            return
        # send join
        self.send_json({"type":"join","from":self.nickname})
        threading.Thread(target=self.receive_loop, daemon=True).start()
        self.append_text("Kết nối thành công!\n")

    def send_json(self, obj):
        try:
            data = json.dumps(obj, ensure_ascii=False) + '\n'
            self.sock.sendall(data.encode())
        except Exception as e:
            self.append_text(f"[Lỗi gửi] {e}\n")

    def send_msg(self):
        text = self.msg_entry.get().strip()
        if not text: return
        obj = {"type":"msg","from": self.nickname, "to":"all", "content": text}
        self.send_json(obj)
        self.msg_entry.delete(0, tk.END)

    def append_text(self, text):
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
                    self.handle_message(msg)
        except Exception as e:
            self.append_text(f"\n[Connection closed] {e}\n")
        finally:
            try:
                self.sock.close()
            except:
                pass

    def handle_message(self, msg):
        mtype = msg.get("type")
        if mtype == "system":
            content = msg.get("content","")
            self.root.after(0, self.append_text, f"[SYSTEM] {content}\n")
        elif mtype == "msg":
            frm = msg.get("from","")
            content = msg.get("content","")
            self.root.after(0, self.append_text, f"{frm}: {content}\n")
        elif mtype == "private":
            frm = msg.get("from","")
            content = msg.get("content","")
            self.root.after(0, self.append_text, f"[PVT]{frm}: {content}\n")
        else:
            self.root.after(0, self.append_text, f"[Unknown message] {msg}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()
