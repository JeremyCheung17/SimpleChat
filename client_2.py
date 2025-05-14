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
import queue
import time
import math
import datetime

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
        self.window = window_size
        self.running = True
        self.message_queue = queue.Queue()
        self.next_ack = -1
        self.ack_gotten = -1
        self.packet_time = None

    def send_message(self, type, format, data):
        '''
        This function makes a message, prepares it as a packet, and then sends it to the server using the server address and port
        type defines the type of message (join, disconnect, etc.)
        format defines the format of the message (1, 2, 3, or 4)
        data is the actual message content
        '''
        message = util.make_message(type, format, data)
        self.send_reliable_message(message)

    def send_reliable_message(self, msg):
        '''
        This function splits the message into chunks and sends them with reliability
        '''
        # Generate a random sequence number for the start packet
        seq_num = random.randint(1, 1000000)
        start_seq_num = seq_num
        
        # Calculate number of chunks needed
        x_var = sys.getsizeof(msg)
        num_of_packets = math.ceil(x_var / util.CHUNK_SIZE)
        chunk_size = math.ceil(len(msg) / num_of_packets)
        
        # Split message into chunks
        chunks = [msg[i:i+chunk_size] for i in range(0, len(msg), chunk_size)]
        
        # Calculate last sequence number
        num_of_data_packets = len(chunks)
        last_seq_num = start_seq_num + num_of_data_packets + 2
        
        # Reset acknowledgment tracking
        self.ack_gotten = -1
        self.next_ack = -1
        
        # Send START packet and wait for acknowledgment
        start_packet = util.make_packet('start', seq_num)
        self.sock.sendto(start_packet.encode('utf-8'), (self.server_addr, self.server_port))
        self.packet_time = datetime.datetime.now()
        
        # Keep retransmitting START until ACK received
        self.start_end_transmission(start_seq_num+1, start_packet)
        # Update ack tracking
        self.ack_gotten = self.next_ack
        self.next_ack = -1
        
        # Send all data chunks with reliability
        self.data_transmission(last_seq_num, start_seq_num, chunks)
        
        # Send END packet and wait for acknowledgment
        end_packet = util.make_packet("end", last_seq_num - 1)
        self.sock.sendto(end_packet.encode('utf-8'), (self.server_addr, self.server_port))
        self.packet_time = datetime.datetime.now()
        
        # Keep retransmitting END until ACK received
        self.start_end_transmission(last_seq_num, end_packet)
        # Reset acknowledgment state
        self.next_ack = -1
        self.ack_gotten = -1
    

    def start_end_transmission(self, seq_num, msg_packet):
        '''
        Handles reliable transmission of START/END packet with retransmission
        '''
        while True:
            if self.next_ack == seq_num:
                break

            if ((datetime.datetime.now() - self.packet_time) > datetime.timedelta(seconds=0.5)):
                self.sock.sendto(msg_packet.encode('utf-8'), (self.server_addr, self.server_port))
                self.packet_time = datetime.datetime.now()
    
    def data_transmission(self, last_seq_num, start_seq_num, chunks):
       while self.ack_gotten != last_seq_num - 1:
            i = self.ack_gotten - start_seq_num - 1
            packet = util.make_packet("data", self.ack_gotten, chunks[i])
            self.sock.sendto(packet.encode('utf-8'), (self.server_addr, self.server_port))
            self.packet_time = datetime.datetime.now()
            self.data_retransmission()
    
    def data_retransmission(self):
        '''
        Handles retransmission of data packets if ACK not received in time
        '''
        while not ((datetime.datetime.now() - self.packet_time) > datetime.timedelta(seconds=0.5)):
            if self.next_ack == self.ack_gotten + 1:
                self.ack_gotten = self.ack_gotten + 1
                self.next_ack = -1
                break

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
                # Waits for user input and extracts it into a list of words
                msg = input()
                if not msg.strip(): 
                    continue
                message = msg.split()
                # Checks if user input is list. If there is more than one word, it sends an error message, otherwise sends server a request for the user list
                if message[0] == 'list':
                    if len(message) > 1:
                        self.send_message('err', 2, "")
                        continue
                    self.send_message('request_users_list', 2, "")
                # Checks if user input is quit. If there is more than one word, it sends an error message, otherwise sends server a disconnect message and quits
                elif message[0] == 'quit':
                    if len(message) > 1:
                        self.send_message('err', 2, "")
                        continue
                    print("quitting")
                    self.send_message('disconnect', 1, self.name)
                    self.quit_server()
                    break
                # Checks if user input is msg and sends the content to the server
                elif message[0] == 'msg':
                    self.send_message('send_message', 4, msg[4:])
                # Checks if user input is help. If there is more than one word, it sends an error message, otherwise prints list of possible commands and their formatting
                elif message[0] == 'help':
                    if len(message) > 1:
                        self.send_message('err', 2, "")
                        continue
                    print("Input for sending message (... to represent possibility for multiple users): msg <num of users to be messaged> <user1> <user2> ... <message>")
                    print("Input for accesing client list: list")
                    print("Input for viewing all user-inputs and their format input: help")
                    print("Input for disconnecting from server: quit")
                # If the input is not recognized, it prints an error message
                else:
                    print("incorrect userinput format")
            # Handles any exceptions that may occur during user input processing
            except Exception as e:
                if not self.running:
                    break
                print(f"Error in client: {e}")
                continue
    
    def packet_receiver(self, message, client_addr):
        '''
        Manages different types of packets received from the server
        '''
        msg_type, seq_num, recv_msg, _ = util.parse_packet(message.decode('utf-8'))
        seq_num = int(seq_num)
        
        if msg_type == 'ack':
            self.next_ack = seq_num
            return " "
        
        # For data packets, we should send an ACK
        if msg_type in ['start', 'data', 'end']:
            # Send the ACK
            msg = util.make_message('ack', 2,)
            msg = util.make_packet('ack', int(seq_num + 1), msg)
            self.sock.sendto(msg.encode("utf-8"), client_addr)  
            # If it's a data packet, return the message content
            if msg_type == 'data':
                return recv_msg
                
        return " "

    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        while self.running:
            try:
                # Receive message from server
                message, server_address = self.sock.recvfrom(4096)
                
                # Process the message based on its type
                recv_msg = self.packet_receiver(message, server_address)
                
                if recv_msg != " ":
                    # Split the message to get its type and content
                    parts = recv_msg.split()
                    if len(parts) < 1:
                        continue
                        
                    message_type = parts[0]
                    
                    # Process message based on its type
                    if message_type == 'response_users_list':
                        users = ' '.join(parts[2:])
                        print("list:", users)
                    elif message_type == 'forward_message':
                        sender = parts[2]
                        message_content = ' '.join(parts[3:])
                        print(f"msg: {sender}: {message_content}")
                    elif message_type == 'err_server_full':
                        print('disconnected: server full')
                        self.quit_server()
                        break
                    elif message_type == 'err_username_unavailable':
                        print('disconnected: username not available')
                        self.quit_server()
                        break
                    elif message_type == 'err_unknown_message':
                        print('disconnected: server received an unknown command')
                        self.quit_server()
                        break
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