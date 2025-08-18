import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from database import get_connection

def get_user_stats(user_id):
    """Felhasználó statisztikáinak lekérése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Összes kártya
    cursor.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (user_id,))
    stats['total_cards'] = cursor.fetchone()[0]
    
    # Cserélni kívánt kártyák
    cursor.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ? AND status = 'trade'", (user_id,))
    stats['trade_cards'] = cursor.fetchone()[0]
    
    # Eladni kívánt kártyák
    cursor.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ? AND status = 'sell'", (user_id,))
    stats['sell_cards'] = cursor.fetchone()[0]
    
    # Csak megvan kártyák
    cursor.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ? AND status = 'owned'", (user_id,))
    stats['owned_cards'] = cursor.fetchone()[0]
    
    # Kívánságlista
    cursor.execute("SELECT COUNT(*) FROM wishlists WHERE user_id = ?", (user_id,))
    stats['wishlist_count'] = cursor.fetchone()[0]
    
    # Olvasatlan üzenetek
    cursor.execute("SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0", (user_id,))
    stats['unread_messages'] = cursor.fetchone()[0]
    
    # Sorozatok száma
    cursor.execute("""
        SELECT COUNT(DISTINCT bc.series_id) 
        FROM user_cards uc
        JOIN base_cards bc ON uc.base_card_id = bc.id
        WHERE uc.user_id = ?
    """, (user_id,))
    stats['series_count'] = cursor.fetchone()[0]
    
    # Legritkább kártyák száma (Epic)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM user_cards uc
        JOIN card_variants cv ON uc.variant_id = cv.id
        WHERE uc.user_id = ? AND cv.name = 'Epic'
    """, (user_id,))
    stats['epic_cards'] = cursor.fetchone()[0]
    
    conn.close()
    return stats

def get_recent_activity(user_id, days=7):
    """Legutóbbi aktivitás lekérése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    since_date = datetime.now() - timedelta(days=days)
    
    cursor.execute("""
        SELECT action, description, created_at
        FROM activity_log
        WHERE user_id = ? AND created_at >= ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (user_id, since_date))
    
    activities = []
    for row in cursor.fetchall():
        activities.append({
            'action': row[0],
            'description': row[1],
            'date': format_datetime(row[2])
        })
    
    conn.close()
    return activities

def find_potential_matches(user_id):
    """Fejlett potenciális matchek keresése rangsorolással"""
    from database import find_potential_matches as db_find_matches
    return db_find_matches(user_id, limit=20)

def get_match_summary(matches):
    """Match összefoglaló statisztikák"""
    if not matches:
        return {
            'total': 0,
            'trade_only': 0,
            'for_sale': 0,
            'affordable': 0,
            'high_priority': 0,
            'rare_cards': 0
        }
    
    total = len(matches)
    trade_only = len([m for m in matches if m['status'] == 'trade'])
    for_sale = len([m for m in matches if m['status'] == 'sell'])
    affordable = len([m for m in matches if m['is_affordable']])
    high_priority = len([m for m in matches if m['user_priority'] >= 3])
    rare_cards = len([m for m in matches if m['rarity_level'] >= 4])
    
    return {
        'total': total,
        'trade_only': trade_only,
        'for_sale': for_sale,
        'affordable': affordable,
        'high_priority': high_priority,
        'rare_cards': rare_cards
    }

def format_match_score(score):
    """Match pontszám formázása"""
    if score >= 80:
        return f"🔥 {score} (Kiváló!)"
    elif score >= 60:
        return f"⭐ {score} (Jó)"
    elif score >= 40:
        return f"👍 {score} (Megfelelő)"
    else:
        return f"📊 {score}"

def get_price_recommendation(current_price, market_avg, market_min, market_max, market_samples):
    """Ár ajánlás algoritmus"""
    if market_samples == 0:
        return "📊 Nincs piaci adat", "neutral"
    
    if current_price < market_min:
        return "📈 Túl alacsony - emelj árat!", "success"
    elif current_price > market_max:
        return "📉 Túl magas - csökkentsd!", "error" 
    elif current_price <= market_avg * 0.9:
        return "💰 Jó ár - gyorsan elkél!", "success"
    elif current_price >= market_avg * 1.1:
        return "⏰ Drága - lassan fogy", "warning"
    else:
        return "✅ Piaci ár - reális", "info"

