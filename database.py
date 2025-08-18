import sqlite3
import hashlib
from datetime import datetime
import streamlit as st

DATABASE_NAME = 'cards_platform.db'

def get_connection():
    """Adatbázis kapcsolat létrehozása"""
    return sqlite3.connect(DATABASE_NAME)

def init_database():
    """Adatbázis táblák inicializálása"""
    conn = get_connection()
    cursor = conn.cursor()
    
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
    
    # Alapkártyák tábla (1-400 minden sorozatban)
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
    
    # Kártya változatok (base, silver, pink, red, blue, epic)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color_code TEXT,
            rarity_level INTEGER DEFAULT 1,
            description TEXT
        )
    """)
    
    # Felhasználó kártyái (minden kártya + változat kombináció)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            base_card_id INTEGER NOT NULL,
            variant_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'owned', -- 'owned', 'trade', 'sell'
            price DECIMAL(10,2) NULL, -- csak ha status = 'sell'
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
            related_card_id INTEGER, -- user_cards.id
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
    conn.close()

# =================== FELHASZNÁLÓ FUNKCIÓK ===================

def hash_password(password):
    """Jelszó hashelése"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, email, password):
    """Új felhasználó létrehozása"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (username, email, password_hash))
        
        user_id = cursor.lastrowid
        
        # Aktivitás log
        log_activity(user_id, "user_registered", "Felhasználó regisztrált")
        
        conn.commit()
        conn.close()
        return True, "Sikeres regisztráció!"
        
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Ez a felhasználónév már foglalt!"
        elif "email" in str(e):
            return False, "Ez az email cím már regisztrált!"
        else:
            return False, "Hiba történt a regisztráció során!"

def authenticate_user(username, password):
    """Felhasználó hitelesítése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    
    cursor.execute("""
        SELECT id, username, email FROM users 
        WHERE username = ? AND password_hash = ?
    """, (username, password_hash))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return True, {"id": user[0], "username": user[1], "email": user[2]}
    else:
        return False, None

def get_all_users():
    """Összes felhasználó lekérése (üzenetküldéshez)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username FROM users ORDER BY username")
    users = cursor.fetchall()
    conn.close()
    
    return users

# =================== SOROZAT FUNKCIÓK ===================

def add_series(name, year=None, sport="", description=""):
    """Új sorozat hozzáadása"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO series (name, year, sport, description)
            VALUES (?, ?, ?, ?)
        """, (name, year, sport, description))
        
        series_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return True, series_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Ez a sorozat már létezik!"

def get_all_series():
    """Összes sorozat lekérése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, year, sport, total_cards, description
        FROM series 
        ORDER BY year DESC, name
    """)
    
    series = cursor.fetchall()
    conn.close()
    
    return series

def get_series_by_id(series_id):
    """Sorozat lekérése ID alapján"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, year, sport, total_cards, description
        FROM series 
        WHERE id = ?
    """, (series_id,))
    
    series = cursor.fetchone()
    conn.close()
    
    return series

# =================== ALAPKÁRTYA FUNKCIÓK ===================

def add_base_card(series_id, card_number, player_name, team="", position="", description=""):
    """Alapkártya hozzáadása sorozathoz"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO base_cards (series_id, card_number, player_name, team, position, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (series_id, card_number, player_name, team, position, description))
        
        card_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return True, card_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Ez a kártya már létezik ebben a sorozatban!"

def get_base_cards_by_series(series_id):
    """Sorozat alapkártyáinak lekérése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, card_number, player_name, team, position, description
        FROM base_cards 
        WHERE series_id = ?
        ORDER BY card_number
    """, (series_id,))
    
    cards = cursor.fetchall()
    conn.close()
    
    return cards

def search_base_cards(query="", series_id=None):
    """Alapkártyák keresése"""
    conn = get_connection()
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
    cards = cursor.fetchall()
    conn.close()
    
    return cards

# =================== KÁRTYA VÁLTOZAT FUNKCIÓK ===================

def get_all_variants():
    """Összes kártya változat lekérése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, color_code, rarity_level, description
        FROM card_variants 
        ORDER BY rarity_level
    """)
    
    variants = cursor.fetchall()
    conn.close()
    
    return variants

