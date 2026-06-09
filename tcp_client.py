import socket
import struct
import sys
import datetime
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / 'run_log_tcp_client.txt'

def log_event(role, event):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now().isoformat()} [{role}] {event}\n")

def recv_exact(sock, size):
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def main():
    if len(sys.argv) not in (5, 6):
        print("Usage: python tcp_client.py <server_ip> <server_port> <Lmin> <Lmax> [seed]")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    try:
        Lmin = int(sys.argv[3])
        Lmax = int(sys.argv[4])
    except ValueError:
        print("Lmin and Lmax must be integers")
        sys.exit(1)
    if Lmin <= 0 or Lmax < Lmin:
        print("Invalid Lmin/Lmax: require 0 < Lmin <= Lmax")
        sys.exit(1)
    seed = int(sys.argv[5]) if len(sys.argv) == 6 else None
    if seed is not None:
        random.seed(seed)
    
    file_path = 'test.txt'
    try:
        with open(file_path, 'r', encoding='ascii') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在")
        sys.exit(1)
    
    total_len = len(content)
    chunk_lengths = []
    remain = total_len
    while remain > Lmax:
        length = random.randint(Lmin, Lmax)
        chunk_lengths.append(length)
        remain -= length
    if remain > 0:
        chunk_lengths.append(remain)
    
    blocks = []
    offset = 0
    for length in chunk_lengths:
        blocks.append(content[offset:offset+length])
        offset += length
    
    print(f"Lmin={Lmin}, Lmax={Lmax}, seed={seed}, chunks={len(blocks)}")
    print(f"chunk lengths: {chunk_lengths}")
    
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(10)
    client.connect((server_ip, server_port))
    
    init_data = len(blocks).to_bytes(4, 'big')
    init_header = struct.pack('!II', 1, len(init_data))
    client.sendall(init_header + init_data)
    log_event('CLIENT', f"send INIT count={len(blocks)} Lmin={Lmin} Lmax={Lmax} seed={seed} lengths={chunk_lengths}")
    print(f"已发送Initialization报文：数据块总数 = {len(blocks)}")
    
    agree_header = client.recv(8)
    if agree_header:
        type_field, length = struct.unpack('!II', agree_header)
        if type_field == 2:
            log_event('CLIENT', 'recv AGREE')
            print("收到agree报文")
    
    reversed_blocks = []
    for idx, block in enumerate(blocks):
        block_data = block.encode('ascii')
        request_header = struct.pack('!II', 3, len(block_data))
        client.sendall(request_header + block_data)
        log_event('CLIENT', f"send REQUEST idx={idx} len={len(block_data)}")
        
        answer_header = recv_exact(client, 8)
        if not answer_header:
            print("服务器关闭连接")
            break
        type_field, length = struct.unpack('!II', answer_header)
        reversed_data = recv_exact(client, length)
        if reversed_data is None:
            print("接收数据失败")
            break
        text = reversed_data.decode('ascii')
        reversed_blocks.append(text)
        log_event('CLIENT', f"recv ANSWER idx={idx} len={len(reversed_data)}")
        print(f"第{idx+1}块：{text}")
    
    # 将服务端返回的反转结果按顺序拼接，生成完整反转文件
    output_content = ''.join(reversed_blocks)
    output_path = SCRIPT_DIR / 'reversed_output.txt'
    with open(output_path, 'w', encoding='ascii') as f:
        f.write(output_content)
    print(f"已生成完整反转文件：{output_path}")
    log_event('CLIENT', f"write reversed file {output_path.name} len={len(output_content)}")
    
    log_event('CLIENT', 'close connection')
    client.close()
    print("传输完成")

if __name__ == "__main__":
    main()