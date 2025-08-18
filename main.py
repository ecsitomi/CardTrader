import streamlit as st
import sqlite3
from database import init_database
from auth import login_page, register_page, logout_user
import utils

# Oldal konfiguráció
st.set_page_config(
    page_title="Kártya Csere Platform",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Adatbázis inicializálás
init_database()

# Tesztadatok hozzáadása (csak első futáskor)
from database import add_sample_data
add_sample_data()

# Session state inicializálás
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

def main():
    # Header
    st.title("🃏 Kártya Csere Platform")
    
    # Ha nincs bejelentkezve
    if not st.session_state.logged_in:
        st.sidebar.title("🔐 Bejelentkezés")
        
        auth_option = st.sidebar.selectbox(
            "Válaszd ki:",
            ["Bejelentkezés", "Regisztráció"]
        )
        
        if auth_option == "Bejelentkezés":
            login_page()
        else:
            register_page()
            
        # Főoldal tartalma nem bejelentkezett felhasználóknak
        st.markdown("""
        ## Üdvözöl a Kártya Csere Platform! 🎯
        
        **Mit csinálhatsz itt?**
        - 🃏 Gyűjteményed kezelése
        - 🔄 Kártyák cseréje/eladása
        - 🔍 Keresés kívánt kártyákra
        - 📨 Kapcsolatfelvétel más gyűjtőkkel
        - ⭐ Kívánságlista összeállítása
        
        **Jelentkezz be vagy regisztrálj a kezdéshez!**
        """)
        
    else:
        # Bejelentkezett felhasználó
        with st.sidebar:
            st.success(f"Bejelentkezve: **{st.session_state.username}**")
            
            # Kijelentkezés gomb
            if st.button("🚪 Kijelentkezés", type="secondary"):
                logout_user()
                st.rerun()
                
            st.divider()
            
            # Gyors statisztikák
            stats = utils.get_user_stats(st.session_state.user_id)
            st.metric("📦 Összesen", stats['total_cards'])
            st.metric("🏠 Megvan", stats['owned_cards'])
            st.metric("🔄 Cserélnék", stats['trade_cards'])
            st.metric("💰 Eladnám", stats['sell_cards'])
            st.metric("📚 Sorozatok", stats['series_count'])
            st.metric("🔥 Epic kártyák", stats['epic_cards'])
            st.metric("⭐ Kívánságok", stats['wishlist_count'])
            
        # Főoldal dashboard bejelentkezett felhasználóknak
        show_dashboard()

def show_dashboard():
    """Főoldal dashboard bejelentkezett felhasználóknak"""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🏠 Főoldal")
        
        # Legutóbbi aktivitás
        st.subheader("📈 Legutóbbi aktivitás")
        recent_activity = utils.get_recent_activity(st.session_state.user_id)
        
        if recent_activity:
            for activity in recent_activity[:5]:
                st.info(f"🔔 {activity['description']} - {activity['date']}")
        else:
            st.info("🌟 Még nincs aktivitásod. Kezdj el kártyákat hozzáadni!")
            
        # Gyors műveletek
        st.subheader("⚡ Gyors műveletek")
        
        col_a, col_b, col_c, col_d = st.columns(4)
        
        with col_a:
            if st.button("🃏 Kártya hozzáadása", use_container_width=True):
                st.switch_page("pages/02_🃏_Kártyáim.py")
                
        with col_b:
            if st.button("🎯 Matchmaking", use_container_width=True):
                st.switch_page("pages/07_🎯_Matchmaking.py")
                
        with col_c:
            if st.button("🔍 Kártya keresése", use_container_width=True):
                st.switch_page("pages/03_🔍_Keresés.py")
                
        with col_d:
            if st.button("📨 Üzenetek", use_container_width=True):
                st.switch_page("pages/05_📨_Üzenetek.py")
    
    with col2:
        st.header("🔥 Ajánlott")
        
        # Lehetséges matchek
        matches = utils.find_potential_matches(st.session_state.user_id)
        
        # Lehetséges matchek
        matches = utils.find_potential_matches(st.session_state.user_id)
        match_summary = utils.get_match_summary(matches)
        
        if matches:
            st.subheader("🎯 Legjobb matchek")
            
            # Quick stats
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("🎯 Összes találat", match_summary['total'])
            with col_b:
                st.metric("🔄 Cserélnék", match_summary['trade_only'])
            with col_c:
                st.metric("💰 Eladó", match_summary['for_sale'])
            
            # Top 3 match
            for match in matches[:3]:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Színes változat megjelenítése
                        variant_colored = f"<span style='color: {match['color_code']}; font-weight: bold;'>●</span> {match['variant_name']}"
                        
                        st.markdown(f"**#{match['card_number']:03d} {match['player_name']}** ({match['series_name']})")
                        st.markdown(f"Változat: {variant_colored} - {utils.get_rarity_text(match['rarity_level'])}", unsafe_allow_html=True)
                        
                        # Match score
                        score_display = utils.format_match_score(match['match_score'])
                        st.markdown(f"**Match pontszám:** {score_display}")
                        
                        # Részletek
                        details = [f"👤 {match['owner']}"]
                        details.append(f"🏷️ {match['condition']}")
                        
                        # Kereslet/kínálat
                        trend = utils.get_market_trend_emoji(match['demand'], match['supply'])
                        details.append(f"{trend} ({match['demand']}👥/{match['supply']}📦)")
                        
                        # Prioritás
                        priority_badge = utils.format_wishlist_priority_badge(match['user_priority'])
                        details.append(f"Prioritás: {priority_badge}")
                        
                        st.write(" | ".join(details))
                        
                        # Státusz és ár
                        if match['status'] == 'sell' and match['price']:
                            if match['is_affordable']:
                                st.success(f"💰 **Eladó:** {utils.format_price(match['price'])} ✅ Megfizethető")
                            else:
                                st.warning(f"💰 **Eladó:** {utils.format_price(match['price'])} ⚠️ Drága")
                        elif match['status'] == 'trade':
                            st.info("🔄 **Cserére elérhető**")
                    
                    with col2:
                        if st.button(f"💬 Üzenet", key=f"msg_{match['user_card_id']}", use_container_width=True):
                            st.switch_page("pages/05_📨_Üzenetek.py")
                        
                        if st.button(f"📊 Részletek", key=f"details_{match['user_card_id']}", use_container_width=True):
                            st.switch_page("pages/07_🎯_Matchmaking.py")
                    
                    st.divider()
            
            # Több match gomb
            if match_summary['total'] > 3:
                if st.button(f"📊 Összes match megtekintése ({match_summary['total']})", use_container_width=True):
                    st.switch_page("pages/07_🎯_Matchmaking.py")
        else:
            st.info("🤔 Még nincsenek potenciális cserék. Adj hozzá kártyákat a kívánságlistádhoz!")
            
        # Friss hírek/bejelentések
        st.subheader("📢 Hírek")
        st.success("🚀 ÚJ! Intelligens Matchmaking algoritmus 145 pontos értékeléssel!")
        st.info("🤖 AI-alapú rangsorolás: kereslet/kínálat + ritkasági szint + prioritás")
        st.info("📊 Piaci insights: legnépszerűbb és legritkább kártyáid elemzése")
        st.info("💰 Ár ajánlások: piaci összehasonlítás automatikus elemzéssel")
        st.info("🔄 Következő: Kívánságlista kezelés és üzenetküldés")

if __name__ == "__main__":
    main()