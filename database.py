import sqlite3
import hashlib
from datetime import datetime
import streamlit as st
import time
from contextlib import contextmanager

DATABASE_NAME = 'cards_platform.db'

@contextmanager
def get_db_connection():
    """Biztonságos adatbázis kapcsolat context managerrel"""
    conn = None
    try:
        # Timeout beállítása és WAL mód
        conn = sqlite3.connect(DATABASE_NAME, timeout=30.0, isolation_level='DEFERRED')
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row  # Dict-szerű sorok
        yield conn
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            # Várunk és újrapróbálkozunk
            time.sleep(0.5)
            conn = sqlite3.connect(DATABASE_NAME, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
        else:
            raise
    finally:
        if conn:
            conn.close()

def get_connection():
    """Legacy függvény - visszafelé kompatibilitás"""
    conn = sqlite3.connect(DATABASE_NAME, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def init_database():
    """Adatbázis táblák inicializálása"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # WAL mód engedélyezése
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Felhasználók tábla
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                profile_info TEXT
            )
        """)
        
        # Sorozatok tábla
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                year INTEGER,
                sport TEXT,
                total_cards INTEGER DEFAULT 400,
                description TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Alapkártyák tábla
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS base_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_id INTEGER NOT NULL,
                card_number INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                team TEXT,
                position TEXT,
                description TEXT,
                FOREIGN KEY (series_id) REFERENCES series (id),
                UNIQUE(series_id, card_number)
            )
        """)
        
        # Kártya változatok
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color_code TEXT,
                rarity_level INTEGER DEFAULT 1,
                description TEXT
            )
        """)
        
        # Felhasználó kártyái
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                base_card_id INTEGER NOT NULL,
                variant_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'owned',
                price DECIMAL(10,2) NULL,
                condition TEXT DEFAULT 'Jó',
                notes TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (base_card_id) REFERENCES base_cards (id),
                FOREIGN KEY (variant_id) REFERENCES card_variants (id),
                UNIQUE(user_id, base_card_id, variant_id)
            )
        """)
        
        # Kívánságlista
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wishlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                base_card_id INTEGER NOT NULL,
                variant_id INTEGER NOT NULL,
                max_price DECIMAL(10,2),
                priority INTEGER DEFAULT 1,
                notes TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (base_card_id) REFERENCES base_cards (id),
                FOREIGN KEY (variant_id) REFERENCES card_variants (id),
                UNIQUE(user_id, base_card_id, variant_id)
            )
        """)
        
        # Üzenetek
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN DEFAULT FALSE,
                parent_message_id INTEGER,
                related_card_id INTEGER,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id),
                FOREIGN KEY (parent_message_id) REFERENCES messages (id),
                FOREIGN KEY (related_card_id) REFERENCES user_cards (id)
            )
        """)
        
        # Aktivitás log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Kártya változatok alapértelmezett adatai
        cursor.execute("SELECT COUNT(*) FROM card_variants")
        if cursor.fetchone()[0] == 0:
            variants = [
                ('Base', '#808080', 1, 'Alapkártya'),
                ('Silver', '#C0C0C0', 2, 'Ezüst változat'),
                ('Pink', '#FFC0CB', 3, 'Rózsaszín változat'),
                ('Red', '#FF0000', 4, 'Piros változat'),
                ('Blue', '#0000FF', 5, 'Kék változat'),
                ('Epic', '#FFD700', 6, 'Epikus változat')
            ]
            
            cursor.executemany("""
                INSERT INTO card_variants (name, color_code, rarity_level, description)
                VALUES (?, ?, ?, ?)
            """, variants)
        
        conn.commit()

# =================== FELHASZNÁLÓ FUNKCIÓK ===================

def hash_password(password):
    """Jelszó hashelése"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, email, password):
    """Új felhasználó létrehozása - JAVÍTOTT VERZIÓ"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            password_hash = hash_password(password)
            
            # Egy tranzakcióban végezzük az összes műveletet
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (?, ?, ?)
                """, (username, email, password_hash))
                
                user_id = cursor.lastrowid
                
                # Log activity ugyanabban a tranzakcióban
                cursor.execute("""
                    INSERT INTO activity_log (user_id, action, description)
                    VALUES (?, ?, ?)
                """, (user_id, "user_registered", "Felhasználó regisztrált"))
                
                conn.commit()
                return True, "Sikeres regisztráció!"
                
            except:
                conn.rollback()
                raise
                
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Ez a felhasználónév már foglalt!"
        elif "email" in str(e):
            return False, "Ez az email cím már regisztrált!"
        else:
            return False, "Hiba történt a regisztráció során!"
    except Exception as e:
        return False, f"Adatbázis hiba: {str(e)}"

