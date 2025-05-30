# Distributed Mutual Exclusion with gRPC

This project implements two classical distributed mutual exclusion algorithms—**Lamport's Mutex Algorithm** and **Ricart-Agrawala Algorithm**—using Python, gRPC, and Protocol Buffers. Each node acts as a separate process and communicates with others to safely enter and exit a critical section (CS) without central coordination.

## Features

- Fully functional gRPC servers for each node
- Peer-to-peer communication via Protocol Buffers
- Logical clock synchronization
- Lamport queue-based ordering
- Ricart-Agrawala deferred reply mechanism
- Automatic startup of multiple nodes using a runner script

## Structure

- `mutual_exclusion.proto`: Defines gRPC services and messages
- `lamport_mutex.py`: Implements Lamport’s Mutex algorithm
- `ricart_agrawala.py`: Implements Ricart-Agrawala algorithm
- `run_all.py`: Launches multiple processes for testing

## Setup

1. Install dependencies:
   ```bash
   pip install grpcio grpcio-tools
2.  Compile the .proto file:
   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. mutual_exclusion.proto

python run_all.py
### How It Works
Each process maintains a logical clock and communicates with other nodes to coordinate access to the critical section. Lamport’s algorithm uses a priority queue (based on timestamps) to manage mutual exclusion, while Ricart-Agrawala uses direct permission requests and deferred replies.


Let me know if you want it tailored to a specific use case (e.g. only Ricart-Agrawala or a different run structure).
