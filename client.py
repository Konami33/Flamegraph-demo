#!/usr/bin/env python3
import socket
import json
import time
import threading
import random

class TCPClient:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        
    def connect_and_send(self, message):
        """Connect to server and send a single message"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.host, self.port))
            
            # Send message
            client_socket.send(message.encode('utf-8'))
            
            # Receive response
            response = client_socket.recv(1024).decode('utf-8')
            print(f"Response: {response}")
            
            client_socket.close()
            return response
            
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def persistent_connection_test(self, duration=30):
        """Maintain persistent connection and send multiple requests"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.host, self.port))
            print(f"Connected to {self.host}:{self.port}")
            
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < duration:
                # Generate different types of requests
                request = self.generate_random_request()
                
                # Send request
                client_socket.send(json.dumps(request).encode('utf-8'))
                
                # Receive response
                response = client_socket.recv(1024).decode('utf-8')
                request_count += 1
                
                if request_count % 10 == 0:
                    print(f"Sent {request_count} requests...")
                
                # Small delay between requests
                time.sleep(0.1)
            
            print(f"Completed {request_count} requests in {duration} seconds")
            client_socket.close()
            
        except Exception as e:
            print(f"Error in persistent connection: {e}")
    
    def generate_random_request(self):
        """Generate random requests of different types"""
        request_types = ['echo', 'compute', 'hash', 'slow']
        request_type = random.choice(request_types)
        
        if request_type == 'echo':
            return {
                'type': 'echo',
                'message': f"Hello from client at {time.time()}"
            }
        elif request_type == 'compute':
            return {
                'type': 'compute',
                'number': random.randint(20, 35)  # Small fibonacci numbers
            }
        elif request_type == 'hash':
            return {
                'type': 'hash',
                'data': f"data_{random.randint(1, 1000)}",
                'iterations': random.randint(1000, 5000)
            }
        elif request_type == 'slow':
            return {
                'type': 'slow',
                'delay': random.uniform(0.05, 0.2)
            }
    
    def load_test(self, num_clients=5, duration=20):
        """Simulate multiple concurrent clients"""
        print(f"Starting load test with {num_clients} concurrent clients for {duration} seconds")
        
        threads = []
        for i in range(num_clients):
            thread = threading.Thread(
                target=self.client_worker,
                args=(f"Client-{i+1}", duration)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        print("Load test completed")
    
    def client_worker(self, client_name, duration):
        """Individual client worker for load testing"""
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.host, self.port))
                
                # Send a request
                request = self.generate_random_request()
                client_socket.send(json.dumps(request).encode('utf-8'))
                
                # Receive response
                response = client_socket.recv(1024).decode('utf-8')
                request_count += 1
                
                client_socket.close()
                
                # Random delay between requests
                time.sleep(random.uniform(0.01, 0.1))
                
            except Exception as e:
                print(f"{client_name} error: {e}")
        
        print(f"{client_name} completed {request_count} requests")

def main():
    client = TCPClient()
    
    print("TCP Client Test Options:")
    print("1. Single message test")
    print("2. Persistent connection test")
    print("3. Load test (multiple clients)")
    
    choice = input("Choose test type (1-3): ").strip()
    
    if choice == '1':
        # Single message test
        message = json.dumps({
            'type': 'echo',
            'message': 'Hello from single client!'
        })
        client.connect_and_send(message)
        
    elif choice == '2':
        # Persistent connection test
        duration = int(input("Duration in seconds (default 30): ") or "30")
        client.persistent_connection_test(duration)
        
    elif choice == '3':
        # Load test
        num_clients = int(input("Number of concurrent clients (default 5): ") or "5")
        duration = int(input("Duration in seconds (default 20): ") or "20")
        client.load_test(num_clients, duration)
        
    else:
        print("Invalid choice")

if __name__ == '__main__':
    main()