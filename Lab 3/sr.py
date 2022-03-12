import copy
import config
import time
import threading
import udt
import util

# NOTE: 
# 1. Run the code with Python 3.
# 2. Please exit only the receiver code after the sender & receiver finish running!! Otherwise, the file won't complete writing.

# Questions
# 1. Why does sender need lock but receiver no need lock?
# 2. Why must sender_base and next_sequence_number start from 0?

class SelectiveRepeat:
    
    def __init__(self, local_port, remote_port, msg_handler):
        util.log("Starting up `Selective Repeat` protocol... ")
        
        self.network_layer = udt.NetworkLayer(local_port, remote_port, self)
        self.msg_handler = msg_handler
        
        self.sender_base = 0
        self.next_sequence_number = 0
        self.receiver_base = 0
        
        self.buffer = [None] * config.WINDOW_SIZE
        self.acked = []
        self.window = [b'']*config.WINDOW_SIZE
        self.timers = [None] * config.WINDOW_SIZE
        
        self.is_receiver = True
        self.sender_lock = threading.Lock()
    
    def send(self, msg):
        self.is_receiver = False
        if self.next_sequence_number < (self.sender_base + config.WINDOW_SIZE):
            self._send_helper(msg)
            return True
        else:
            util.log("Sender window is full. App data rejected")
            time.sleep(1)
            return False
        
    def _send_helper(self, msg):
        self.sender_lock.acquire()
        
        pkt = util.make_packet(msg, config.MSG_TYPE_DATA, self.next_sequence_number) # Create DATA packet
        pkt_data = util.extract_data(pkt)
        
        self.window[0 if self.next_sequence_number==0 else self.next_sequence_number%config.WINDOW_SIZE] = pkt # Required for retransmission
        util.log("Sending data: " + util.pkt_to_string(pkt_data))
        self.network_layer.send(pkt) # Send DATA packet

        pkt_num = copy.deepcopy(pkt_data.seq_num)
        self.set_timer(pkt_num)
        self.timers[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE].start()
        self.next_sequence_number += 1 
        self.sender_lock.release()
        return

    def set_timer(self, pkt_num):
        t = threading.Timer((config.TIMEOUT_MSEC/1000.0), self._timeout, args=[pkt_num])
        self.timers[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE] = t

        
    def handle_arrival_msg(self):        
        msg = self.network_layer.recv()
        msg_data = util.extract_data(msg)
        pkt_num = msg_data.seq_num
        
        if msg_data.is_corrupt:
            util.log("Received corrupted data. Is receiver: " + str(self.is_receiver))
            util.log("Corrupted packet will wait for timeout. Packet: " + str(pkt_num))
            return # Do nothing. Just wait for timeout.
                
        if msg_data.msg_type == config.MSG_TYPE_ACK: # Is sender            
            self.sender_lock.acquire()
            
            if self.timers[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE].is_alive():
                util.log("Received ACK: " + util.pkt_to_string(msg_data) + ". Stopping timer.")
                self.timers[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE].cancel() # Stop timer
            
            if (pkt_num >= self.sender_base and pkt_num <= self.sender_base + config.WINDOW_SIZE): # ACK Packet in sender window, [sender_base, sender_base + N]
                self.acked.append(pkt_num) # Add ACK-ed packet number
                
                if (self.sender_base == pkt_num): # Smallest un-ACKed packet                    
                    for acked in range(pkt_num, pkt_num + config.WINDOW_SIZE):
                        if acked in self.acked:
                            self.sender_base += 1 # Advance sender window
                        else:
                            break

            self.sender_lock.release()
            
        else: # Is receiver
            assert msg_data.msg_type == config.MSG_TYPE_DATA
            util.log("Received DATA: " + util.pkt_to_string(msg_data))
            
            if (pkt_num >= self.receiver_base) and (pkt_num <= self.receiver_base + config.WINDOW_SIZE - 1): # Packet in [receiver_base, receiver_base + N-1]
                self.buffer[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE] = msg_data
                
                ack_pkt = util.make_packet(b'', config.MSG_TYPE_ACK, pkt_num) # Create ACK packet
                self.network_layer.send(ack_pkt) # Send ACK packet
                util.log("Sent ACK: " + util.pkt_to_string(util.extract_data(ack_pkt)))
            
                if pkt_num == self.receiver_base: # In-order sequence
                    for i in range(0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE, config.WINDOW_SIZE):
                        if self.buffer[i] != None:
                            pkt = util.make_packet(msg, config.MSG_TYPE_DATA, pkt_num) # Create DATA packet
                            self.msg_handler(self.buffer[i].payload) # Deliver buffer
                            util.log("Delivered message. Message: " + str(self.buffer[i]))
                            self.buffer[i] = None # Clear buffer
                            self.receiver_base += 1 # Advance receiver window
                            util.log("Advanced window. Receiver base: " + str(self.receiver_base))
                            
                            if i == 9 and self.buffer[0] != None:
                                for j in range(0, config.WINDOW_SIZE):
                                    if self.buffer[j] != None:
                                        pkt = util.make_packet(msg, config.MSG_TYPE_DATA, pkt_num) # Create DATA packet
                                        self.msg_handler(self.buffer[j].payload) # Deliver buffer
                                        util.log("Delivered message. Message: " + str(self.buffer[j].payload))
                                        self.buffer[j] = None # Clear buffer
                                        self.receiver_base += 1 # Advance receiver window
                                        util.log("Advanced window. Receiver base: " + str(self.receiver_base))
                                        if self.receiver_base == 211: util.log(str(self.buffer))

                                    else:
                                        break # Reached the next "not-yet-received" packet
                            
                        else:
                            break # Reached the next "not-yet-received" packet

                
            if (pkt_num >= self.receiver_base - config.WINDOW_SIZE) and (pkt_num <= self.receiver_base - 1): # Packet in [receiver_base - N, receiver_base - 1]
                util.log("WARNING: Received old packet. Packet number: " + str(pkt_num))
                ack_pkt = util.make_packet(b'', config.MSG_TYPE_ACK, pkt_num) # Create ACK packet
                self.network_layer.send(ack_pkt) # Send ACK packet
                util.log("Sent ACK: " + util.pkt_to_string(util.extract_data(ack_pkt)))

    def shutdown(self):
        if not self.is_receiver: self._wait_for_last_ACK() # Sender wait for last ACK
        for i in range(config.WINDOW_SIZE):
            if self.timers[i].is_alive():
                self.timers[i].cancel()
        self.network_layer.shutdown()
        
    def _wait_for_last_ACK(self):
        while self.sender_base < self.next_sequence_number - 1:
            util.log("Waiting for last ACK from receiver with sequence # "
                     + str(int(self.next_sequence_number-1)) + ".")
            time.sleep(1)
        
    
    def _timeout(self, pkt_num):
        util.log("Timeout! Packet: " + str(pkt_num))
        self.sender_lock.acquire()
        if self.timers[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE].is_alive(): 
            self.timers[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE].cancel()
        self.set_timer(pkt_num)
        
        pkt = self.window[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE]
        self.network_layer.send(pkt) # Resend pkt
        util.log("Resending packet: " + util.pkt_to_string(util.extract_data(pkt)))
        self.timers[0 if pkt_num==0 else pkt_num%config.WINDOW_SIZE].start() # Restart timer
        self.sender_lock.release()
        return
        
        
        