def get_variant_by_name(variant_name):
    """Változat lekérése név alapján"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, color_code, rarity_level, description
        FROM card_variants 
        WHERE name = ?
    """, (variant_name,))
    
    variant = cursor.fetchone()
    conn.close()
    
    return variant

# =================== FELHASZNÁLÓ KÁRTYÁK FUNKCIÓK ===================

def add_user_card(user_id, base_card_id, variant_id, status='owned', price=None, condition='Jó', notes=''):
    """Kártya hozzáadása felhasználóhoz"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO user_cards (user_id, base_card_id, variant_id, status, price, condition, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, base_card_id, variant_id, status, price, condition, notes))
        
        conn.commit()
        conn.close()
        
        log_activity(user_id, "card_added", f"Kártya hozzáadva: {status}")
        return True, "Kártya sikeresen hozzáadva!"
        
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Ez a kártya már megvan nálad ebben a változatban!"

def update_user_card_status(user_card_id, status, price=None):
    """Felhasználó kártya státuszának frissítése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE user_cards 
        SET status = ?, price = ?
        WHERE id = ?
    """, (status, price, user_card_id))
    
    conn.commit()
    conn.close()

def get_user_cards(user_id, status=None, series_id=None):
    """Felhasználó kártyáinak lekérése"""
    conn = get_connection()
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
    cards = cursor.fetchall()
    conn.close()
    
    return cards

def delete_user_card(user_card_id, user_id):
    """Felhasználó kártya törlése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM user_cards 
        WHERE id = ? AND user_id = ?
    """, (user_card_id, user_id))
    
    conn.commit()
    conn.close()

# =================== KÍVÁNSÁGLISTA FUNKCIÓK ===================

def add_to_wishlist(user_id, base_card_id, variant_id, max_price=None, priority=1, notes=""):
    """Kártya hozzáadása kívánságlistához"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO wishlists (user_id, base_card_id, variant_id, max_price, priority, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, base_card_id, variant_id, max_price, priority, notes))
        
        conn.commit()
        conn.close()
        
        log_activity(user_id, "wishlist_added", "Kártya hozzáadva a kívánságlistához")
        return True, "Kártya hozzáadva a kívánságlistához!"
        
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Ez a kártya már a kívánságlistádon van!"

def get_user_wishlist(user_id):
    """Felhasználó kívánságlistájának lekérése"""
    conn = get_connection()
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
    
    wishlist = cursor.fetchall()
    conn.close()
    
    return wishlist

# =================== MATCHMAKING FUNKCIÓK ===================

