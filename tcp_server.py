import socket
import threading
import struct
import datetime
from pathlib import Path
import portalocker

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / 'run_log.txt'

def log_event(role, event):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        f.write(f"{datetime.datetime.now().isoformat()} [{role}] {event}\n")
        f.flush()
        portalocker.unlock(f)

def recv_exact(conn, size):
    data = b''
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def handle_client(conn, addr):
    print(f"客户端 {addr} 已连接")
    log_event('SERVER', f"client connected {addr}")
    try:
        while True:
            header = recv_exact(conn, 8)
            if not header:
                break
            
            type_field, length = struct.unpack('!II', header)
            
            if type_field == 1:
                data = recv_exact(conn, length)
                if data is None:
                    break
                block_count = int.from_bytes(data, 'big')
                print(f"收到Initialization报文：数据块总数 = {block_count}")
                log_event('SERVER', f"recv INIT count={block_count} from {addr}")
                
                agree_header = struct.pack('!II', 2, 0)
                conn.sendall(agree_header)
                log_event('SERVER', f"send AGREE to {addr}")
                print("已发送agree报文")
                
            elif type_field == 3:
                data = recv_exact(conn, length)
                if data is None:
                    break
                log_event('SERVER', f"recv REQUEST len={len(data)} from {addr}")
                text = data.decode('utf-8')
                reverse_text = text[::-1]
                reverse_data = reverse_text.encode('utf-8')
                
                answer_header = struct.pack('!II', 4, len(reverse_data))
                conn.sendall(answer_header + reverse_data)
                log_event('SERVER', f"send ANSWER len={len(reverse_data)} to {addr}")
                
            else:
                print(f"收到未知类型报文: {type_field}")
                break
                
    except Exception as e:
        print(f"处理客户端 {addr} 时发生错误: {e}")
        log_event('SERVER', f"error for {addr}: {e}")
    finally:
        conn.close()
        print(f"客户端 {addr} 已断开连接")
        log_event('SERVER', f"client disconnected {addr}")

def main():
    host = '0.0.0.0'
    port = 12345
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    
    print(f"TCP服务端已启动，监听端口 {port}")
    
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    main()