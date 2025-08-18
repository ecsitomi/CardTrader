#!/usr/bin/env python3
"""
Kritikus hibák gyors javítása a Kártya Csere Platform projektben
Futtatás: python fix_critical_bugs.py
"""

import os
import shutil
from pathlib import Path

def fix_requirements():
    """Requirements.txt javítása"""
    print("🔧 Requirements.txt javítása...")
    
    correct_requirements = """streamlit>=1.28.0
# bcrypt>=4.0.0  # Opcionális: biztonságos jelszó kezeléshez
# pillow>=9.0.0  # Opcionális: képkezeléshez
"""
    
    with open("requirements.txt", "w") as f:
        f.write(correct_requirements)
    
    print("✅ Requirements.txt javítva!")

def fix_page_names():
    """Oldal fájlnevek javítása (emoji eltávolítása)"""
    print("🔧 Oldal fájlnevek javítása...")
    
    pages_dir = Path("pages")
    if not pages_dir.exists():
        print("❌ pages mappa nem található!")
        return
    
    # Fájlnév mapping
    renames = {
        "02_🃏_Kártyáim.py": "02_Kartyaim.py",
        "03_🔍_Keresés.py": "03_Kereses.py",
        "04_⭐_Kívánságlista.py": "04_Kivansaglista.py",
        "05_📨_Üzenetek.py": "05_Uzenetek.py",
        "06_👤_Profil.py": "06_Profil.py",
        "07_🎯_Matchmaking.py": "07_Matchmaking.py"
    }
    
    for old_name, new_name in renames.items():
        old_path = pages_dir / old_name
        new_path = pages_dir / new_name
        
        if old_path.exists():
            shutil.move(str(old_path), str(new_path))
            print(f"  ✅ {old_name} → {new_name}")

def add_init_files():
    """__init__.py fájlok hozzáadása a megfelelő import-okhoz"""
    print("🔧 __init__.py fájlok hozzáadása...")
    
    # Root __init__.py
    with open("__init__.py", "w") as f:
        f.write('"""Kártya Csere Platform"""\n')
    
    # pages/__init__.py
    pages_dir = Path("pages")
    if pages_dir.exists():
        with open(pages_dir / "__init__.py", "w") as f:
            f.write('"""Platform oldalak"""\n')
    
    print("✅ __init__.py fájlok létrehozva!")

def create_config_file():
    """Konfiguráció fájl létrehozása"""
    print("🔧 Konfiguráció fájl létrehozása...")
    
    config_content = """# config.py
import os
from pathlib import Path

# Alap beállítások
BASE_DIR = Path(__file__).parent
DATABASE_NAME = 'cards_platform.db'
DATABASE_PATH = BASE_DIR / DATABASE_NAME

# Streamlit beállítások
PAGE_CONFIG = {
    "page_title": "Kártya Csere Platform",
    "page_icon": "🃏",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Biztonság
SECRET_KEY = os.environ.get('SECRET_KEY', 'development-key-change-in-production')
PASSWORD_SALT_ROUNDS = 100000  # PBKDF2 iterációk száma

# Rate limiting
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT_SECONDS = 300  # 5 perc

# Fejlesztői mód
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
"""
    
    with open("config.py", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print("✅ config.py létrehozva!")

def update_imports_in_pages():
    """Import utasítások javítása a pages mappában"""
    print("🔧 Import utasítások javítása...")
    
    pages_dir = Path("pages")
    if not pages_dir.exists():
        print("❌ pages mappa nem található!")
        return
    
    # Minden .py fájl a pages mappában
    for py_file in pages_dir.glob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # sys.path manipuláció eltávolítása és helyettesítése
        old_import = """import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)"""
        
        new_import = """import sys
import os
from pathlib import Path

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent.parent))"""
        
        if old_import in content:
            content = content.replace(old_import, new_import)
            
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"  ✅ {py_file.name} importok javítva")

def create_run_script():
    """Indító script létrehozása"""
    print("🔧 Indító script létrehozása...")
    
    run_script = """#!/usr/bin/env python3
\"\"\"
Kártya Csere Platform indító script
Használat: python run.py
\"\"\"

import subprocess
import sys

def main():
    print("🚀 Kártya Csere Platform indítása...")
    print("-" * 50)
    
    try:
        # Streamlit futtatása
        subprocess.run([sys.executable, "-m", "streamlit", "run", "main.py"])
    except KeyboardInterrupt:
        print("\\n👋 Viszlát!")
    except Exception as e:
        print(f"❌ Hiba történt: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
    
    with open("run.py", "w", encoding="utf-8") as f:
        f.write(run_script)
    
    # Futtathatóvá tesszük Linux/Mac rendszeren
    os.chmod("run.py", 0o755)
    
    print("✅ run.py létrehozva!")

def main():
    """Fő javító folyamat"""
    print("=" * 50)
    print("🔧 KÁRTYA CSERE PLATFORM - KRITIKUS HIBÁK JAVÍTÁSA")
    print("=" * 50)
    
    # 1. Requirements javítása
    fix_requirements()
    
    # 2. Oldal nevek javítása (opcionális)
    # fix_page_names()  # Kommenteld ki, ha nem akarod
    
    # 3. Init fájlok
    add_init_files()
    
    # 4. Config fájl
    create_config_file()
    
    # 5. Import javítások
    update_imports_in_pages()
    
    # 6. Indító script
    create_run_script()
    
    print("=" * 50)
    print("✅ KÉSZ! A kritikus hibák javítva!")
    print("\n📌 Következő lépések:")
    print("1. pip install -r requirements.txt")
    print("2. python run.py")
    print("3. Teszteld az alkalmazást!")
    print("=" * 50)

if __name__ == "__main__":
    main()