def find_potential_matches(user_id, limit=50):
    """Fejlett matchmaking algoritmus rangsorolással"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Komplex lekérdezés rangsorolással
    cursor.execute("""
        WITH card_demand AS (
            -- Minden kártya kereslettsége
            SELECT base_card_id, variant_id, COUNT(*) as demand_count
            FROM wishlists
            GROUP BY base_card_id, variant_id
        ),
        card_supply AS (
            -- Minden kártya kínálata
            SELECT base_card_id, variant_id, COUNT(*) as supply_count
            FROM user_cards
            WHERE status IN ('trade', 'sell')
            GROUP BY base_card_id, variant_id
        ),
        user_wishlist_priority AS (
            -- Felhasználó prioritásai
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
            
            -- Rangsorolási pontszám kalkuláció
            (
                -- Alappontok kívánságlista prioritás alapján (1-4 -> 40-10 pont)
                (5 - COALESCE(uwp.priority, 3)) * 10 +
                
                -- Ritkasági bónusz (1-6 -> 0-25 pont)
                cv.rarity_level * 5 +
                
                -- Demand/Supply arány bónusz (max 30 pont)
                CASE 
                    WHEN COALESCE(cs.supply_count, 0) = 0 THEN 30
                    WHEN COALESCE(cs.supply_count, 0) = 1 THEN 25
                    WHEN COALESCE(cs.supply_count, 0) = 2 THEN 20
                    WHEN COALESCE(cs.supply_count, 0) <= 5 THEN 15
                    ELSE GREATEST(0, 10 - cs.supply_count)
                END +
                
                -- Kereslet bónusz (max 20 pont)
                LEAST(COALESCE(cd.demand_count, 0) * 3, 20) +
                
                -- Ár megfelelőség bónusz eladáshoz (max 15 pont)
                CASE 
                    WHEN uc.status = 'trade' THEN 15
                    WHEN uc.status = 'sell' AND uwp.max_price IS NULL THEN 10
                    WHEN uc.status = 'sell' AND uc.price <= uwp.max_price THEN 15
                    WHEN uc.status = 'sell' AND uc.price <= uwp.max_price * 1.1 THEN 10
                    WHEN uc.status = 'sell' AND uc.price <= uwp.max_price * 1.2 THEN 5
                    ELSE 0
                END +
                
                -- Frissesség bónusz (max 10 pont)
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
            
            # Kalkulált értékek
            'demand_supply_ratio': row[16] / max(row[17], 1),
            'is_affordable': True if row[1] == 'trade' else (
                row[15] is None or row[2] is None or row[2] <= row[15]
            ),
            'rarity_text': get_rarity_text(row[10]),
            'priority_text': get_priority_text(row[14]),
            'days_since_added': (datetime.now() - datetime.fromisoformat(row[4])).days if row[4] else 999
        }
        
        matches.append(match_data)
    
    conn.close()
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

def find_reverse_matches(user_id, limit=30):
    """Megfordított matchmaking - Amit kínálok és mások keresnek"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        WITH interested_users AS (
            -- Kik keresik amit én kínálok
            SELECT 
                w.user_id as interested_user_id,
                w.base_card_id,
                w.variant_id,
                w.priority,
                w.max_price,
                u.username,
                COUNT(*) OVER (PARTITION BY w.base_card_id, w.variant_id) as total_demand
            FROM wishlists w
            JOIN users u ON w.user_id = u.id
            WHERE (w.base_card_id, w.variant_id) IN (
                SELECT base_card_id, variant_id 
                FROM user_cards 
                WHERE user_id = ? AND status IN ('trade', 'sell')
            )
            AND w.user_id != ?
        )
        
        SELECT DISTINCT
            uc.id as my_card_id,
            uc.status,
            uc.price,
            bc.card_number,
            bc.player_name,
            cv.name as variant_name,
            cv.color_code,
            cv.rarity_level,
            s.name as series_name,
            iu.interested_user_id,
            iu.username as interested_user,
            iu.priority as their_priority,
            iu.max_price as their_max_price,
            iu.total_demand,
            
            -- Érdeklődés pontszám
            (
                iu.priority * 10 +  -- Mennyire akarják (10-40 pont)
                cv.rarity_level * 3 +  -- Ritkasági bónusz
                iu.total_demand * 2  -- Mennyi ember akarja
            ) as interest_score
            
        FROM user_cards uc
        JOIN base_cards bc ON uc.base_card_id = bc.id
        JOIN card_variants cv ON uc.variant_id = cv.id
        JOIN series s ON bc.series_id = s.id
        JOIN interested_users iu ON uc.base_card_id = iu.base_card_id 
            AND uc.variant_id = iu.variant_id
            
        WHERE uc.user_id = ?
        AND uc.status IN ('trade', 'sell')
        AND (
            uc.status = 'trade' OR
            (uc.status = 'sell' AND (iu.max_price IS NULL OR uc.price <= iu.max_price))
        )
        
        ORDER BY interest_score DESC, iu.total_demand DESC
        LIMIT ?
    """, (user_id, user_id, user_id, limit))
    
    reverse_matches = []
    for row in cursor.fetchall():
        reverse_matches.append({
            'my_card_id': row[0],
            'status': row[1], 
            'price': row[2],
            'card_number': row[3],
            'player_name': row[4],
            'variant_name': row[5],
            'color_code': row[6],
            'rarity_level': row[7],
            'series_name': row[8],
            'interested_user_id': row[9],
            'interested_user': row[10],
            'their_priority': row[11],
            'their_max_price': row[12],
            'total_demand': row[13],
            'interest_score': row[14]
        })
    
    conn.close()
    return reverse_matches

