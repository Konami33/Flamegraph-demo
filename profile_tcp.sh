#!/bin/bash

# FlameGraph Profiling Script for TCP Server Analysis
# This script sets up profiling and generates FlameGraphs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROFILE_DURATION=30
FLAMEGRAPH_DIR="flamegraph_output"
SERVER_SCRIPT="server.py"
CLIENT_SCRIPT="client.py"

echo -e "${BLUE}=== FlameGraph TCP Server Profiling Setup ===${NC}"

# Function to print colored output
print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (needed for perf)
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script needs to be run as root for perf profiling"
        echo "Please run: sudo $0"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    print_step "Checking dependencies..."
    
    # Check perf
    if ! command -v perf &> /dev/null; then
        print_error "perf not found. Install with: sudo apt-get install linux-tools-common linux-tools-generic"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "python3 not found"
        exit 1
    fi
    
    # Check if FlameGraph tools exist
    if [ ! -f "flamegraph.pl" ]; then
        print_info "FlameGraph tools not found. Downloading..."
        git clone https://github.com/brendangregg/FlameGraph.git
        cp FlameGraph/*.pl .
        chmod +x *.pl
    fi
    
    print_info "All dependencies satisfied"
}

# Setup profiling environment
setup_environment() {
    print_step "Setting up profiling environment..."
    
    # Create output directory
    mkdir -p "$FLAMEGRAPH_DIR"
    
    # Set perf settings for better stack traces
    echo -1 > /proc/sys/kernel/perf_event_paranoid
    echo 0 > /proc/sys/kernel/kptr_restrict
    
    print_info "Environment ready"
}

# Start the TCP server in background
start_server() {
    print_step "Starting TCP server..."
    
    python3 "$SERVER_SCRIPT" &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 2
    
    # Check if server is running
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        print_error "Failed to start server"
        exit 1
    fi
    
    print_info "Server started with PID: $SERVER_PID"
}

# Profile with different scenarios
profile_scenario() {
    local scenario_name=$1
    local client_args=$2
    
    print_step "Profiling scenario: $scenario_name"
    
    # Start profiling
    print_info "Starting perf profiling for $PROFILE_DURATION seconds..."
    perf record -F 99 -p $SERVER_PID -g -o "${FLAMEGRAPH_DIR}/${scenario_name}.perf" -- sleep $PROFILE_DURATION &
    PERF_PID=$!
    
    # Wait a moment for perf to start
    sleep 1
    
    # Start client load
    print_info "Starting client load..."
    python3 "$CLIENT_SCRIPT" $client_args &
    CLIENT_PID=$!
    
    # Wait for profiling to complete
    wait $PERF_PID
    
    # Stop client if still running
    if kill -0 $CLIENT_PID 2>/dev/null; then
        kill $CLIENT_PID
    fi
    
    print_info "Profiling completed for $scenario_name"
}

# Generate FlameGraphs
generate_flamegraphs() {
    print_step "Generating FlameGraphs..."
    
    cd "$FLAMEGRAPH_DIR"
    
    for perf_file in *.perf; do
        if [ -f "$perf_file" ]; then
            scenario_name=$(basename "$perf_file" .perf)
            print_info "Processing $scenario_name..."
            
            # Convert perf data to text
            perf script -i "$perf_file" > "${scenario_name}.perf.txt"
            
            # Fold stacks
            ../stackcollapse-perf.pl "${scenario_name}.perf.txt" > "${scenario_name}.folded"
            
            # Generate FlameGraph
            ../flamegraph.pl "${scenario_name}.folded" > "${scenario_name}.svg"
            
            # Generate filtered FlameGraphs for specific functions
            grep "fibonacci\|handle_compute" "${scenario_name}.folded" | \
                ../flamegraph.pl > "${scenario_name}_compute.svg" 2>/dev/null || true
            
            grep "handle_hash\|hashlib" "${scenario_name}.folded" | \
                ../flamegraph.pl > "${scenario_name}_hash.svg" 2>/dev/null || true
            
            grep "socket\|recv\|send" "${scenario_name}.folded" | \
                ../flamegraph.pl > "${scenario_name}_network.svg" 2>/dev/null || true
            
            print_info "Generated FlameGraphs for $scenario_name"
        fi
    done
    
    cd ..
}

# Cleanup function
cleanup() {
    print_step "Cleaning up..."
    
    # Kill server if running
    if [ ! -z "$SERVER_PID" ] && kill -0 $SERVER_PID 2>/dev/null; then
        kill $SERVER_PID
        print_info "Server stopped"
    fi
    
    # Kill client if running
    if [ ! -z "$CLIENT_PID" ] && kill -0 $CLIENT_PID 2>/dev/null; then
        kill $CLIENT_PID
        print_info "Client stopped"
    fi
    
    # Kill perf if running
    if [ ! -z "$PERF_PID" ] && kill -0 $PERF_PID 2>/dev/null; then
        kill $PERF_PID
        print_info "Perf stopped"
    fi
}

# Main profiling function
run_profiling() {
    print_step "Starting comprehensive TCP server profiling..."
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    start_server
    
    # Scenario 1: Light load (echo requests)
    print_info "=== Scenario 1: Light Load (Echo) ==="
    echo "1" | python3 "$CLIENT_SCRIPT" &
    CLIENT_PID=$!
    sleep 5
    
    perf record -F 99 -p $SERVER_PID -g -o "${FLAMEGRAPH_DIR}/light_load.perf" -- sleep 15 &
    PERF_PID=$!
    wait $PERF_PID
    
    kill $CLIENT_PID 2>/dev/null || true
    
    # Scenario 2: CPU intensive (compute requests)
    print_info "=== Scenario 2: CPU Intensive (Compute) ==="
    echo -e "2\n10" | python3 "$CLIENT_SCRIPT" &
    CLIENT_PID=$!
    sleep 2
    
    perf record -F 99 -p $SERVER_PID -g -o "${FLAMEGRAPH_DIR}/cpu_intensive.perf" -- sleep 20 &
    PERF_PID=$!
    wait $PERF_PID
    
    kill $CLIENT_PID 2>/dev/null || true
    
    # Scenario 3: Load test (multiple clients)
    print_info "=== Scenario 3: Load Test ==="
    echo -e "3\n5\n15" | python3 "$CLIENT_SCRIPT" &
    CLIENT_PID=$!
    sleep 2
    
    perf record -F 99 -p $SERVER_PID -g -o "${FLAMEGRAPH_DIR}/load_test.perf" -- sleep 20 &
    PERF_PID=$!
    wait $PERF_PID
    
    kill $CLIENT_PID 2>/dev/null || true
    
    print_info "All profiling scenarios completed"
}

# Display results
show_results() {
    print_step "Profiling Results Summary"
    
    echo -e "\n${BLUE}Generated FlameGraphs:${NC}"
    ls -la "$FLAMEGRAPH_DIR"/*.svg 2>/dev/null || echo "No SVG files found"
    
    echo -e "\n${BLUE}To view FlameGraphs:${NC}"
    echo "1. Open the SVG files in a web browser"
    echo "2. Use Python HTTP server: python3 -m http.server 8000"
    echo "3. Navigate to http://localhost:8000/$FLAMEGRAPH_DIR/"
    
    echo -e "\n${BLUE}Analysis Tips:${NC}"
    echo "- light_load.svg: Shows baseline server performance"
    echo "- cpu_intensive.svg: Shows CPU hotspots (look for fibonacci)"
    echo "- load_test.svg: Shows performance under concurrent load"
    echo "- *_compute.svg: Filtered view of computation functions"
    echo "- *_network.svg: Filtered view of network I/O functions"
    
    echo -e "\n${YELLOW}Look for:${NC}"
    echo "- Wide boxes at the top = functions using most CPU"
    echo "- Tall stacks = deep call chains"
    echo "- fibonacci function should dominate in CPU intensive test"
    echo "- socket/network functions in load test"
}

# Main execution
main() {
    echo -e "${BLUE}TCP Server FlameGraph Profiling${NC}"
    echo "This script will:"
    echo "1. Set up profiling environment"
    echo "2. Start TCP server"
    echo "3. Run different load scenarios"
    echo "4. Generate FlameGraphs"
    echo ""
    
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    
    check_root
    check_dependencies
    setup_environment
    run_profiling
    generate_flamegraphs
    show_results
    
    print_step "Profiling complete! Check the $FLAMEGRAPH_DIR directory for results."
}

# Run main function
main "$@"