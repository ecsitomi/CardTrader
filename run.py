#!/usr/bin/env python3
"""
Kártya Csere Platform indító script
Használat: python run.py
"""

import subprocess
import sys

def main():
    print("🚀 Kártya Csere Platform indítása...")
    print("-" * 50)
    
    try:
        # Streamlit futtatása
        subprocess.run([sys.executable, "-m", "streamlit", "run", "main.py"])
    except KeyboardInterrupt:
        print("\n👋 Viszlát!")
    except Exception as e:
        print(f"❌ Hiba történt: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