def authenticate_user(username, password):
    """Felhasználó hitelesítése - JAVÍTOTT"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute("""
            SELECT id, username, email FROM users 
            WHERE username = ? AND password_hash = ?
        """, (username, password_hash))
        
        user = cursor.fetchone()
        
        if user:
            return True, {"id": user[0], "username": user[1], "email": user[2]}
        else:
            return False, None

def get_all_users():
    """Összes felhasználó lekérése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users ORDER BY username")
        return cursor.fetchall()

# =================== SOROZAT FUNKCIÓK ===================

def add_series(name, year=None, sport="", description=""):
    """Új sorozat hozzáadása"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO series (name, year, sport, description)
                VALUES (?, ?, ?, ?)
            """, (name, year, sport, description))
            
            series_id = cursor.lastrowid
            conn.commit()
            
            return True, series_id
    except sqlite3.IntegrityError:
        return False, "Ez a sorozat már létezik!"

def get_all_series():
    """Összes sorozat lekérése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, year, sport, total_cards, description
            FROM series 
            ORDER BY year DESC, name
        """)
        
        return cursor.fetchall()

def get_series_by_id(series_id):
    """Sorozat lekérése ID alapján"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, year, sport, total_cards, description
            FROM series 
            WHERE id = ?
        """, (series_id,))
        
        return cursor.fetchone()

# =================== ALAPKÁRTYA FUNKCIÓK ===================

def add_base_card(series_id, card_number, player_name, team="", position="", description=""):
    """Alapkártya hozzáadása sorozathoz"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO base_cards (series_id, card_number, player_name, team, position, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (series_id, card_number, player_name, team, position, description))
            
            card_id = cursor.lastrowid
            conn.commit()
            
            return True, card_id
    except sqlite3.IntegrityError:
        return False, "Ez a kártya már létezik ebben a sorozatban!"

def get_base_cards_by_series(series_id):
    """Sorozat alapkártyáinak lekérése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, card_number, player_name, team, position, description
            FROM base_cards 
            WHERE series_id = ?
            ORDER BY card_number
        """, (series_id,))
        
        return cursor.fetchall()

def search_base_cards(query="", series_id=None):
    """Alapkártyák keresése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        sql = """
            SELECT bc.id, bc.card_number, bc.player_name, bc.team, bc.position, 
                   s.name as series_name, s.year
            FROM base_cards bc
            JOIN series s ON bc.series_id = s.id
            WHERE 1=1
        """
        params = []
        
        if query:
            sql += " AND (bc.player_name LIKE ? OR bc.team LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        if series_id:
            sql += " AND bc.series_id = ?"
            params.append(series_id)
        
        sql += " ORDER BY s.name, bc.card_number"
        
        cursor.execute(sql, params)
        return cursor.fetchall()

# =================== KÁRTYA VÁLTOZAT FUNKCIÓK ===================

def get_all_variants():
    """Összes kártya változat lekérése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, color_code, rarity_level, description
            FROM card_variants 
            ORDER BY rarity_level
        """)
        
        return cursor.fetchall()

def get_variant_by_name(variant_name):
    """Változat lekérése név alapján"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, color_code, rarity_level, description
            FROM card_variants 
            WHERE name = ?
        """, (variant_name,))
        
        return cursor.fetchone()

# =================== FELHASZNÁLÓ KÁRTYÁK FUNKCIÓK ===================

