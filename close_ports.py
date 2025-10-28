#!/usr/bin/env python3
"""
Close Ports Script
Closes all ports used by Nexus Alpha applications
"""
import subprocess
import sys
import time

def close_port(port):
    """Close a specific port by killing the process using it"""
    try:
        # Find process using the port
        result = subprocess.run(
            ['netstat', '-ano'], 
            capture_output=True, 
            text=True, 
            shell=True
        )
        
        if result.returncode != 0:
            print(f"Error running netstat: {result.stderr}")
            return False
        
        # Parse netstat output to find PID
        lines = result.stdout.split('\n')
        pid = None
        
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    break
        
        if pid:
            print(f"Found process {pid} using port {port}")
            
            # Kill the process
            kill_result = subprocess.run(
                ['taskkill', '/F', '/PID', pid],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if kill_result.returncode == 0:
                print(f"SUCCESS - Closed port {port}")
                return True
            else:
                print(f"FAILED - Could not kill process {pid}: {kill_result.stderr}")
                return False
        else:
            print(f"INFO - No process found using port {port}")
            return True
            
    except Exception as e:
        print(f"ERROR - Could not close port {port}: {e}")
        return False

def main():
    """Close all Nexus Alpha ports"""
    print("Nexus Alpha - Port Cleanup")
    print("=" * 30)
    
    # Ports used by Nexus Alpha applications
    ports = [8010, 8011, 8012, 8013, 8014]
    
    closed_count = 0
    total_count = len(ports)
    
    for port in ports:
        print(f"Closing port {port}...")
        if close_port(port):
            closed_count += 1
        time.sleep(1)  # Brief pause between port closures
    
    print("\n" + "=" * 30)
    print(f"Port cleanup complete: {closed_count}/{total_count} ports closed")
    
    if closed_count == total_count:
        print("SUCCESS - All ports successfully closed")
        return 0
    else:
        print("WARNING - Some ports may still be in use")
        return 1

if __name__ == "__main__":
    sys.exit(main())
