'''
This file contains basic utility functions that you can use and can also make your helper functions here
'''
import binascii

MAX_NUM_CLIENTS = 10
TIME_OUT = 0.5 # 500ms
CHUNK_SIZE = 1400 # 1400 Bytes

def validate_checksum(message):
    '''
    Validates Checksum of a message and returns true/false
    '''
    try:
        msg, checksum = message.rsplit('|', 1)
        msg += '|'
        return generate_checksum(msg.encode()) == checksum
    except BaseException:
        return False


def generate_checksum(message):
    '''
    Returns Checksum of the given message
    '''
    return str(binascii.crc32(message) & 0xffffffff)


def make_packet(msg_type="data", seqno=0, msg=""):
    '''
    This will add the header to your message.
    The formats is `<message_type> <sequence_number> <body> <checksum>`
    msg_type can be data, ack, end, start
    seqno is a packet sequence number (integer)
    msg is the actual message string
    '''
    body = "%s|%d|%s|" % (msg_type, seqno, msg)
    checksum = generate_checksum(body.encode())
    packet = "%s%s" % (body, checksum)
    return packet


def parse_packet(message):
    '''
    This function will parse the packet in the same way it was made in the above function.
    '''
    pieces = message.split('|')
    msg_type, seqno = pieces[0:2]
    checksum = pieces[-1]
    data = '|'.join(pieces[2:-1])
    return msg_type, seqno, data, checksum


def make_message(msg_type, msg_format, message=None):
    '''
    This function can be used to format your message according
    to any one of the formats described in the documentation.
    msg_type defines type like join, disconnect etc.
    msg_format is either 1,2,3 or 4
    msg is remaining. 
    '''
    if msg_format == 2:
        msg_len = 0
        return "%s %d" % (msg_type, msg_len)
    if msg_format in [1, 3, 4]:
        msg_len = len(message)
        return "%s %d %s" % (msg_type, msg_len, message)
    return ""

def handle_message(sock):
        '''
        This function can be used to extract the message_type, format, and data from an incoming message from the socket
        It will also return the address of the server that sent the message
        message_type defines the type like join, disconnect etc.
        length is the length of the message
        data is everything after the length
        '''
        message, serveraddress = sock.recvfrom(4096)
        decoded_message = message.decode("utf-8")
        msg_type, seq_num, recv_msg, check_sum = parse_packet(decoded_message)
        message_type = ''
        message_length = ''
        message_data = ''
        if recv_msg:
            parts = recv_msg.split()
            if len(parts) >= 1:
                message_type = parts[0]
            if len(parts) >= 2:
                message_length = parts[1]
            if len(parts) >= 3:
                message_data = parts[2:]
        return message_type, message_length, message_data, serveraddress
