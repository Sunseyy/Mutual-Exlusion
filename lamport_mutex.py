import argparse
import threading
import time
import heapq
import grpc
from concurrent import futures
from colorama import init, Fore, Style

import mutual_exclusion_pb2 as pb
import mutual_exclusion_pb2_grpc as rpc

init(autoreset=True)

class LamportServer(rpc.MutexServicer):
    def __init__(self, pid):
        self.pid = pid
        self.clock = 0
        self.queue = []  # min-heap of (timestamp, pid)
        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)

    def Request(self, req, ctx):
        with self.lock:
            old_clock = self.clock
            self.clock = max(self.clock, req.timestamp) + 1
            heapq.heappush(self.queue, (req.timestamp, req.pid))
            print(Fore.MAGENTA + f"[Lamport][P{self.pid}] Received REQUEST from P{req.pid} with timestamp {req.timestamp} | Clock updated {old_clock} -> {self.clock}" + Style.RESET_ALL)
        # reply immediately
        return pb.ReplyMsg(timestamp=self.clock, pid=self.pid)

    def Release(self, req, ctx):
        with self.lock:
            old_queue = self.queue.copy()
            self.queue = [(t, p) for t, p in self.queue if p != req.pid]
            heapq.heapify(self.queue)
            print(Fore.BLUE + f"[Lamport][P{self.pid}] Received RELEASE from P{req.pid} | Queue before: {old_queue} | Queue after: {self.queue}" + Style.RESET_ALL)
            self.cv.notify_all()
        return pb.Empty()

    def start(self, port):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        rpc.add_MutexServicer_to_server(self, server)
        server.add_insecure_port(f"[::]:{port}")
        server.start()
        print(Fore.CYAN + f"[Lamport][P{self.pid}] gRPC server started on port {port}" + Style.RESET_ALL, flush=True)
        return server


class LamportProcess:
    def __init__(self, pid, port, peers):
        self.server = LamportServer(pid)
        self.grpc_server = self.server.start(port)
        self.peers = peers  # dict pid->"host:port"
        time.sleep(1)       # wait for servers to start
        print(Fore.CYAN + f"[Lamport][P{self.server.pid}] Ready with peers: {self.peers}" + Style.RESET_ALL)

    def enter_critical(self):
        with self.server.lock:
            self.server.clock += 1
            timestamp = self.server.clock
            heapq.heappush(self.server.queue, (timestamp, self.server.pid))
            print(Fore.YELLOW + f"[Lamport][P{self.server.pid}] Added own request to queue with timestamp {timestamp} | Queue: {self.server.queue}" + Style.RESET_ALL)

        # send Request to all peers
        for peer_pid, addr in self.peers.items():
            if peer_pid == self.server.pid:
                continue
            stub = rpc.MutexStub(grpc.insecure_channel(addr))
            try:
                print(Fore.MAGENTA + f"[Lamport][P{self.server.pid}] Sending REQUEST to P{peer_pid}" + Style.RESET_ALL)
                reply = stub.Request(pb.RequestMsg(timestamp=timestamp, pid=self.server.pid))
                print(Fore.MAGENTA + f"[Lamport][P{self.server.pid}] Received REPLY from P{peer_pid} with timestamp {reply.timestamp}" + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"[Lamport][P{self.server.pid}] Error requesting peer P{peer_pid}: {e}" + Style.RESET_ALL)

        # wait until this process is at the head of the queue
        with self.server.cv:
            print(Fore.YELLOW + f"[Lamport][P{self.server.pid}] Waiting to enter critical section. Queue head: {self.server.queue[0]}" + Style.RESET_ALL)
            while self.server.queue[0][1] != self.server.pid:
                self.server.cv.wait()

        print(Fore.GREEN + f"[Lamport][P{self.server.pid}] Entered critical section" + Style.RESET_ALL)
        time.sleep(2)  # simulate critical section work
        print(Fore.YELLOW + f"[Lamport][P{self.server.pid}] Exited critical section" + Style.RESET_ALL)

        # broadcast Release to all peers
        for peer_pid, addr in self.peers.items():
            if peer_pid == self.server.pid:
                continue
            stub = rpc.MutexStub(grpc.insecure_channel(addr))
            try:
                print(Fore.BLUE + f"[Lamport][P{self.server.pid}] Sending RELEASE to P{peer_pid}" + Style.RESET_ALL)
                stub.Release(pb.ReleaseMsg(pid=self.server.pid))
            except Exception as e:
                print(Fore.RED + f"[Lamport][P{self.server.pid}] Error releasing peer P{peer_pid}: {e}" + Style.RESET_ALL)

    def run(self):
        # simulation loop
        while True:
            time.sleep(5 + self.server.pid)
            self.enter_critical()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--peers", required=True,
                        help="comma-separated list of pid:host:port")

    args = parser.parse_args()

    peers = {}
    for entry in args.peers.split(","):
        pid_str, host, port_str = entry.split(":")
        peers[int(pid_str)] = f"{host}:{port_str}"

    process = LamportProcess(args.pid, args.port, peers)
    process.run()