def add_user_card(user_id, base_card_id, variant_id, status='owned', price=None, condition='Jó', notes=''):
    """Kártya hozzáadása felhasználóhoz - JAVÍTOTT"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                cursor.execute("""
                    INSERT INTO user_cards (user_id, base_card_id, variant_id, status, price, condition, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, base_card_id, variant_id, status, price, condition, notes))
                
                # Log activity ugyanabban a tranzakcióban
                cursor.execute("""
                    INSERT INTO activity_log (user_id, action, description)
                    VALUES (?, ?, ?)
                """, (user_id, "card_added", f"Kártya hozzáadva: {status}"))
                
                conn.commit()
                return True, "Kártya sikeresen hozzáadva!"
                
            except:
                conn.rollback()
                raise
                
    except sqlite3.IntegrityError:
        return False, "Ez a kártya már megvan nálad ebben a változatban!"

def update_user_card_status(user_card_id, status, price=None):
    """Felhasználó kártya státuszának frissítése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_cards 
            SET status = ?, price = ?
            WHERE id = ?
        """, (status, price, user_card_id))
        
        conn.commit()

def get_user_cards(user_id, status=None, series_id=None):
    """Felhasználó kártyáinak lekérése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        sql = """
            SELECT uc.id, uc.status, uc.price, uc.condition, uc.notes, uc.added_at,
                   bc.card_number, bc.player_name, bc.team, bc.position,
                   cv.name as variant_name, cv.color_code, cv.rarity_level,
                   s.name as series_name, s.year
            FROM user_cards uc
            JOIN base_cards bc ON uc.base_card_id = bc.id
            JOIN card_variants cv ON uc.variant_id = cv.id
            JOIN series s ON bc.series_id = s.id
            WHERE uc.user_id = ?
        """
        params = [user_id]
        
        if status:
            sql += " AND uc.status = ?"
            params.append(status)
        
        if series_id:
            sql += " AND bc.series_id = ?"
            params.append(series_id)
        
        sql += " ORDER BY s.name, bc.card_number, cv.rarity_level"
        
        cursor.execute(sql, params)
        return cursor.fetchall()

def delete_user_card(user_card_id, user_id):
    """Felhasználó kártya törlése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM user_cards 
            WHERE id = ? AND user_id = ?
        """, (user_card_id, user_id))
        
        conn.commit()

# =================== KÍVÁNSÁGLISTA FUNKCIÓK ===================

def add_to_wishlist(user_id, base_card_id, variant_id, max_price=None, priority=1, notes=""):
    """Kártya hozzáadása kívánságlistához - JAVÍTOTT"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                cursor.execute("""
                    INSERT INTO wishlists (user_id, base_card_id, variant_id, max_price, priority, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, base_card_id, variant_id, max_price, priority, notes))
                
                cursor.execute("""
                    INSERT INTO activity_log (user_id, action, description)
                    VALUES (?, ?, ?)
                """, (user_id, "wishlist_added", "Kártya hozzáadva a kívánságlistához"))
                
                conn.commit()
                return True, "Kártya hozzáadva a kívánságlistához!"
                
            except:
                conn.rollback()
                raise
                
    except sqlite3.IntegrityError:
        return False, "Ez a kártya már a kívánságlistádon van!"

def get_user_wishlist(user_id):
    """Felhasználó kívánságlistájának lekérése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT w.id, w.max_price, w.priority, w.notes, w.added_at,
                   bc.card_number, bc.player_name, bc.team,
                   cv.name as variant_name, cv.color_code,
                   s.name as series_name, s.year
            FROM wishlists w
            JOIN base_cards bc ON w.base_card_id = bc.id
            JOIN card_variants cv ON w.variant_id = cv.id
            JOIN series s ON bc.series_id = s.id
            WHERE w.user_id = ?
            ORDER BY w.priority DESC, w.added_at DESC
        """, (user_id,))
        
        return cursor.fetchall()

# =================== MATCHMAKING FUNKCIÓK ===================

