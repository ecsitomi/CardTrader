import streamlit as st
import sys
import os
from pathlib import Path

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import require_login
from database import (
    get_user_cards, get_all_series, get_base_cards_by_series, 
    get_all_variants, add_user_card, update_user_card_status,
    delete_user_card, add_base_card, add_series
)
from utils import (
    get_sports_list, get_status_list, get_condition_list,
    format_price, get_variant_display, format_card_display,
    check_duplicate_card, get_series_completion
)

# Bejelentkezés ellenőrzése
if not require_login():
    st.stop()

st.title("🃏 Kártyáim")

# Sidebar szűrők és statisztikák
with st.sidebar:
    st.header("🔍 Szűrés és Statisztikák")
    
    # Sorozat szűrő
    all_series = get_all_series()
    series_options = ["Összes sorozat"] + [f"{s[1]} ({s[2]})" for s in all_series]
    selected_series = st.selectbox("🎯 Sorozat", series_options)
    
    selected_series_id = None
    if selected_series != "Összes sorozat":
        series_index = series_options.index(selected_series) - 1
        selected_series_id = all_series[series_index][0]
    
    # Változat szűrő
    all_variants = get_all_variants()
    variant_options = ["Összes változat"] + [v[1] for v in all_variants]
    selected_variant = st.selectbox("💎 Változat", variant_options)
    
    # Státusz szűrő
    status_options = ["Összes státusz"] + [f"{desc}" for code, desc in get_status_list()]
    selected_status = st.selectbox("📊 Státusz", status_options)
    
    st.divider()
    
    # Gyors statisztikák
    user_cards = get_user_cards(st.session_state.user_id)
    total_cards = len(user_cards)
    
    if total_cards > 0:
        owned_count = len([c for c in user_cards if c[1] == 'owned'])
        trade_count = len([c for c in user_cards if c[1] == 'trade'])
        sell_count = len([c for c in user_cards if c[1] == 'sell'])
        
        st.metric("📦 Összesen", total_cards)
        st.metric("🏠 Megvan", owned_count)
        st.metric("🔄 Cserélnék", trade_count)
        st.metric("💰 Eladnám", sell_count)
        
        # Sorozat teljesítettség
        if selected_series_id:
            has, total, percentage = get_series_completion(st.session_state.user_id, selected_series_id)
            st.metric("🎯 Teljesítettség", f"{percentage:.1f}%")
            st.write(f"📊 {has}/{total} kártya")
    else:
        st.info("🎯 Még nincs kártyád!")

# Fő tartalom
tab1, tab2, tab3 = st.tabs(["📋 Gyűjteményem", "➕ Kártya hozzáadása", "🆕 Új sorozat/kártya"])

