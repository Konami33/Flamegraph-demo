#!/usr/bin/env python3
"""
Python cProfile integration for TCP server
This version works without root access by using Python's built-in profiler
"""

import cProfile
import pstats
import io
import sys
import os
import subprocess
import threading
import time
import signal
from server import TCPServer

class ProfiledTCPServer:
    def __init__(self, host='localhost', port=8888):
        self.server = TCPServer(host, port)
        self.profiler = None
        self.profile_thread = None
        self.running = False
        
    def start_profiled_server(self, profile_duration=30):
        """Start server with profiling enabled"""
        print(f"Starting profiled TCP server for {profile_duration} seconds...")
        
        # Create profiler
        self.profiler = cProfile.Profile()
        self.running = True
        
        # Start profiling in a separate thread
        self.profile_thread = threading.Thread(
            target=self._run_server_with_profiling,
            args=(profile_duration,)
        )
        self.profile_thread.start()
        
        return self.profile_thread
    
    def _run_server_with_profiling(self, duration):
        """Run server with profiling for specified duration"""
        try:
            # Start profiling
            self.profiler.enable()
            
            # Start server in a separate thread
            server_thread = threading.Thread(target=self.server.start_server)
            server_thread.daemon = True
            server_thread.start()
            
            # Wait for specified duration
            time.sleep(duration)
            
        except KeyboardInterrupt:
            pass
        finally:
            # Stop profiling
            self.profiler.disable()
            self.running = False
            print("Profiling stopped")
    
    def save_profile_stats(self, filename="server_profile.stats"):
        """Save profiling statistics"""
        if self.profiler:
            self.profiler.dump_stats(filename)
            print(f"Profile saved to {filename}")
    
    def print_profile_stats(self, sort_by='cumulative', lines=20):
        """Print profile statistics"""
        if not self.profiler:
            print("No profiling data available")
            return
        
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats(sort_by)
        ps.print_stats(lines)
        print(s.getvalue())

