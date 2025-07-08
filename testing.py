import socket

s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, 25, b"utun4\0")  # Bind to interface (Linux/macOS)
s.connect(('2606:4700:4700::1111', 53))
print("Source IP used:", s.getsockname()[0])