def calculate_trade_value_score(my_rarity, their_rarity, my_demand, their_demand):
    """Csere értékesség kalkulátor"""
    rarity_diff = their_rarity - my_rarity
    demand_diff = their_demand - my_demand
    
    score = 50  # Alap pontszám
    
    # Ritkasági különbség
    score += rarity_diff * 10
    
    # Kereslet különbség
    score += demand_diff * 5
    
    # Értékelés
    if score >= 70:
        return score, "🔥 Nagyszerű csere!"
    elif score >= 55:
        return score, "👍 Jó csere"
    elif score >= 45:
        return score, "⚖️ Egyenértékű"
    elif score >= 30:
        return score, "👎 Rossz csere"
    else:
        return score, "💸 Nagy veszteség!"

def get_market_trend_emoji(demand, supply):
    """Piaci trend emoji"""
    if supply == 0:
        return "🔥 Nincs kínálat!"
    
    ratio = demand / supply
    
    if ratio >= 3:
        return "📈 Nagyon keresett"
    elif ratio >= 2:
        return "⬆️ Keresett"
    elif ratio >= 1:
        return "➡️ Kiegyensúlyozott"
    elif ratio >= 0.5:
        return "⬇️ Túlkínálat"
    else:
        return "📉 Alacsony kereslet"

def format_wishlist_priority_badge(priority):
    """Kívánságlista prioritás badge"""
    priority_styles = {
        4: "🔥 SÜRGŐS",
        3: "🟠 MAGAS", 
        2: "🟡 KÖZEPES",
        1: "🔴 ALACSONY"
    }
    return priority_styles.get(priority, "❓ NINCS")

def get_rarity_color_style(rarity_level):
    """Ritkasági szint színstílus"""
    colors = {
        1: "#808080",  # Base - szürke
        2: "#C0C0C0",  # Silver - ezüst
        3: "#FFC0CB",  # Pink - rózsaszín
        4: "#FF0000",  # Red - piros
        5: "#0000FF",  # Blue - kék
        6: "#FFD700"   # Epic - arany
    }
    return colors.get(rarity_level, "#000000")

def format_days_ago(days):
    """Napok óta formázás"""
    if days == 0:
        return "Ma"
    elif days == 1:
        return "Tegnap"
    elif days <= 7:
        return f"{days} napja"
    elif days <= 30:
        return f"{days//7} hete"
    else:
        return f"{days//30} hónapja"

# =================== ÜZENET FUNKCIÓK ===================

def format_message_time(sent_at):
    """Üzenet időpont formázása"""
    try:
        if isinstance(sent_at, str):
            msg_time = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
        else:
            msg_time = sent_at
        
        now = datetime.now()
        diff = now - msg_time
        
        if diff.days == 0:
            # Ma
            if diff.seconds < 3600:  # 1 óránál kevesebb
                minutes = diff.seconds // 60
                return f"{minutes} perce" if minutes > 0 else "Most"
            else:
                hours = diff.seconds // 3600
                return f"{hours} órája"
        elif diff.days == 1:
            return "Tegnap"
        elif diff.days < 7:
            return f"{diff.days} napja"
        else:
            return msg_time.strftime("%Y.%m.%d")
    except:
        return str(sent_at)

def truncate_message_content(content, max_length=100):
    """Üzenet tartalom rövidítése előnézethez"""
    if len(content) <= max_length:
        return content
    
    return content[:max_length-3] + "..."

def get_message_priority_badge(is_read, reply_count=0, related_card=None):
    """Üzenet prioritás badge"""
    badges = []
    
    if not is_read:
        badges.append("🔴 Új")
    
    if reply_count > 0:
        badges.append(f"💬 {reply_count}")
    
    if related_card:
        badges.append("🃏 Kártya")
    
    return " | ".join(badges) if badges else ""

def format_message_subject(subject, max_length=50):
    """Üzenet tárgy formázása"""
    if len(subject) <= max_length:
        return subject
    
    return subject[:max_length-3] + "..."

