'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util


'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen 
for incoming messages in this function.
'''

class Client:
    '''
    This is the main Client Class. 
    '''

    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.running = True

    def send_message(self, type, format, data):
        '''
        This function makes a message, prepares it as a packet, and then sends it to the server using the server address and port
        type defines the type of message (join, disconnect, etc.)
        format defines the format of the message (1, 2, 3, or 4)
        data is the actual message content
        '''
        message = util.make_message(type, format, data)
        packet = util.make_packet('data', 0, message)
        self.sock.sendto(packet.encode('utf-8'), (self.server_addr, self.server_port))

    def quit_server(self):
        '''
        This function is used to quit the server and close the socket, while setting the running flag to False in order to stop the main loop
        '''
        self.running = False
        self.sock.close()
        sys.exit()

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message. 
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it
        '''
        self.send_message('join', 1, self.name)
        while self.running:
            try:
                #Waits for user input and extracts it into a list of words
                msg = input()
                if not msg.strip(): 
                    continue
                message = msg.split()
                #Checks if user input is list. If there is more than one word, it sends an error message, otherwise sends server a request for the user list
                if message[0] == 'list':
                    if len(message) > 1:
                        self.send_message('err', 2, "")
                        continue
                    self.send_message('request_users_list', 2, "")
                #Checks if user input is quit. If there is more than one word, it sends an error message, otherwise sends server a disconnect message and quits
                elif message[0] == 'quit':
                    if len(message) > 1:
                        self.send_message('err', 2, "")
                        continue
                    print("quitting")
                    self.send_message('disconnect', 1, self.name)
                    self.quit_server()
                    break
                #Checks if user input is msg and sends the content to the server
                elif message[0] == 'msg':
                    self.send_message('send_message', 4, msg[4:])
                #Checks if user input is help. If there is more than one word, it sends an error message, otherwise prints list of possible commands and their formatting
                elif message[0] == 'help':
                    if len(message) > 1:
                        self.send_message('err', 2, "")
                        continue
                    print("Input for sending message (... to represent possibility for multiple users): msg <num of users to be messaged> <user1> <user2> ... <message>")
                    print("Input for accesing client list: list")
                    print("Input for viewing all user-inputs and their format input: help")
                    print("Input for disconnecting from server: quit")
                #If the input is not recognized, it prints an error message
                else:
                    print("incorrect userinput format")
            #Handles any exceptions that may occur during user input processing
            except Exception as e:
                if not self.running:
                    break
                print(f"Error in client: {e}")
                continue
            

    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        while self.running:
            try:
                #Extracts the message type, length, data and server address from the received message
                message_type, message_length, message_data, server_address = util.handle_message(self.sock)
                #Checks if message type is response_users_list. If so, turns the data into a string seperated by spaces and prints it
                if message_type == 'response_users_list':
                    users= ' '.join(message_data)
                    print("list:", users)
                #Checks if message type is forward_message. If so, it extracts the sender (first word of data) and message (rest of data turned into a string seperated by spaces) from the data and prints it
                elif message_type == 'forward_message':
                    sender = message_data[0]
                    message = ' '.join(message_data[1:])
                    print(f"msg: {sender}: {message}")
                #Checks if message type is err_server_full. If so, it prints an error message and quits the server
                elif message_type == 'err_server_full':
                    print('disconnected: server full')
                    self.quit_server()
                    break
                #Checks if message type is err_username_unavailable. If so, it prints an error message and quits the server
                elif message_type == 'err_username_unavailable':
                    print('disconnected: username not available')
                    self.quit_server()
                    break
                #Checks if message type is err_unknown_message. If so, it prints an error message and quits the server
                elif message_type == 'err_unknown_message':
                    print('disconnected: server received an unknown command')
                    self.quit_server()
                    break
            #Handles any exceptions that may occur during message processing
            except Exception as e:
                if not self.running:
                    break
                print(f"Error in client receiving: {e}")
                continue
            



# Do not change below part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=","window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
