'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util

class Server:
    '''
    This is the main Server Class. You will  write Server code inside this class.
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.window = window
        self.clients = {}

    def send_message(self, type, format, data, clientaddress):
        '''
        This function makes a message, prepares it as a packet, and then sends it to the client using the client address
        type defines the type of message 
        format defines the format of the message (1, 2, 3, or 4)
        data is the actual message content
        '''
        message = util.make_message(type, format, data)
        packet = util.make_packet('data', 0, message)
        self.sock.sendto(packet.encode('utf-8'), clientaddress)
    
    def unknown_error(self, clientaddress):
        '''
        This function is used to handle unknown errors and send an error message to the client
        '''
        print("disconnected:", self.clients[clientaddress], "sent unknown command")
        self.clients.pop(clientaddress)
        self.send_message('err_unknown_message', 2, "")

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.

        '''
        while True:
            try:
                #Extracts the message type, length, data and server address from the received message
                message_type, message_length, message_data, client_address = util.handle_message(self.sock)
                #Checks if message_type is join and if the server is full or if the username is already taken it sends appropriate error messages, otherwise adds the client to the clients dictionary and prints a join message
                if message_type == 'join':
                    if len(self.clients) >= util.MAX_NUM_CLIENTS:
                        self.send_message('err_server_full', 2, "", client_address)
                        print('disconnected: server full')
                    elif message_data[0] in self.clients.values():
                        self.send_message('err_username_unavailable', 2, "", client_address)
                        print('disconnected: username not available')
                    else:
                        self.clients[client_address] = message_data[0]
                        print("join:", message_data[0])
                #Checks if message_type is request_users_list and sends the sorted list of users to the client
                elif message_type == 'request_users_list':
                    username = self.clients[client_address]
                    print("request_users_list: " + username)
                    userlist = list(self.clients.values())
                    userlist = sorted(userlist)
                    resp = ' '.join(userlist)
                    self.send_message('response_users_list', 3, resp, client_address)
                #Checks if message_type is send_message and if the message data is valid, it sends the message to the specified users, otherwise sends an unknown error message
                elif message_type == 'send_message':
                    print("msg: " + self.clients[client_address])
                    if len(message_data) < 2:
                        self.unknown_error(client_address)
                        continue
                    elif message_data[0] not in ['1', '2', '3', '4' ,'5' ,'6' ,'7' , '8', '9', '10']:
                        self.unknown_error(client_address)
                        continue
                    #Extracts the number of users to be messaged, the list of users and the message content
                    numusers = int(message_data[0])
                    help = numusers + 1
                    messageuserlist = message_data[1:help]
                    sentmessage = message_data[help:]
                    #Checks if the number of users in the message matches the number of users specified, otherwise sends an unknown error message
                    if len(messageuserlist) != numusers:
                        self.unknown_error(client_address)
                        continue
                    #Iterates through the list of users and sends the message to each user if they are in the clients dictionary, otherwise prints an error message
                    for user in messageuserlist:
                        if user in self.clients.values():
                            useraddress = next((addr for addr, name in self.clients.items() if name == user), None)
                            self.send_message('forward_message', 4, ' '.join([self.clients[client_address]] + sentmessage), useraddress)
                        else:
                            print("msg:", self.clients[client_address], "to non-existent user", user)
                #Checks if message_type is disconnect and removes the client from the clients dictionary and prints disconnect message, otherwise sends an unknown error message
                elif message_type == 'disconnect':
                    print('disconnected:', self.clients[client_address])
                    self.clients.pop(client_address)
                #If message_type is not recognized, it sends an unknown error message
                else:
                    self.unknown_error(client_address)
            #Handles any exceptions that may occur during message processing
            except Exception as e:
                print(f"Error in server: {e}")
                continue

# Do not change below part of code

if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=","window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
