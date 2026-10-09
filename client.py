import socket

HOST = '127.0.0.1'
PORT = 5050


def recv_line(sock):
    buffer = b''
    while not buffer.endswith(b'\n'):
        chunk = sock.recv(1)
        if not chunk:
            break
        buffer += chunk
    return buffer.decode('utf-8').strip()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
        client_sock.connect((HOST, PORT))
        print(f'[CLIENT] Connected to {HOST}:{PORT}')
        print('Commands: ECHO <text> | TIME | QUIT')

        while True:
            message = input('Enter a command: ')
            if message == '':
                continue

            client_sock.sendall((message + '\n').encode('utf-8'))
            reply = recv_line(client_sock)
            print(f'[CLIENT] Server replied: {reply}')

            if message.split(' ', 1)[0].upper() == 'QUIT':
                break


if __name__ == '__main__':
    main()
