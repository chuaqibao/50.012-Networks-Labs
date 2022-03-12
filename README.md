# 50.012-Networks-Labs

Done in 2021

### Lab 1: Simple Web Proxy Server 

Perform caching of web pages using web proxy.

<img width="629" alt="Screenshot 2022-03-12 at 3 49 48 PM" src="https://user-images.githubusercontent.com/62118373/158009188-e06c86e0-9bb7-4b1b-a37f-e650014b56b5.png">

### Lab 2: REST API using FastAPI

Build REST over HTTP API using FastAPI and Redis database that performs GET, POST, DELETE/PUT requests, perform authorization through inspecting request headers and can do batch delete.

### Lab 3: Implement a Reliable Data Transfer Protocol

Implement Selective Repeat protocol to achieve reliable data transfer. Selective Repeat protocol avoids unnecessary retransmission as the sender retransmit only packets that are suspected to be lost or received errors at the received. The main events include 
1. Data received at sender
2. Timeouts to detect lost packets
3. ACK received by sender
4. Packet with sequence number is correctly received at receiver

### Lab 4: TCP Congestion Control
* Understand TCP's control mechanism
* Learn to use mininet tool and get familiar with network emulation
* Understand why large buffers are disadvantageous