def convert_profile_to_flamegraph(stats_file, output_dir="flamegraph_output"):
    """Convert Python profile to FlameGraph format"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert stats to FlameGraph format using py-spy format
    try:
        # First, let's create a simple converter
        print("Converting profile to FlameGraph format...")
        
        # Load the stats
        stats = pstats.Stats(stats_file)
        
        # Create folded format manually
        folded_file = os.path.join(output_dir, "python_profile.folded")
        
        with open(folded_file, 'w') as f:
            for func, (cc, nc, tt, ct, callers) in stats.stats.items():
                filename, line, func_name = func
                # Create a simple stack representation
                stack_name = f"{filename}:{func_name}"
                f.write(f"{stack_name} {int(ct * 1000)}\n")  # Convert to integer samples
        
        print(f"Created folded format: {folded_file}")
        
        # Generate FlameGraph if flamegraph.pl is available
        flamegraph_script = "flamegraph.pl"
        if os.path.exists(flamegraph_script):
            svg_file = os.path.join(output_dir, "python_profile.svg")
            cmd = f"./{flamegraph_script} {folded_file} > {svg_file}"
            subprocess.run(cmd, shell=True, check=True)
            print(f"FlameGraph generated: {svg_file}")
        else:
            print("flamegraph.pl not found. Download FlameGraph tools from:")
            print("https://github.com/brendangregg/FlameGraph")
            
    except Exception as e:
        print(f"Error converting profile: {e}")

def run_load_test_scenario():
    """Run a comprehensive load test with profiling"""
    
    print("=== TCP Server FlameGraph Analysis ===")
    print("This will:")
    print("1. Start a profiled TCP server")
    print("2. Run client load tests")
    print("3. Generate FlameGraph visualization")
    print()
    
    # Configuration
    profile_duration = 45
    output_dir = "flamegraph_output"
    
    # Start profiled server
    profiled_server = ProfiledTCPServer()
    server_thread = profiled_server.start_profiled_server(profile_duration)
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        print("Server started. Running client scenarios...")
        
        # Import client after server starts
        from client import TCPClient
        client = TCPClient()
        
        # Scenario 1: Warm up (5 seconds)
        print("Phase 1: Warm up...")
        warm_thread = threading.Thread(target=lambda: client.persistent_connection_test(5))
        warm_thread.start()
        warm_thread.join()
        
        # Scenario 2: CPU intensive load (15 seconds)
        print("Phase 2: CPU intensive load...")
        def cpu_intensive_load():
            import json
            for i in range(50):
                request = {
                    'type': 'compute',
                    'number': 25 + (i % 10)  # Fibonacci 25-35
                }
                client.connect_and_send(json.dumps(request))
                time.sleep(0.2)
        
        cpu_thread = threading.Thread(target=cpu_intensive_load)
        cpu_thread.start()
        cpu_thread.join()
        
        # Scenario 3: Mixed load test (remaining time)
        print("Phase 3: Mixed concurrent load...")
        remaining_time = profile_duration - 25  # 45 - 5 - 15 = 25 seconds
        if remaining_time > 0:
            load_thread = threading.Thread(
                target=lambda: client.load_test(num_clients=3, duration=remaining_time)
            )
            load_thread.start()
            load_thread.join()
        
        print("Client load testing completed")
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error during load test: {e}")
    
    # Wait for profiling to complete
    print("Waiting for profiling to complete...")
    server_thread.join()
    
    # Save and analyze results
    stats_file = "server_profile.stats"
    profiled_server.save_profile_stats(stats_file)
    
    print("\n=== Profile Statistics ===")
    profiled_server.print_profile_stats(lines=15)
    
    # Convert to FlameGraph
    convert_profile_to_flamegraph(stats_file, output_dir)
    
    print(f"\n=== Results ===")
    print(f"Profile data saved to: {stats_file}")
    print(f"FlameGraph files in: {output_dir}")
    print("\nTo view results:")
    print("1. Open flamegraph_output/python_profile.svg in a web browser")
    print("2. Or run: python3 -m http.server 8000")
    print("   Then visit: http://localhost:8000/flamegraph_output/")

def analyze_existing_profile(stats_file="server_profile.stats"):
    """Analyze an existing profile file"""
    if not os.path.exists(stats_file):
        print(f"Profile file {stats_file} not found")
        return
    
    print(f"Analyzing profile: {stats_file}")
    
    # Load and display stats
    stats = pstats.Stats(stats_file)
    
    print("\n=== Top Functions by Cumulative Time ===")
    stats.sort_stats('cumulative').print_stats(15)
    
    print("\n=== Top Functions by Total Time ===")
    stats.sort_stats('tottime').print_stats(15)
    
    print("\n=== Network/Socket Related Functions ===")
    stats.print_stats('socket|recv|send|accept')
    
    print("\n=== Computation Related Functions ===")
    stats.print_stats('fibonacci|compute|hash')
    
    # Convert to FlameGraph
    convert_profile_to_flamegraph(stats_file)

def setup_flamegraph_tools():
    """Download and setup FlameGraph tools if not present"""
    if not os.path.exists("flamegraph.pl"):
        print("FlameGraph tools not found. Setting up...")
        try:
            subprocess.run([
                "git", "clone", 
                "https://github.com/brendangregg/FlameGraph.git"
            ], check=True)
            
            # Copy scripts to current directory
            for script in ["flamegraph.pl", "stackcollapse.pl", "stackcollapse-perf.pl"]:
                src = f"FlameGraph/{script}"
                if os.path.exists(src):
                    subprocess.run(["cp", src, "."], check=True)
                    subprocess.run(["chmod", "+x", script], check=True)
            
            print("FlameGraph tools setup complete")
            return True
            
        except subprocess.CalledProcessError:
            print("Failed to setup FlameGraph tools")
            print("Please manually download from: https://github.com/brendangregg/FlameGraph")
            return False
    else:
        print("FlameGraph tools already available")
        return True

def create_enhanced_folded_format(stats_file, output_file):
    """Create a more detailed folded format for better FlameGraphs"""
    stats = pstats.Stats(stats_file)
    
    # Build call graph
    call_graph = {}
    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        filename, line, func_name = func
        func_key = f"{os.path.basename(filename)}:{func_name}"
        
        if func_key not in call_graph:
            call_graph[func_key] = {
                'self_time': tt,
                'total_time': ct,
                'call_count': cc,
                'callers': []
            }
        
        # Add caller information
        for caller, (caller_cc, caller_nc, caller_tt, caller_ct) in callers.items():
            caller_filename, caller_line, caller_func_name = caller
            caller_key = f"{os.path.basename(caller_filename)}:{caller_func_name}"
            call_graph[func_key]['callers'].append({
                'name': caller_key,
                'time': caller_ct
            })
    
    # Generate folded format with call stacks
    with open(output_file, 'w') as f:
        for func_name, data in call_graph.items():
            # Simple entry (function only)
            samples = int(data['total_time'] * 1000)
            if samples > 0:
                f.write(f"{func_name} {samples}\n")
            
            # Add caller-callee relationships
            for caller in data['callers']:
                caller_samples = int(caller['time'] * 1000)
                if caller_samples > 0:
                    stack = f"{caller['name']};{func_name}"
                    f.write(f"{stack} {caller_samples}\n")

def main():
    """Main function with different modes"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TCP Server FlameGraph Profiler')
    parser.add_argument('--mode', choices=['profile', 'analyze', 'setup'], 
                       default='profile', help='Operation mode')
    parser.add_argument('--stats-file', default='server_profile.stats',
                       help='Profile stats file')
    parser.add_argument('--duration', type=int, default=45,
                       help='Profiling duration in seconds')
    
    args = parser.parse_args()
    
    if args.mode == 'setup':
        setup_flamegraph_tools()
    elif args.mode == 'analyze':
        analyze_existing_profile(args.stats_file)
    else:  # profile mode
        setup_flamegraph_tools()
        run_load_test_scenario()

if __name__ == '__main__':
    main()