def get_market_insights(user_id):
    """Piaci insights a felhasználó gyűjteményéhez"""
    conn = get_connection()
    cursor = conn.cursor()
    
    insights = {}
    
    # Legnépszerűbb kártyáim (amit sokan keresnek)
    cursor.execute("""
        SELECT 
            bc.card_number,
            bc.player_name,
            cv.name as variant_name,
            cv.color_code,
            s.name as series_name,
            COUNT(w.id) as demand_count,
            uc.status,
            uc.price
        FROM user_cards uc
        JOIN base_cards bc ON uc.base_card_id = bc.id
        JOIN card_variants cv ON uc.variant_id = cv.id
        JOIN series s ON bc.series_id = s.id
        LEFT JOIN wishlists w ON uc.base_card_id = w.base_card_id 
            AND uc.variant_id = w.variant_id
        WHERE uc.user_id = ?
        GROUP BY uc.id
        HAVING demand_count > 0
        ORDER BY demand_count DESC, cv.rarity_level DESC
        LIMIT 10
    """, (user_id,))
    
    insights['most_wanted_cards'] = cursor.fetchall()
    
    # Legritkább kártyáim
    cursor.execute("""
        SELECT 
            bc.card_number,
            bc.player_name,
            cv.name as variant_name,
            cv.color_code,
            s.name as series_name,
            cv.rarity_level,
            uc.status,
            (SELECT COUNT(*) FROM user_cards uc2 
             WHERE uc2.base_card_id = uc.base_card_id 
             AND uc2.variant_id = uc.variant_id) as total_copies
        FROM user_cards uc
        JOIN base_cards bc ON uc.base_card_id = bc.id
        JOIN card_variants cv ON uc.variant_id = cv.id
        JOIN series s ON bc.series_id = s.id
        WHERE uc.user_id = ?
        ORDER BY cv.rarity_level DESC, total_copies ASC
        LIMIT 10
    """, (user_id,))
    
    insights['rarest_cards'] = cursor.fetchall()
    
    # Ár ajánlások eladásra kínált kártyákhoz
    cursor.execute("""
        SELECT 
            uc.id,
            bc.card_number,
            bc.player_name,
            cv.name as variant_name,
            uc.price as my_price,
            AVG(uc2.price) as market_avg,
            MIN(uc2.price) as market_min,
            MAX(uc2.price) as market_max,
            COUNT(uc2.id) as market_samples
        FROM user_cards uc
        JOIN base_cards bc ON uc.base_card_id = bc.id
        JOIN card_variants cv ON uc.variant_id = cv.id
        LEFT JOIN user_cards uc2 ON uc.base_card_id = uc2.base_card_id 
            AND uc.variant_id = uc2.variant_id
            AND uc2.status = 'sell' 
            AND uc2.price IS NOT NULL
            AND uc2.user_id != ?
        WHERE uc.user_id = ? AND uc.status = 'sell'
        GROUP BY uc.id
        HAVING market_samples > 0
    """, (user_id, user_id))
    
    insights['price_comparisons'] = cursor.fetchall()
    
    conn.close()
    return insights

# =================== ÜZENET FUNKCIÓK ===================