with tab1:
    st.header("📋 Gyűjteményem")
    
    # Kártyák lekérése és szűrése
    user_cards = get_user_cards(st.session_state.user_id, series_id=selected_series_id)
    
    # További szűrés
    filtered_cards = []
    for card in user_cards:
        # Változat szűrő
        if selected_variant != "Összes változat" and card[10] != selected_variant:
            continue
        
        # Státusz szűrő
        if selected_status != "Összes státusz":
            status_map = {"🏠 Megvan": "owned", "🔄 Cserélnék": "trade", "💰 Eladnám": "sell"}
            required_status = None
            for status_desc, status_code in status_map.items():
                if status_desc in selected_status:
                    required_status = status_code
                    break
            
            if required_status and card[1] != required_status:
                continue
        
        filtered_cards.append(card)
    
    if not filtered_cards:
        if not user_cards:
            st.info("🎯 Még nincs kártyád! Használd a 'Kártya hozzáadása' fület.")
        else:
            st.info("🔍 Nincs a szűrőknek megfelelő kártya.")
    else:
        # Kártyák csoportosítása sorozat szerint
        from collections import defaultdict
        cards_by_series = defaultdict(list)
        
        for card in filtered_cards:
            series_name = card[13]  # series_name
            cards_by_series[series_name].append(card)
        
        for series_name, cards in cards_by_series.items():
            with st.expander(f"📚 {series_name} ({len(cards)} kártya)", expanded=len(cards_by_series) == 1):
                
                # Kártyák megjelenítése
                for card in sorted(cards, key=lambda x: (x[6], x[11])):  # card_number, rarity_level
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        # Kártya alapadatok
                        variant_display = f"<span style='color: {card[11]}; font-weight: bold;'>●</span> {card[10]}"
                        st.markdown(f"**#{card[6]:03d} {card[7]}** - {variant_display}", unsafe_allow_html=True)
                        
                        if card[8]:  # team
                            st.write(f"👥 {card[8]}")
                        if card[9]:  # position
                            st.write(f"📍 {card[9]}")
                    
                    with col2:
                        # Státusz
                        status_icons = {"owned": "🏠", "trade": "🔄", "sell": "💰"}
                        status_names = {"owned": "Megvan", "trade": "Cserélnék", "sell": "Eladnám"}
                        
                        st.write(f"**Státusz:** {status_icons.get(card[1], '❓')} {status_names.get(card[1], card[1])}")
                        
                        if card[2]:  # price
                            st.write(f"**Ár:** {format_price(card[2])}")
                        
                        st.write(f"**Állapot:** {card[3]}")
                    
                    with col3:
                        # Megjegyzés és dátum
                        if card[4]:  # notes
                            st.write(f"**Megjegyzés:** {card[4]}")
                        
                        # Hozzáadás dátuma
                        st.caption(f"Hozzáadva: {card[5][:10]}")
                    
                    with col4:
                        # Műveletek
                        # Státusz váltás gombok
                        current_status = card[1]
                        
                        if current_status != "trade":
                            if st.button("🔄", help="Cserélnék", key=f"trade_{card[0]}"):
                                update_user_card_status(card[0], "trade", None)
                                st.rerun()
                        
                        if current_status != "sell":
                            if st.button("💰", help="Eladnám", key=f"sell_{card[0]}"):
                                # Ár megadás
                                with st.popover("💰 Ár megadása"):
                                    price = st.number_input("Ár (Ft)", min_value=1, key=f"price_{card[0]}")
                                    if st.button("✅ Beállítás", key=f"set_price_{card[0]}"):
                                        update_user_card_status(card[0], "sell", price)
                                        st.rerun()
                        
                        if current_status != "owned":
                            if st.button("🏠", help="Csak megvan", key=f"owned_{card[0]}"):
                                update_user_card_status(card[0], "owned", None)
                                st.rerun()
                        
                        # Törlés gomb
                        if st.button("🗑️", help="Törlés", key=f"delete_{card[0]}"):
                            delete_user_card(card[0], st.session_state.user_id)
                            st.success("Kártya törölve!")
                            st.rerun()
                    
                    st.divider()