def find_potential_matches(user_id, limit=50):
    """Fejlett matchmaking algoritmus rangsorolással"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Komplex lekérdezés rangsorolással
        cursor.execute("""
            WITH card_demand AS (
                SELECT base_card_id, variant_id, COUNT(*) as demand_count
                FROM wishlists
                GROUP BY base_card_id, variant_id
            ),
            card_supply AS (
                SELECT base_card_id, variant_id, COUNT(*) as supply_count
                FROM user_cards
                WHERE status IN ('trade', 'sell')
                GROUP BY base_card_id, variant_id
            ),
            user_wishlist_priority AS (
                SELECT base_card_id, variant_id, priority, max_price
                FROM wishlists
                WHERE user_id = ?
            )
            
            SELECT DISTINCT
                uc.id as user_card_id,
                uc.status,
                uc.price,
                uc.condition,
                uc.added_at,
                bc.card_number,
                bc.player_name,
                bc.team,
                cv.name as variant_name,
                cv.color_code,
                cv.rarity_level,
                s.name as series_name,
                s.year,
                u.username as owner,
                uwp.priority as user_priority,
                uwp.max_price as user_max_price,
                COALESCE(cd.demand_count, 0) as demand,
                COALESCE(cs.supply_count, 0) as supply,
                
                (
                    (5 - COALESCE(uwp.priority, 3)) * 10 +
                        cv.rarity_level * 5 +
                        CASE 
                            WHEN COALESCE(cs.supply_count, 0) = 0 THEN 30
                            WHEN COALESCE(cs.supply_count, 0) = 1 THEN 25
                            WHEN COALESCE(cs.supply_count, 0) = 2 THEN 20
                            WHEN COALESCE(cs.supply_count, 0) <= 5 THEN 15
                            ELSE CASE WHEN (10 - cs.supply_count) > 0 THEN (10 - cs.supply_count) ELSE 0 END
                        END +
                        CASE 
                            WHEN COALESCE(cd.demand_count, 0) * 3 < 20 THEN COALESCE(cd.demand_count, 0) * 3 
                            ELSE 20 
                        END +
                        CASE 
                            WHEN uc.status = 'trade' THEN 15
                            WHEN uc.status = 'sell' AND uwp.max_price IS NULL THEN 10
                            WHEN uc.status = 'sell' AND uc.price <= uwp.max_price THEN 15
                            WHEN uc.status = 'sell' AND uc.price <= uwp.max_price * 1.1 THEN 10
                            WHEN uc.status = 'sell' AND uc.price <= uwp.max_price * 1.2 THEN 5
                            ELSE 0
                        END +
                        CASE 
                            WHEN uc.added_at >= datetime('now', '-1 day') THEN 10
                            WHEN uc.added_at >= datetime('now', '-3 days') THEN 7
                            WHEN uc.added_at >= datetime('now', '-7 days') THEN 5
                            WHEN uc.added_at >= datetime('now', '-30 days') THEN 2
                            ELSE 0
                        END
                ) as match_score
                
            FROM user_cards uc
            JOIN base_cards bc ON uc.base_card_id = bc.id
            JOIN card_variants cv ON uc.variant_id = cv.id
            JOIN series s ON bc.series_id = s.id
            JOIN users u ON uc.user_id = u.id
            JOIN user_wishlist_priority uwp ON uc.base_card_id = uwp.base_card_id 
                AND uc.variant_id = uwp.variant_id
            LEFT JOIN card_demand cd ON uc.base_card_id = cd.base_card_id 
                AND uc.variant_id = cd.variant_id
            LEFT JOIN card_supply cs ON uc.base_card_id = cs.base_card_id 
                AND uc.variant_id = cs.variant_id
                
            WHERE uc.user_id != ?
            AND uc.status IN ('trade', 'sell')
            
            ORDER BY match_score DESC, demand DESC, cv.rarity_level DESC
            LIMIT ?
        """, (user_id, user_id, limit))
        
        matches = []
        for row in cursor.fetchall():
            match_data = {
                'user_card_id': row[0],
                'status': row[1],
                'price': row[2],
                'condition': row[3],
                'added_at': row[4],
                'card_number': row[5],
                'player_name': row[6],
                'team': row[7],
                'variant_name': row[8],
                'color_code': row[9],
                'rarity_level': row[10],
                'series_name': row[11],
                'series_year': row[12],
                'owner': row[13],
                'user_priority': row[14],
                'user_max_price': row[15],
                'demand': row[16],
                'supply': row[17],
                'match_score': row[18],
                'demand_supply_ratio': row[16] / max(row[17], 1),
                'is_affordable': True if row[1] == 'trade' else (
                    row[15] is None or row[2] is None or row[2] <= row[15]
                ),
                'rarity_text': get_rarity_text(row[10]),
                'priority_text': get_priority_text(row[14]),
                'days_since_added': (datetime.now() - datetime.fromisoformat(row[4])).days if row[4] else 999
            }
            
            matches.append(match_data)
        
        return matches

def get_rarity_text(rarity_level):
    """Ritkasági szint szöveges megfelelője"""
    rarity_map = {
        1: "🟢 Gyakori",
        2: "🔵 Ritka", 
        3: "🟣 Különleges",
        4: "🔴 Nagyon ritka",
        5: "🟡 Legendás",
        6: "🔥 Epikus"
    }
    return rarity_map.get(rarity_level, "❓ Ismeretlen")

def get_priority_text(priority):
    """Prioritás szöveges megfelelője"""
    priority_map = {
        1: "🔴 Alacsony",
        2: "🟡 Közepes", 
        3: "🟠 Magas",
        4: "🔥 Sürgős"
    }
    return priority_map.get(priority, "❓ Nincs megadva")

# További függvények ugyanazok maradnak, csak használják az új get_db_connection() context managert...

# =================== AKTIVITÁS LOG ===================

def log_activity(user_id, action, description):
    """Aktivitás naplózása - JAVÍTOTT önálló verzió"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO activity_log (user_id, action, description)
                VALUES (?, ?, ?)
            """, (user_id, action, description))
            
            conn.commit()
    except Exception as e:
        # Hiba esetén csak logoljuk, ne állítsuk le a folyamatot
        print(f"Log activity error: {e}")
        pass

def get_user_activity(user_id, limit=10):
    """Felhasználó aktivitásának lekérése"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT action, description, created_at
            FROM activity_log
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        return cursor.fetchall()