def send_message(sender_id, receiver_id, subject, content, parent_message_id=None, related_card_id=None):
    """Üzenet küldése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO messages (sender_id, receiver_id, subject, content, parent_message_id, related_card_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sender_id, receiver_id, subject, content, parent_message_id, related_card_id))
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Aktivitás log
        log_activity(sender_id, "message_sent", f"Üzenet küldve: {subject[:50]}")
        
        return True, message_id
    except Exception as e:
        conn.close()
        return False, str(e)

def get_inbox_messages(user_id, limit=50):
    """Beérkezett üzenetek lekérése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            m.id,
            m.sender_id,
            m.subject,
            m.content,
            m.sent_at,
            m.is_read,
            m.parent_message_id,
            m.related_card_id,
            u.username as sender_name,
            -- Kapcsolódó kártya adatok ha van
            CASE WHEN m.related_card_id IS NOT NULL THEN
                bc.card_number || ' ' || bc.player_name || ' (' || cv.name || ')'
            ELSE NULL END as related_card_info,
            -- Válasz darabszám
            (SELECT COUNT(*) FROM messages m2 WHERE m2.parent_message_id = m.id) as reply_count
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        LEFT JOIN user_cards uc ON m.related_card_id = uc.id
        LEFT JOIN base_cards bc ON uc.base_card_id = bc.id
        LEFT JOIN card_variants cv ON uc.variant_id = cv.id
        WHERE m.receiver_id = ? AND m.parent_message_id IS NULL
        ORDER BY m.sent_at DESC
        LIMIT ?
    """, (user_id, limit))
    
    messages = cursor.fetchall()
    conn.close()
    
    return messages

def get_sent_messages(user_id, limit=50):
    """Elküldött üzenetek lekérése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            m.id,
            m.receiver_id,
            m.subject,
            m.content,
            m.sent_at,
            m.is_read,
            m.parent_message_id,
            m.related_card_id,
            u.username as receiver_name,
            -- Kapcsolódó kártya adatok ha van
            CASE WHEN m.related_card_id IS NOT NULL THEN
                bc.card_number || ' ' || bc.player_name || ' (' || cv.name || ')'
            ELSE NULL END as related_card_info,
            -- Válasz darabszám
            (SELECT COUNT(*) FROM messages m2 WHERE m2.parent_message_id = m.id) as reply_count
        FROM messages m
        JOIN users u ON m.receiver_id = u.id
        LEFT JOIN user_cards uc ON m.related_card_id = uc.id
        LEFT JOIN base_cards bc ON uc.base_card_id = bc.id
        LEFT JOIN card_variants cv ON uc.variant_id = cv.id
        WHERE m.sender_id = ? AND m.parent_message_id IS NULL
        ORDER BY m.sent_at DESC
        LIMIT ?
    """, (user_id, limit))
    
    messages = cursor.fetchall()
    conn.close()
    
    return messages

def get_message_thread(message_id, user_id):
    """Üzenet szál lekérése (eredeti + válaszok)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Megkeressük az eredeti üzenetet
    cursor.execute("""
        SELECT parent_message_id FROM messages WHERE id = ?
    """, (message_id,))
    
    result = cursor.fetchone()
    if result and result[0]:
        # Ha ez egy válasz, akkor az eredeti üzenet ID-ját használjuk
        root_message_id = result[0]
    else:
        # Ez az eredeti üzenet
        root_message_id = message_id
    
    # Lekérjük az eredeti üzenetet + összes válasz
    cursor.execute("""
        SELECT 
            m.id,
            m.sender_id,
            m.receiver_id,
            m.subject,
            m.content,
            m.sent_at,
            m.is_read,
            m.parent_message_id,
            m.related_card_id,
            u.username as sender_name,
            CASE WHEN m.related_card_id IS NOT NULL THEN
                bc.card_number || ' ' || bc.player_name || ' (' || cv.name || ')'
            ELSE NULL END as related_card_info
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        LEFT JOIN user_cards uc ON m.related_card_id = uc.id
        LEFT JOIN base_cards bc ON uc.base_card_id = bc.id
        LEFT JOIN card_variants cv ON uc.variant_id = cv.id
        WHERE m.id = ? OR m.parent_message_id = ?
        AND (m.sender_id = ? OR m.receiver_id = ?)
        ORDER BY m.sent_at ASC
    """, (root_message_id, root_message_id, user_id, user_id))
    
    thread = cursor.fetchall()
    conn.close()
    
    return thread

def mark_message_as_read(message_id, user_id):
    """Üzenet olvasottnak jelölése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE messages 
        SET is_read = TRUE 
        WHERE id = ? AND receiver_id = ?
    """, (message_id, user_id))
    
    conn.commit()
    conn.close()