def get_message_type_icon(related_card_id, content):
    """Üzenet típus ikonja tartalom alapján"""
    if related_card_id:
        if "vételi" in content.lower() or "vásárol" in content.lower() or "megvesz" in content.lower():
            return "💰"
        elif "csere" in content.lower() or "cserél" in content.lower():
            return "🔄"
        else:
            return "🃏"
    else:
        return "💬"

def validate_message_content(subject, content):
    """Üzenet tartalom validálása"""
    errors = []
    
    if not subject or len(subject.strip()) < 3:
        errors.append("A tárgy legalább 3 karakter hosszú legyen!")
    
    if len(subject) > 100:
        errors.append("A tárgy maximum 100 karakter lehet!")
    
    if not content or len(content.strip()) < 10:
        errors.append("Az üzenet legalább 10 karakter hosszú legyen!")
    
    if len(content) > 2000:
        errors.append("Az üzenet maximum 2000 karakter lehet!")
    
    # Spam check - egyszerű
    spam_words = ['spam', 'reklám', 'ingyen', 'nyeremény', 'kattints ide']
    content_lower = content.lower()
    
    for spam_word in spam_words:
        if spam_word in content_lower:
            errors.append("Az üzenet spam-szerű tartalmat tartalmaz!")
            break
    
    return errors

def get_conversation_summary(messages):
    """Beszélgetés összefoglaló"""
    if not messages:
        return "Nincs üzenet"
    
    total = len(messages)
    last_message = messages[-1] if messages else None
    
    if last_message:
        last_time = format_message_time(last_message[5])  # sent_at
        return f"{total} üzenet • Utolsó: {last_time}"
    
    return f"{total} üzenet"

def create_message_thread_display(thread, current_user_id):
    """Üzenet szál megjelenítési adatai"""
    display_data = []
    
    for msg in thread:
        is_mine = msg[1] == current_user_id  # sender_id
        
        display_data.append({
            'id': msg[0],
            'sender_id': msg[1],
            'receiver_id': msg[2],
            'subject': msg[3],
            'content': msg[4],
            'sent_at': msg[5],
            'is_read': msg[6],
            'is_mine': is_mine,
            'sender_name': msg[9],
            'related_card_info': msg[10],
            'formatted_time': format_message_time(msg[5]),
            'message_icon': get_message_type_icon(msg[8], msg[4])
        })
    
    return display_data

def get_quick_reply_templates():
    """Gyors válasz sablonok"""
    return [
        "Köszönöm az érdeklődést! ",
        "Sajnos ez a kártya már nem elérhető. ",
        "Az ár még aktuális. ",
        "Szívesen megbeszéljük a részleteket. ",
        "Kérlek, írj privát üzenetet! ",
        "Bocsi, de ez a kártya nem eladó. ",
        "Érdekel a csere! Mit kínálsz? ",
        "Az ár fix, nem alkudok. "
    ]

def search_messages(user_id, query, message_type="all"):
    """Üzenetek keresése - placeholder funkció"""
    # Ezt később implementáljuk a database.py-ban
    pass

def export_messages_to_csv(messages):
    """Üzenetek exportálása CSV-be"""
    import io
    
    output = io.StringIO()
    output.write("Dátum,Feladó,Címzett,Tárgy,Tartalom,Olvasott,Kártya\n")
    
    for msg in messages:
        # CSV escape
        fields = [
            str(msg[4]),  # sent_at
            str(msg[8]),  # sender_name
            "Te" if msg[1] != msg[2] else str(msg[8]),  # receiver
            f'"{str(msg[2]).replace('"', '""')}"',  # subject
            f'"{str(msg[3]).replace('"', '""')}"',  # content
            "Igen" if msg[5] else "Nem",  # is_read
            str(msg[9]) if msg[9] else ""  # related_card_info
        ]
        
        output.write(",".join(fields) + "\n")
    
    return output.getvalue()

def format_datetime(dt_string):
    """Dátum formázása magyar formátumra"""
    try:
        if isinstance(dt_string, str):
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        else:
            dt = dt_string
        
        # Magyar hónapnevek
        months = [
            'január', 'február', 'március', 'április', 'május', 'június',
            'július', 'augusztus', 'szeptember', 'október', 'november', 'december'
        ]
        
        return f"{dt.year}. {months[dt.month-1]} {dt.day}. {dt.hour:02d}:{dt.minute:02d}"
    except:
        return str(dt_string)