with tab2:
    st.header("➕ Kártya hozzáadása gyűjteményhez")
    
    # 1. lépés: Sorozat választása
    st.subheader("1️⃣ Sorozat választása")
    
    all_series = get_all_series()
    if not all_series:
        st.warning("⚠️ Még nincs egyetlen sorozat sem! Használd a 'Új sorozat/kártya' fület.")
        st.stop()
    
    series_options = [f"{s[1]} ({s[2]}) - {s[3]}" for s in all_series]
    selected_series_idx = st.selectbox("🎯 Válassz sorozatot:", range(len(series_options)), 
                                      format_func=lambda x: series_options[x])
    
    selected_series_data = all_series[selected_series_idx]
    series_id = selected_series_data[0]
    
    st.success(f"✅ Kiválasztva: **{selected_series_data[1]}**")
    
    # 2. lépés: Kártya választása
    st.subheader("2️⃣ Kártya választása")
    
    base_cards = get_base_cards_by_series(series_id)
    
    if not base_cards:
        st.warning(f"⚠️ A '{selected_series_data[1]}' sorozatban még nincsenek kártyák!")
        
        # Gyors kártya hozzáadás
        with st.form("quick_add_card"):
            st.write("**Gyors kártya hozzáadás:**")
            col1, col2 = st.columns(2)
            
            with col1:
                card_number = st.number_input("Kártya száma", min_value=1, max_value=400, value=1)
                player_name = st.text_input("Játékos neve", placeholder="pl. Lionel Messi")
            
            with col2:
                team = st.text_input("Csapat", placeholder="pl. PSG")
                position = st.text_input("Pozíció", placeholder="pl. RW")
            
            if st.form_submit_button("➕ Kártya létrehozása"):
                if player_name:
                    success, card_id = add_base_card(series_id, card_number, player_name, team, position)
                    if success:
                        st.success(f"✅ {player_name} kártya létrehozva!")
                        st.rerun()
                    else:
                        st.error("❌ Hiba: Ez a kártya szám már foglalt!")
                else:
                    st.error("❌ A játékos neve kötelező!")
        
        st.stop()
    
    # Kártya választó
    search_player = st.text_input("🔍 Játékos keresése", placeholder="Írd be a játékos nevét...")
    
    filtered_cards = base_cards
    if search_player:
        filtered_cards = [card for card in base_cards if search_player.lower() in card[2].lower()]
    
    if not filtered_cards:
        st.warning("🤷 Nincs ilyen játékos a sorozatban.")
        st.stop()
    
    # Kártyák megjelenítése
    selected_card = None
    
    for card in filtered_cards[:20]:  # Csak első 20 találat
        col1, col2 = st.columns([4, 1])
        
        with col1:
            card_info = f"#{card[1]:03d} **{card[2]}**"
            if card[3]:  # team
                card_info += f" - {card[3]}"
            if card[4]:  # position
                card_info += f" ({card[4]})"
            
            st.markdown(card_info)
        
        with col2:
            if st.button("✅ Választás", key=f"select_card_{card[0]}"):
                selected_card = card
                st.session_state.selected_card = card
                break
    
    # Ha van kiválasztott kártya
    if 'selected_card' in st.session_state:
        selected_card = st.session_state.selected_card
        
        st.success(f"✅ Kiválasztva: **#{selected_card[1]:03d} {selected_card[2]}**")
        
        # 3. lépés: Változat és részletek
        st.subheader("3️⃣ Változat és részletek megadása")
        
        with st.form("add_card_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Változat választás
                variants = get_all_variants()
                variant_options = []
                for variant in variants:
                    variant_display = f"{variant[1]} (Ritkasági szint: {variant[3]})"
                    variant_options.append(variant_display)
                
                selected_variant_idx = st.selectbox("💎 Változat", range(len(variants)), 
                                                   format_func=lambda x: variant_options[x])
                
                selected_variant = variants[selected_variant_idx]
                
                # Státusz
                status_options = get_status_list()
                status_idx = st.selectbox("📊 Mit szeretnél csinálni?", range(len(status_options)),
                                        format_func=lambda x: status_options[x][1])
                
                selected_status = status_options[status_idx][0]
            
            with col2:
                # Ár (ha eladás)
                price = None
                if selected_status == "sell":
                    price = st.number_input("💰 Eladási ár (Ft)", min_value=1, value=1000)
                
                # Állapot
                condition = st.selectbox("🏷️ Állapot", get_condition_list(), index=2)
                
                # Megjegyzés
                notes = st.text_area("📝 Megjegyzés", placeholder="Opcionális megjegyzés...")
            
            # Ellenőrzés duplikáció
            duplicate_check = check_duplicate_card(st.session_state.user_id, selected_card[0], selected_variant[0])
            
            if duplicate_check:
                st.warning(f"⚠️ Már megvan nálad ez a kártya ebben a változatban!")
            
            # Hozzáadás gomb
            col_a, col_b = st.columns(2)
            
            with col_a:
                submit_disabled = duplicate_check
                if st.form_submit_button("✅ Hozzáadás gyűjteményhez", disabled=submit_disabled):
                    if not duplicate_check:
                        success, message = add_user_card(
                            user_id=st.session_state.user_id,
                            base_card_id=selected_card[0],
                            variant_id=selected_variant[0],
                            status=selected_status,
                            price=price,
                            condition=condition,
                            notes=notes
                        )
                        
                        if success:
                            st.success(f"🎉 {selected_card[2]} ({selected_variant[1]}) hozzáadva!")
                            del st.session_state.selected_card
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
            
            with col_b:
                if st.form_submit_button("❌ Mégse"):
                    if 'selected_card' in st.session_state:
                        del st.session_state.selected_card
                    st.rerun()

with tab3:
    st.header("🆕 Új sorozat vagy kártya létrehozása")
    
    subtab1, subtab2 = st.tabs(["📚 Új sorozat", "🃏 Új kártya meglévő sorozathoz"])
    
    with subtab1:
        st.subheader("📚 Új sorozat létrehozása")
        
        with st.form("create_series_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                series_name = st.text_input("📚 Sorozat neve *", placeholder="pl. FIFA 2024")
                series_year = st.number_input("📅 Év", min_value=1900, max_value=2030, value=2024)
            
            with col2:
                series_sport = st.selectbox("🏃 Sport", get_sports_list())
                total_cards = st.number_input("🔢 Kártyák száma", min_value=1, max_value=1000, value=400)
            
            series_description = st.text_area("📄 Leírás", placeholder="Sorozat leírása...")
            
            if st.form_submit_button("✅ Sorozat létrehozása"):
                if series_name.strip():
                    success, result = add_series(series_name.strip(), series_year, series_sport, series_description.strip())
                    
                    if success:
                        st.success(f"🎉 '{series_name}' sorozat sikeresen létrehozva!")
                        st.info("💡 Most már hozzáadhatsz kártyákat ehhez a sorozathoz!")
                    else:
                        st.error(f"❌ {result}")
                else:
                    st.error("❌ A sorozat neve kötelező!")
    
    with subtab2:
        st.subheader("🃏 Új kártya hozzáadása meglévő sorozathoz")
        
        all_series = get_all_series()
        if not all_series:
            st.warning("⚠️ Először hozz létre egy sorozatot!")
        else:
            with st.form("create_card_form"):
                # Sorozat választás
                series_options = [f"{s[1]} ({s[2]})" for s in all_series]
                selected_series_idx = st.selectbox("🎯 Sorozat", range(len(series_options)), 
                                                  format_func=lambda x: series_options[x])
                
                target_series_id = all_series[selected_series_idx][0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    card_number = st.number_input("🔢 Kártya száma", min_value=1, max_value=400, value=1)
                    player_name = st.text_input("👤 Játékos neve *", placeholder="pl. Lionel Messi")
                
                with col2:
                    team = st.text_input("👥 Csapat", placeholder="pl. PSG")
                    position = st.text_input("📍 Pozíció", placeholder="pl. RW")
                
                description = st.text_area("📄 Leírás", placeholder="Opcionális leírás...")
                
                if st.form_submit_button("✅ Kártya létrehozása"):
                    if player_name.strip():
                        success, result = add_base_card(
                            series_id=target_series_id,
                            card_number=card_number,
                            player_name=player_name.strip(),
                            team=team.strip(),
                            position=position.strip(),
                            description=description.strip()
                        )
                        
                        if success:
                            st.success(f"🎉 {player_name} kártja sikeresen létrehozva!")
                        else:
                            st.error(f"❌ {result}")
                    else:
                        st.error("❌ A játékos neve kötelező!")