def delete_message(message_id, user_id):
    """Üzenet törlése (csak saját üzenetek)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Ellenőrizzük, hogy a felhasználó tulajdonosa-e az üzenetnek
    cursor.execute("""
        DELETE FROM messages 
        WHERE id = ? AND (sender_id = ? OR receiver_id = ?)
    """, (message_id, user_id, user_id))
    
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return deleted_count > 0

def get_unread_message_count(user_id):
    """Olvasatlan üzenetek száma"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE receiver_id = ? AND is_read = FALSE
    """, (user_id,))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count

def search_users_for_messaging(query="", exclude_user_id=None):
    """Felhasználók keresése üzenetküldéshez"""
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT 
            u.id,
            u.username,
            u.created_at,
            -- Kártyák száma
            (SELECT COUNT(*) FROM user_cards uc WHERE uc.user_id = u.id) as card_count,
            -- Utolsó aktivitás
            (SELECT MAX(created_at) FROM activity_log al WHERE al.user_id = u.id) as last_activity
        FROM users u
        WHERE 1=1
    """
    params = []
    
    if exclude_user_id:
        sql += " AND u.id != ?"
        params.append(exclude_user_id)
    
    if query:
        sql += " AND u.username LIKE ?"
        params.append(f"%{query}%")
    
    sql += " ORDER BY u.username LIMIT 20"
    
    cursor.execute(sql, params)
    users = cursor.fetchall()
    conn.close()
    
    return users

def get_conversation_partners(user_id, limit=10):
    """Beszélgetőpartnerek lekérése (akikkel volt üzenetváltás)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT
            CASE 
                WHEN m.sender_id = ? THEN m.receiver_id
                ELSE m.sender_id
            END as partner_id,
            CASE 
                WHEN m.sender_id = ? THEN receiver.username
                ELSE sender.username
            END as partner_name,
            MAX(m.sent_at) as last_message_time,
            COUNT(m.id) as message_count,
            SUM(CASE WHEN m.receiver_id = ? AND m.is_read = FALSE THEN 1 ELSE 0 END) as unread_count
        FROM messages m
        LEFT JOIN users sender ON m.sender_id = sender.id
        LEFT JOIN users receiver ON m.receiver_id = receiver.id
        WHERE m.sender_id = ? OR m.receiver_id = ?
        GROUP BY partner_id, partner_name
        ORDER BY last_message_time DESC
        LIMIT ?
    """, (user_id, user_id, user_id, user_id, user_id, limit))
    
    partners = cursor.fetchall()
    conn.close()
    
    return partners

def create_card_inquiry_message(inquirer_id, card_owner_name, user_card_id, card_data, inquiry_type="general"):
    """Kártya érdeklődés üzenet sablon létrehozása (egyszerűsített verzió)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Érdeklődő neve
    cursor.execute("SELECT username FROM users WHERE id = ?", (inquirer_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None, "Felhasználó nem található"
    
    inquirer_name = result[0]
    conn.close()
    
    # Sablon típus szerint
    if inquiry_type == "buy":
        subject = f"Vételi érdeklődés: {card_data['player_name']} ({card_data['variant_name']})"
        content = f"""Szia {card_owner_name}!

Érdeklődnék a következő kártyád iránt vásárlás céljából:

🃏 Kártya: #{card_data['card_number']:03d} {card_data['player_name']}
📚 Sorozat: {card_data['series_name']}
💎 Változat: {card_data['variant_name']}
🏷️ Állapot: {card_data['condition']}
💰 Jelenlegi ár: {format_price(card_data['price']) if card_data['price'] else 'Nincs megadva'}

Eladásra szánod? Ha igen, tudnánk egyeztetni az árról és a részletekről?

Üdvözlettel,
{inquirer_name}"""

    elif inquiry_type == "trade":
        subject = f"Csere érdeklődés: {card_data['player_name']} ({card_data['variant_name']})"
        content = f"""Szia {card_owner_name}!

Érdeklődnék a következő kártyád iránt cserére:

🃏 Kártya: #{card_data['card_number']:03d} {card_data['player_name']}
📚 Sorozat: {card_data['series_name']}
💎 Változat: {card_data['variant_name']}
🏷️ Állapot: {card_data['condition']}

Van valami konkrét kártya, amit keresel cserébe? Szívesen megnézem a gyűjteményem, hátha találunk valami érdekes cserét!

