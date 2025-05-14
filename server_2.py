'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
import queue
import threading
import random
import time
import datetime
import math

class Server:
    '''
    This is the main Server Class. You will write Server code inside this class.
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
        self.client_messages = {}
        self.ack_num_next = {}
        self.expected_seq = {}
        self.ack_gotten = {}
        self.packet_times = {}

    def send_message(self, type, format, data, clientaddress):
        '''
        This function makes a message, prepares it as a packet, and then sends it to the client using the client address
        type defines the type of message 
        format defines the format of the message (1, 2, 3, or 4)
        data is the actual message content
        '''
        message = util.make_message(type, format, data)
        self.make_thread(message, clientaddress)
    
    def make_thread(self, msg, client_address):
        '''
        Create a thread to handle message chunking and sending
        '''
        T = threading.Thread(target=self.send_reliable_message, args=(msg, client_address))
        T.daemon = True
        T.start()
    
    def send_reliable_message(self, msg, client_address):
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
        
        # Reset acknowledgment tracking for this client
        self.ack_gotten[client_address] = -1
        self.ack_num_next[client_address] = -1
        
        # Send START packet and wait for acknowledgment
        start_packet = util.make_packet('start', seq_num)
        self.sock.sendto(start_packet.encode('utf-8'), client_address)
        self.packet_times[client_address] = datetime.datetime.now()
        
        # Keep retransmitting START until ACK received
        self.start_end_transmission(client_address, start_seq_num + 1, start_packet)
        # Update ack tracking
        self.ack_gotten[client_address] = self.ack_num_next[client_address]
        self.ack_num_next[client_address] = -1
        
        # Send all data chunks with reliability
        self.data_transmission(client_address, last_seq_num, start_seq_num, chunks)
        
        # Send END packet and wait for acknowledgment
        end_packet = util.make_packet("end", last_seq_num - 1)
        self.sock.sendto(end_packet.encode('utf-8'), client_address)
        self.packet_times[client_address] = datetime.datetime.now()
        
        # Keep retransmitting END until ACK received
        self.start_end_transmission(client_address, last_seq_num, end_packet)
        # Reset acknowledgment state
        self.ack_num_next[client_address] = -1
        self.ack_gotten[client_address] = -1
    
    def start_end_transmission(self, client_address, seq, msg_packet):
        '''
        Handles reliable transmission of START/END packet with retransmission
        '''
        ack_control = False
        while True:
            if self.ack_num_next.get(client_address) == seq:
                break

            if ack_control:
                ack_control = False

            if (datetime.datetime.now() - self.packet_times.get(client_address)) > datetime.timedelta(seconds=0.5):
                ack_control = True
                self.sock.sendto(msg_packet.encode('utf-8'), client_address)
                self.packet_times[client_address] = datetime.datetime.now()

    def data_transmission(self, client_address, last_seq_num, start_seq_num, chunks):
        '''
        Handles reliable transmission of DATA packets with retransmission
        '''
        while self.ack_gotten[client_address] != last_seq_num - 1:
            i = self.ack_gotten[client_address] - start_seq_num - 1
            packet = util.make_packet("data", self.ack_gotten[client_address], chunks[i])
            self.sock.sendto(packet.encode('utf-8'), client_address)
            self.packet_times[client_address] = datetime.datetime.now()
            self.data_retransmission(client_address)
    
    def data_retransmission(self, client_address):
        '''
        Handles retransmission of data packets if ACK not received in time
        '''
        while not (datetime.datetime.now() - self.packet_times.get(client_address)) > datetime.timedelta(seconds=0.5):
            if self.ack_num_next.get(client_address) == self.ack_gotten[client_address] + 1:
                self.ack_gotten[client_address] = self.ack_gotten[client_address] + 1
                self.ack_num_next[client_address] = -1
                break
    
    def client_handler(self, message_packet, client_addr):
        '''
        Handle incoming packets from clients
        '''
        # Decode the packet and extract info
        message_decoded = message_packet.decode('utf-8')
        msg_type, seq_num, recv_msg, _ = util.parse_packet(message_decoded)
        seq_num = int(seq_num)
        end_recv = False
        recv_msg_result = " "
        
        # Handle different packet types
        if msg_type == 'ack':
            # Update next expected sequence number
            self.ack_num_next[client_addr] = seq_num
            
        elif msg_type == 'start':
            # Initialize a new message reception
            if client_addr not in self.client_messages:
                self.client_messages[client_addr] = queue.Queue()
            msg_queue = queue.Queue()
            self.client_messages[client_addr] = msg_queue
            # Set next expected sequence number
            self.expected_seq[client_addr] = seq_num + 1
            seq_num_send = self.expected_seq[client_addr]
            # Send acknowledgment
            msg = util.make_message('ack', 2,)
            msg = util.make_packet('ack', int(seq_num_send), msg)
            self.sock.sendto(msg.encode("utf-8"), client_addr)   
            
        elif msg_type == 'data':
            # Check if sequence number matches expected
            if client_addr in self.expected_seq and self.expected_seq[client_addr] == seq_num:
                # Add to message queue
                self.client_messages[client_addr].put(message_packet)
                # Update next expected sequence number
                self.expected_seq[client_addr] = seq_num + 1
            # Send acknowledgment for the received packet
            msg = util.make_message('ack', 2,)
            msg = util.make_packet('ack', int(self.expected_seq.get(client_addr, seq_num + 1)), msg)
            self.sock.sendto(msg.encode("utf-8"), client_addr)
            
        elif msg_type == 'end':
            # Process the complete message if all packets received
            if client_addr in self.expected_seq and self.expected_seq[client_addr] == seq_num:
                # Combine all received message chunks
                recv_msg_result = ''
                while not self.client_messages[client_addr].empty():
                    msg_type, _, str_msg, _ = util.parse_packet(self.client_messages[client_addr].get().decode('utf-8'))
                    recv_msg_result += str_msg
                
                # Send acknowledgment for END packet
                seq_num_next = self.expected_seq[client_addr] + 1
                msg = util.make_message('ack', 2,)
                msg = util.make_packet('ack', int(seq_num_next), msg)
                self.sock.sendto(msg.encode("utf-8"), client_addr) 
                
                # Clean up client state
                if client_addr in self.expected_seq:
                    del self.expected_seq[client_addr]
                
                end_recv = True
            else:
                # Send acknowledgment for the current expected sequence
                msg = util.make_message('ack', 2,)
                msg = util.make_packet('ack', int(self.expected_seq.get(client_addr, seq_num)), msg)
                self.sock.sendto(msg.encode("utf-8"), client_addr) 
        if end_recv:
            return recv_msg_result
        else:
            return " "
    
    def unknown_error(self, clientaddress):
        '''
        This function is used to handle unknown errors and send an error message to the client
        '''
        print("disconnected:", self.clients[clientaddress], "sent unknown command")
        self.clients.pop(clientaddress)
        self.send_message('err_unknown_message', 2, "", clientaddress)

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.
        '''
        while True:
            try:
                # Receive message from client
                message, client_address = self.sock.recvfrom(4096)
                
                # Process the message
                recv_msg = self.client_handler(message, client_address)
                
                if recv_msg != " ":
                    # Split the message to get its type and content
                    message_parts = recv_msg.split()
                    if len(message_parts) < 1:
                        continue
                        
                    message_type = message_parts[0]
                    
                    # Process message based on its type
                    if message_type == 'join':
                        # Check if server is full
                        if len(self.clients) >= util.MAX_NUM_CLIENTS:
                            self.send_message('err_server_full', 2, "", client_address)
                            print('disconnected: server full')
                        # Check if username is already taken
                        elif message_parts[2] in self.clients.values():
                            self.send_message('err_username_unavailable', 2, "", client_address)
                            print('disconnected: username not available')
                        else:
                            # Add client to the list of connected clients
                            self.clients[client_address] = message_parts[2]
                            print("join:", message_parts[2])
                            
                    elif message_type == 'request_users_list':
                        # Send list of connected users
                        username = self.clients[client_address]
                        print("request_users_list:", username)
                        userlist = list(self.clients.values())
                        userlist = sorted(userlist)
                        resp = ' '.join(userlist)
                        self.send_message('response_users_list', 3, resp, client_address)
                        
                    elif message_type == 'send_message':
                        # Forward message to specified clients
                        print("msg:", self.clients[client_address])
                        
                        # Check if message format is valid
                        if len(message_parts) < 2:
                            self.unknown_error(client_address)
                            continue
                        elif message_parts[2] not in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                            self.unknown_error(client_address)
                            continue
                            
                        # Extract message details
                        num_users = int(message_parts[2])
                        user_end_index = 3 + num_users
                        
                        # Check if number of users matches
                        if len(message_parts) < user_end_index:
                            self.unknown_error(client_address)
                            continue
                            
                        user_list = message_parts[3:user_end_index]
                        message_content = ' '.join(message_parts[user_end_index:])
                        
                        # Send message to each specified user
                        for user in user_list:
                            if user in self.clients.values():
                                # Get user's address
                                user_address = next((addr for addr, name in self.clients.items() if name == user), None)
                                self.send_message('forward_message', 4, ' '.join([self.clients[client_address], message_content]), user_address)
                            else:
                                print("msg:", self.clients[client_address], "to non-existent user", user)
                                
                    elif message_type == 'disconnect':
                        # Remove client from the list of connected clients
                        print('disconnected:', self.clients[client_address])
                        self.clients.pop(client_address)
                        
                    else:
                        # Handle unknown message type
                        self.unknown_error(client_address)
                        
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
            