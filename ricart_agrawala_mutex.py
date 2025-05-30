# -*- coding: utf-8 -*-
import grpc, threading, time, argparse
from concurrent import futures
from colorama import init, Fore, Style
import pyfiglet

import mutual_exclusion_pb2 as pb
import mutual_exclusion_pb2_grpc as rpc

init(autoreset=True)

def print_title():
    ascii_art = pyfiglet.figlet_format("AGRWALA")
    print(Fore.MAGENTA + Style.BRIGHT + ascii_art)
    print(Fore.YELLOW + Style.BRIGHT + "Mutual Exclusion Algorithm (Ricart & Agrawala)")

class RA_Server(rpc.MutexServicer):
    def __init__(self, pid, peers):
        self.pid = pid
        self.clock = 0
        self.peers = peers
        self.hostport = peers[pid]
        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)

        self.requesting = False
        self.request_time = None
        self.replies_pending = set()
        self.deferred_replies = set()

    def Request(self, req, ctx):
        with self.lock:
            self.clock = max(self.clock, req.timestamp) + 1
            print(Fore.YELLOW + Style.BRIGHT + f"[RA][P{self.pid}] Received REQUEST from P{req.pid} @ {req.timestamp}")

            if self.requesting and (self.request_time, self.pid) < (req.timestamp, req.pid):
                self.deferred_replies.add(req.pid)
                print(Fore.CYAN + Style.BRIGHT + f"[RA][P{self.pid}] Deferred reply to P{req.pid}")
                return pb.ReplyMsg(timestamp=self.clock, pid=self.pid)
            else:
                channel = grpc.insecure_channel(self.peers[req.pid])
                stub = rpc.MutexStub(channel)
                stub.Reply(pb.ReplyMsg(timestamp=self.clock, pid=self.pid))
                print(Fore.GREEN + Style.BRIGHT + f"[RA][P{self.pid}] Immediate reply to P{req.pid}")
                return pb.ReplyMsg(timestamp=self.clock, pid=self.pid)

    def Reply(self, req, ctx):
        with self.lock:
            print(Fore.BLUE + Style.BRIGHT + f"[RA][P{self.pid}] Received REPLY from P{req.pid}")
            self.replies_pending.discard(req.pid)
            if not self.replies_pending:
                self.cv.notify()
        return pb.Empty()

    def Release(self, req, ctx):
        return pb.Empty()

    def start(self, port):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        rpc.add_MutexServicer_to_server(self, server)
        server.add_insecure_port(f"[::]:{port}")
        server.start()
        print(Fore.MAGENTA + Style.BRIGHT + f"[RA][P{self.pid}] gRPC server launched on port {port}")
        return server

class RA_Process:
    def __init__(self, pid, port, peers):
        
        self.server = RA_Server(pid, peers)
        self.port = port
        self.peers = peers
        self.stub_map = {p: rpc.MutexStub(grpc.insecure_channel(addr)) for p, addr in peers.items() if p != pid}
        self.server_thread = self.server.start(port)
        time.sleep(1)

    def enter_critical(self):
        with self.server.lock:
            self.server.clock += 1
            self.server.requesting = True
            self.server.request_time = self.server.clock
            self.server.replies_pending = set(self.stub_map.keys())

        for peer_id, stub in self.stub_map.items():
            try:
                stub.Request(pb.RequestMsg(timestamp=self.server.request_time,
                                           pid=self.server.pid))
            except Exception as e:
                print(Fore.RED + f"[RA][P{self.server.pid}] Request error to P{peer_id}: {e}")

        with self.server.cv:
            while self.server.replies_pending:
                self.server.cv.wait()

        print(Fore.GREEN + Style.BRIGHT + f"[RA][P{self.server.pid}] ENTERING CRITICAL SECTION")
        time.sleep(2)
        print(Fore.RED + Style.BRIGHT + f"[RA][P{self.server.pid}] EXITING CRITICAL SECTION")

        with self.server.lock:
            self.server.requesting = False
            for peer_id in self.server.deferred_replies:
                try:
                    self.stub_map[peer_id].Reply(pb.ReplyMsg(timestamp=self.server.clock, pid=self.server.pid))
                    print(Fore.CYAN + f"[RA][P{self.server.pid}] Sending deferred REPLY to P{peer_id}")
                except Exception as e:
                    print(Fore.RED + f"[RA][P{self.server.pid}] Error sending deferred REPLY to P{peer_id}: {e}")
            self.server.deferred_replies.clear()

    def run(self):
        while True:
            time.sleep(5 + self.server.pid)
            self.enter_critical()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--peers", required=True)
   

    args = parser.parse_args()

    peers = {}
    for entry in args.peers.split(","):
        pid, host, port = entry.split(":")
        peers[int(pid)] = f"{host}:{port}"

    proc = RA_Process(args.pid, args.port, peers)
    proc.run()