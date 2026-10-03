"""
Streamer Party Ready EXE Build Script
Clean ASCII console output to prevent Windows cmd.exe encoding errors
"""

import sys
import os
import subprocess

def run_build():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)

    print("=" * 60)
    print("  Streamer Party Ready EXE Builder")
    print("=" * 60)
    print()
    print("[1/2] Building standalone executable (StreamerPartyReady.exe)...")
    print("      Please wait about 15-20 seconds...")
    print()

    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "streamer_party_ready.spec"]

    try:
        result = subprocess.run(cmd, check=False)
        print()
        if result.returncode == 0:
            exe_path = os.path.join(current_dir, "dist", "StreamerPartyReady.exe")
            print("=" * 60)
            print("  >>> BUILD SUCCESS! <<<")
            print(f"  Output: {exe_path}")
            if os.path.exists(exe_path):
                size_mb = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"  File size: {size_mb:.1f} MB")
            print("=" * 60)
            print("\nYou can now run dist\\StreamerPartyReady.exe directly!")
            return 0
        else:
            print("=" * 60)
            print(f"  [ERROR] Build failed (exit code: {result.returncode})")
            print("=" * 60)
            return result.returncode
    except Exception as e:
        print(f"\n[Error occurred]: {e}")
        return 1

if __name__ == "__main__":
    code = run_build()
    sys.exit(code)