def format_price(price):
    """Ár formázása"""
    if price is None:
        return "Nincs megadva"
    return f"{price:,.0f} Ft".replace(',', ' ')

def get_sports_list():
    """Sportágak listája"""
    return [
        "",  # üres opció
        "Futball",
        "Kosárlabda", 
        "Baseball",
        "Amerikai futball",
        "Jégkorong",
        "Tenisz",
        "Formula 1",
        "MotoGP",
        "Golf",
        "Boksz",
        "UFC",
        "Egyéb"
    ]

def get_status_list():
    """Kártya státusz listája"""
    return [
        ("owned", "🏠 Megvan"),
        ("trade", "🔄 Cserélnék"),
        ("sell", "💰 Eladnám")
    ]

def get_condition_list():
    """Állapot listája"""
    return [
        "Újszerű",
        "Kiváló",
        "Jó", 
        "Közepes",
        "Rossz"
    ]

def get_priority_list():
    """Prioritás listája"""
    return [
        (1, "🔴 Alacsony"),
        (2, "🟡 Közepes"),
        (3, "🟠 Magas"),
        (4, "🔥 Sürgős")
    ]

def get_variant_display(variant_name, color_code):
    """Kártya változat megjelenítése színnel"""
    return f"<span style='color: {color_code}; font-weight: bold;'>●</span> {variant_name}"

def format_card_display(card_number, player_name, variant_name, color_code, series_name=""):
    """Kártya teljes megjelenítése"""
    variant_colored = f"<span style='color: {color_code}; font-weight: bold;'>●</span> {variant_name}"
    
    if series_name:
        return f"#{card_number:03d} {player_name} ({series_name}) - {variant_colored}"
    else:
        return f"#{card_number:03d} {player_name} - {variant_colored}"

def search_users(query=""):
    """Felhasználók keresése"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if query:
        cursor.execute("""
            SELECT id, username FROM users 
            WHERE username LIKE ? 
            ORDER BY username
        """, (f"%{query}%",))
    else:
        cursor.execute("SELECT id, username FROM users ORDER BY username")
    
    users = cursor.fetchall()
    conn.close()
    
    return users

def get_popular_cards(limit=10):
    """Népszerű kártyák (legtöbbet keresett)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            bc.id,
            bc.card_number,
            bc.player_name,
            bc.team,
            s.name as series_name,
            cv.name as variant_name,
            cv.color_code,
            COUNT(w.id) as demand,
            COUNT(uc.id) as supply
        FROM base_cards bc
        JOIN series s ON bc.series_id = s.id
        JOIN card_variants cv ON cv.name = 'Base'  -- Csak Base változatokat nézzük
        LEFT JOIN wishlists w ON bc.id = w.base_card_id AND cv.id = w.variant_id
        LEFT JOIN user_cards uc ON bc.id = uc.base_card_id AND cv.id = uc.variant_id 
            AND uc.status IN ('trade', 'sell')
        GROUP BY bc.id, bc.card_number, bc.player_name, s.name, cv.name
        HAVING demand > 0
        ORDER BY demand DESC, supply ASC
        LIMIT ?
    """, (limit,))
    
    popular = []
    for row in cursor.fetchall():
        popular.append({
            'id': row[0],
            'card_number': row[1],
            'player_name': row[2],
            'team': row[3],
            'series_name': row[4],
            'variant_name': row[5],
            'color_code': row[6],
            'demand': row[7],
            'supply': row[8]
        })
    
    conn.close()
    return popular

def get_series_completion(user_id, series_id):
    """Sorozat teljesítettségének kiszámítása"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Összes kártya a sorozatban (minden változattal)
    cursor.execute("""
        SELECT COUNT(*) FROM base_cards bc
        CROSS JOIN card_variants cv
        WHERE bc.series_id = ?
    """, (series_id,))
    total_possible = cursor.fetchone()[0]
    
    # Felhasználó kártyái ebből a sorozatból
    cursor.execute("""
        SELECT COUNT(*) FROM user_cards uc
        JOIN base_cards bc ON uc.base_card_id = bc.id
        WHERE uc.user_id = ? AND bc.series_id = ?
    """, (user_id, series_id))
    user_has = cursor.fetchone()[0]
    
    conn.close()
    
    if total_possible == 0:
        return 0, 0, 0
    
    percentage = (user_has / total_possible) * 100
    return user_has, total_possible, percentage

