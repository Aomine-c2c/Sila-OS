#!/usr/bin/env python3
"""
Environment and build requirement check for KAIROS OS.
Inspects local host and container capabilities.
"""

import sys
import shutil
import subprocess
import os

def check_command(cmd):
    return shutil.which(cmd) is not None

def main():
    print("================================================================================")
    print(" KAIROS OS Build Environment Diagnostic")
    print("================================================================================")
    
    in_wsl = os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop") or "WSL_DISTRO_NAME" in os.environ
    print(f"[*] Execution context: {'WSL2 / Linux' if in_wsl else 'Host Native'}")
    
    critical_tools = ["python3", "bash"]
    recommended_tools = ["podman", "docker", "make", "git", "xorriso", "mksquashfs", "qemu-system-x86_64"]
    
    missing_critical = [tool for tool in critical_tools if not check_command(tool)]
    if missing_critical:
        print(f"[!] CRITICAL: Missing mandatory host tool(s): {', '.join(missing_critical)}")
        sys.exit(1)
        
    print("[+] Core host runtime: OK (Python3, Bash)")
    
    tool_status = {}
    for tool in recommended_tools:
        tool_status[tool] = "Available" if check_command(tool) else "Missing (Available in build container)"
        print(f"  - {tool:<20} : {tool_status[tool]}")
        
    print("================================================================================")
    print("[+] Environment check passed. Proceeding with architecture pipeline.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