Üdvözlettel,
{inquirer_name}"""

    else:  # general
        subject = f"Érdeklődés: {card_data['player_name']} ({card_data['variant_name']})"
        content = f"""Szia {card_owner_name}!

Láttam, hogy nálad van ez a kártya:

🃏 Kártya: #{card_data['card_number']:03d} {card_data['player_name']}
📚 Sorozat: {card_data['series_name']}
💎 Változat: {card_data['variant_name']}
🏷️ Állapot: {card_data['condition']}

Érdeklődnék, hogy szánod-e eladásra vagy cserére? Ha igen, milyen feltételekkel?

Üdvözlettel,
{inquirer_name}"""
    
    return {
        'subject': subject,
        'content': content,
        'related_card_id': user_card_id
    }, None

def get_user_id_by_name(username):
    """Felhasználó ID lekérése név alapján"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def log_activity(user_id, action, description):
    """Aktivitás naplózása"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO activity_log (user_id, action, description)
        VALUES (?, ?, ?)
    """, (user_id, action, description))
    
    conn.commit()
    conn.close()

def get_user_activity(user_id, limit=10):
    """Felhasználó aktivitásának lekérése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT action, description, created_at
        FROM activity_log
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))
    
    activities = cursor.fetchall()
    conn.close()
    
    return activities

# =================== TESZTADATOK ===================

def add_sample_data():
    """Tesztadatok hozzáadása"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Ellenőrizzük, hogy van-e már adat
    cursor.execute("SELECT COUNT(*) FROM series")
    series_count = cursor.fetchone()[0]
    
    if series_count == 0:
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
            
            # Minta kártyák minden sorozathoz (első 10 kártya)
            if "FIFA" in series_data[0]:
                sample_players = [
                    (1, "Lionel Messi", "PSG", "RW"),
                    (2, "Cristiano Ronaldo", "Al Nassr", "ST"),
                    (3, "Kevin De Bruyne", "Man City", "CM"),
                    (4, "Erling Haaland", "Man City", "ST"),
                    (5, "Kylian Mbappé", "PSG", "LW"),
                    (6, "Virgil van Dijk", "Liverpool", "CB"),
                    (7, "Luka Modrić", "Real Madrid", "CM"),
                    (8, "Robert Lewandowski", "Barcelona", "ST"),
                    (9, "Mohamed Salah", "Liverpool", "RW"),
                    (10, "Neymar Jr", "Al Hilal", "LW")
                ]
            elif "NBA" in series_data[0]:
                sample_players = [
                    (1, "LeBron James", "Lakers", "SF"),
                    (2, "Stephen Curry", "Warriors", "PG"),
                    (3, "Kevin Durant", "Suns", "SF"),
                    (4, "Giannis Antetokounmpo", "Bucks", "PF"),
                    (5, "Luka Dončić", "Mavericks", "PG"),
                    (6, "Jayson Tatum", "Celtics", "SF"),
                    (7, "Joel Embiid", "76ers", "C"),
                    (8, "Nikola Jokić", "Nuggets", "C"),
                    (9, "Jimmy Butler", "Heat", "SF"),
                    (10, "Damian Lillard", "Bucks", "PG")
                ]
            else:  # F1
                sample_players = [
                    (1, "Max Verstappen", "Red Bull", "Driver"),
                    (2, "Lewis Hamilton", "Mercedes", "Driver"),
                    (3, "Charles Leclerc", "Ferrari", "Driver"),
                    (4, "Sergio Pérez", "Red Bull", "Driver"),
                    (5, "Carlos Sainz", "Ferrari", "Driver"),
                    (6, "George Russell", "Mercedes", "Driver"),
                    (7, "Lando Norris", "McLaren", "Driver"),
                    (8, "Fernando Alonso", "Aston Martin", "Driver"),
                    (9, "Oscar Piastri", "McLaren", "Driver"),
                    (10, "Lance Stroll", "Aston Martin", "Driver")
                ]
            
            for player in sample_players:
                cursor.execute("""
                    INSERT INTO base_cards (series_id, card_number, player_name, team, position)
                    VALUES (?, ?, ?, ?, ?)
                """, (series_id, player[0], player[1], player[2], player[3]))
    
    conn.commit()
    conn.close()