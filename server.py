#!/usr/bin/env python3
import socket
import threading
import time
import json
import hashlib

class TCPServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.clients = []
        
    def start_server(self):
        """Start the TCP server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            print(f"Server listening on {self.host}:{self.port}")
            
            while True:
                client_socket, client_address = server_socket.accept()
                print(f"Connection from {client_address}")
                self.clients.append(client_socket)
                
                # Create a new thread for each client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        finally:
            server_socket.close()
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connections"""
        try:
            while True:
                # Receive data from client
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                print(f"Received from {client_address}: {data}")
                
                # Process the data (simulate some work)
                response = self.process_request(data)
                
                # Send response back to client
                client_socket.send(response.encode('utf-8'))
                
        except ConnectionResetError:
            print(f"Client {client_address} disconnected")
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
            if client_socket in self.clients:
                self.clients.remove(client_socket)
    
    def process_request(self, data):
        """Process client requests - simulate different types of work"""
        try:
            request = json.loads(data)
            request_type = request.get('type', 'echo')
            
            if request_type == 'echo':
                return self.handle_echo(request)
            elif request_type == 'compute':
                return self.handle_compute(request)
            elif request_type == 'hash':
                return self.handle_hash(request)
            elif request_type == 'slow':
                return self.handle_slow_operation(request)
            else:
                return json.dumps({'error': 'Unknown request type'})
                
        except json.JSONDecodeError:
            # Handle non-JSON messages
            return json.dumps({
                'type': 'echo',
                'response': f"Echo: {data}",
                'timestamp': time.time()
            })
    
    def handle_echo(self, request):
        """Simple echo handler"""
        return json.dumps({
            'type': 'echo',
            'response': f"Echo: {request.get('message', '')}",
            'timestamp': time.time()
        })
    
    def handle_compute(self, request):
        """CPU-intensive computation"""
        n = request.get('number', 1000)
        result = self.fibonacci(n)
        return json.dumps({
            'type': 'compute',
            'input': n,
            'result': result,
            'timestamp': time.time()
        })
    
    def handle_hash(self, request):
        """Hash computation - simulate crypto work"""
        data = request.get('data', 'default')
        iterations = request.get('iterations', 10000)
        
        # Simulate intensive hashing
        result = data
        for i in range(iterations):
            result = hashlib.sha256(result.encode()).hexdigest()
        
        return json.dumps({
            'type': 'hash',
            'result': result[:32],  # Return first 32 chars
            'iterations': iterations,
            'timestamp': time.time()
        })
    
    def handle_slow_operation(self, request):
        """Simulate slow I/O or database operation"""
        delay = request.get('delay', 0.1)
        time.sleep(delay)  # Simulate slow operation
        
        return json.dumps({
            'type': 'slow',
            'message': f"Completed slow operation with {delay}s delay",
            'timestamp': time.time()
        })
    
    def fibonacci(self, n):
        """Recursive fibonacci - intentionally inefficient for profiling"""
        if n <= 1:
            return n
        return self.fibonacci(n - 1) + self.fibonacci(n - 2)

if __name__ == '__main__':
    server = TCPServer()
    server.start_server()