def validate_card_data(series_id, card_number, player_name):
    """Kártya adatok validálása"""
    errors = []
    
    if not player_name or len(player_name.strip()) < 2:
        errors.append("A játékos nevének legalább 2 karakter hosszúnak kell lennie!")
    
    if len(player_name) > 100:
        errors.append("A játékos neve maximum 100 karakter lehet!")
    
    if not series_id:
        errors.append("Sorozatot kötelező kiválasztani!")
    
    if not card_number or card_number < 1 or card_number > 400:
        errors.append("A kártya szám 1 és 400 között lehet!")
    
    return errors

def get_card_value_estimate(base_card_id, variant_id):
    """Kártya értékbecslés eladási árak alapján"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT AVG(price), MIN(price), MAX(price), COUNT(*)
        FROM user_cards
        WHERE base_card_id = ? AND variant_id = ? AND status = 'sell' AND price IS NOT NULL
    """, (base_card_id, variant_id))
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[3] > 0:  # Ha van adat
        return {
            'avg_price': result[0],
            'min_price': result[1],
            'max_price': result[2],
            'sample_size': result[3]
        }
    
    return None

def export_user_collection(user_id):
    """Felhasználó gyűjteményének exportálása CSV formátumra"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            s.name as sorozat,
            bc.card_number as szam,
            bc.player_name as jatekos,
            bc.team as csapat,
            cv.name as valtozat,
            uc.status as statusz,
            uc.price as ar,
            uc.condition as allapot,
            uc.notes as megjegyzes,
            uc.added_at as hozzaadva
        FROM user_cards uc
        JOIN base_cards bc ON uc.base_card_id = bc.id
        JOIN card_variants cv ON uc.variant_id = cv.id
        JOIN series s ON bc.series_id = s.id
        WHERE uc.user_id = ?
        ORDER BY s.name, bc.card_number, cv.rarity_level
    """, (user_id,))
    
    cards = cursor.fetchall()
    conn.close()
    
    # CSV formátum készítése
    csv_data = "Sorozat,Szám,Játékos,Csapat,Változat,Státusz,Ár,Állapot,Megjegyzés,Hozzáadva\n"
    
    for card in cards:
        row = []
        for item in card:
            if item is None:
                row.append("")
            else:
                # CSV escape
                item_str = str(item).replace('"', '""')
                if ',' in item_str or '"' in item_str:
                    item_str = f'"{item_str}"'
                row.append(item_str)
        csv_data += ",".join(row) + "\n"
    
    return csv_data

def check_duplicate_card(user_id, base_card_id, variant_id):
    """Ellenőrzi, hogy van-e már ilyen kártya a felhasználónál"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM user_cards 
        WHERE user_id = ? AND base_card_id = ? AND variant_id = ?
    """, (user_id, base_card_id, variant_id))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0

def get_system_stats():
    """Rendszer statisztikák"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Alapstatisztikák
    cursor.execute("SELECT COUNT(*) FROM users")
    stats['total_users'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM series")
    stats['total_series'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM base_cards")
    stats['total_base_cards'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM user_cards")
    stats['total_user_cards'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    stats['total_messages'] = cursor.fetchone()[0]
    
    # Aktivitás az elmúlt 7 napban
    week_ago = datetime.now() - timedelta(days=7)
    cursor.execute("SELECT COUNT(*) FROM activity_log WHERE created_at >= ?", (week_ago,))
    stats['activity_week'] = cursor.fetchone()[0]
    
    # Legnépszerűbb sorozat
    cursor.execute("""
        SELECT s.name, COUNT(uc.id) as card_count
        FROM series s
        LEFT JOIN base_cards bc ON s.id = bc.series_id
        LEFT JOIN user_cards uc ON bc.id = uc.base_card_id
        GROUP BY s.id, s.name
        ORDER BY card_count DESC
        LIMIT 1
    """)
    
    popular_series = cursor.fetchone()
    stats['popular_series'] = popular_series[0] if popular_series else "Nincs adat"
    
    conn.close()
    return stats