# =================== TESZTADATOK ===================

def add_sample_data():
    """Tesztadatok hozzáadása - JAVÍTOTT"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Ellenőrizzük, hogy van-e már adat
        cursor.execute("SELECT COUNT(*) FROM series")
        series_count = cursor.fetchone()[0]
        
        if series_count == 0:
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Minta sorozatok
                sample_series = [
                    ("FIFA 2023", 2023, "Futball", "A legnépszerűbb futball kártyák"),
                    ("NBA 2023-24", 2023, "Kosárlabda", "Amerikai kosárlabda sztárok"),
                    ("Formula 1 2023", 2023, "Formula 1", "F1 pilóták és csapatok")
                ]
                
                for series_data in sample_series:
                    cursor.execute("""
                        INSERT INTO series (name, year, sport, description)
                        VALUES (?, ?, ?, ?)
                    """, series_data)
                    
                    series_id = cursor.lastrowid
                    
                    # Minta kártyák minden sorozathoz
                    if "FIFA" in series_data[0]:
                        sample_players = [
                            (1, "Lionel Messi", "PSG", "RW"),
                            (2, "Cristiano Ronaldo", "Al Nassr", "ST"),
                            (3, "Kevin De Bruyne", "Man City", "CM"),
                            (4, "Erling Haaland", "Man City", "ST"),
                            (5, "Kylian Mbappé", "PSG", "LW")
                        ]
                    elif "NBA" in series_data[0]:
                        sample_players = [
                            (1, "LeBron James", "Lakers", "SF"),
                            (2, "Stephen Curry", "Warriors", "PG"),
                            (3, "Kevin Durant", "Suns", "SF"),
                            (4, "Giannis Antetokounmpo", "Bucks", "PF"),
                            (5, "Luka Dončić", "Mavericks", "PG")
                        ]
                    else:  # F1
                        sample_players = [
                            (1, "Max Verstappen", "Red Bull", "Driver"),
                            (2, "Lewis Hamilton", "Mercedes", "Driver"),
                            (3, "Charles Leclerc", "Ferrari", "Driver"),
                            (4, "Sergio Pérez", "Red Bull", "Driver"),
                            (5, "Carlos Sainz", "Ferrari", "Driver")
                        ]
                    
                    for player in sample_players:
                        cursor.execute("""
                            INSERT INTO base_cards (series_id, card_number, player_name, team, position)
                            VALUES (?, ?, ?, ?, ?)
                        """, (series_id, player[0], player[1], player[2], player[3]))
                
                conn.commit()
                
            except:
                conn.rollback()
                raise

# =================== ÜZENET FUNKCIÓK maradnak változatlanok ===================
# ... (a többi függvény ugyanaz marad, csak használja az új get_db_connection()-t)