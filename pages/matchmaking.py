import streamlit as st
import sys
import os
from pathlib import Path

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import require_login
from database import (
    find_potential_matches,
    #get_market_insights,
    get_all_variants,
    get_all_series
)

from utils import (
    get_match_summary, format_match_score, get_market_trend_emoji,
    format_wishlist_priority_badge, format_price, get_rarity_text,
    format_days_ago, get_price_recommendation
)

# Bejelentkezés ellenőrzése
if not require_login():
    st.stop()

st.title("🎯 Intelligens Matchmaking")
st.markdown("*Fejlett algoritmus a legjobb cserék és vételek megtalálásához*")

# Sidebar szűrők
with st.sidebar:
    st.header("🔧 Szűrési beállítások")
    
    # Match típus
    match_type = st.selectbox(
        "🎯 Mit szeretnél látni?",
        [
            "🔍 Amit keresek (vásárlás/csere)",
            "💰 Amit kínálok (eladás/csere)",
            "📊 Piaci insights",
            "🎯 Mind a kettő"
        ]
    )
    
    st.divider()
    
    # Szűrők
    min_match_score = st.slider("📊 Min. match pontszám", 0, 100, 40)
    
    max_price = st.number_input("💰 Max. ár (Ft)", min_value=0, value=0, help="0 = nincs limit")
    
    selected_rarity = st.selectbox(
        "💎 Min. ritkasági szint",
        ["Összes", "Silver+", "Pink+", "Red+", "Blue+", "Epic csak"]
    )
    
    rarity_filter = {
        "Összes": 1,
        "Silver+": 2,
        "Pink+": 3, 
        "Red+": 4,
        "Blue+": 5,
        "Epic csak": 6
    }[selected_rarity]
    
    only_affordable = st.checkbox("💸 Csak megfizethetők", value=True)
    
    st.divider()
    
    # Matchmaking statisztikák
    st.subheader("📈 Gyors statisztikák")

# Fő tartalom
if match_type == "🔍 Amit keresek (vásárlás/csere)" or match_type == "🎯 Mind a kettő":
    
    with st.container():
        st.header("🔍 Amit keresek - Rangsort találatok")
        
        # Matchek lekérése
        with st.spinner("🔄 Matchmaking algoritmus futtatása..."):
            matches = find_potential_matches(st.session_state.user_id, limit=100)
        
        # Szűrés
        filtered_matches = []
        for match in matches:
            # Match score szűrő
            if match['match_score'] < min_match_score:
                continue
            
            # Ár szűrő
            if max_price > 0 and match['status'] == 'sell' and match['price'] and match['price'] > max_price:
                continue
            
            # Ritkasági szűrő
            if selected_rarity == "Epic csak" and match['rarity_level'] != 6:
                continue
            elif match['rarity_level'] < rarity_filter:
                continue
            
            # Megfizethetőség szűrő
            if only_affordable and not match['is_affordable']:
                continue
            
            filtered_matches.append(match)
        
        # Összefoglaló
        if filtered_matches:
            summary = get_match_summary(filtered_matches)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🎯 Találatok", summary['total'])
            with col2:
                st.metric("🔄 Cserélnék", summary['trade_only'])
            with col3:
                st.metric("💰 Eladó", summary['for_sale'])
            with col4:
                st.metric("🔥 Magas prioritás", summary['high_priority'])
            
            st.divider()
            
            # Match-ek megjelenítése
            for i, match in enumerate(filtered_matches):
                with st.expander(
                    f"#{i+1} - {match['player_name']} ({match['variant_name']}) - {format_match_score(match['match_score'])}", 
                    expanded=(i < 3)
                ):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        # Kártya alapadatok
                        variant_colored = f"<span style='color: {match['color_code']}; font-weight: bold;'>●</span> {match['variant_name']}"
                        st.markdown(f"**#{match['card_number']:03d} {match['player_name']}**")
                        st.markdown(f"📚 {match['series_name']} ({match['series_year']})")
                        st.markdown(f"💎 {variant_colored} - {get_rarity_text(match['rarity_level'])}", unsafe_allow_html=True)
                        
                        if match['team']:
                            st.write(f"👥 **Csapat:** {match['team']}")
                    
                    with col2:
                        # Match részletek
                        st.markdown(f"**🎯 Match pontszám:** {format_match_score(match['match_score'])}")
                        
                        # Kereslet/kínálat elemzés
                        trend_emoji = get_market_trend_emoji(match['demand'], match['supply'])
                        st.write(f"📊 **Piaci helyzet:** {trend_emoji}")
                        st.write(f"👥 **Kereslet:** {match['demand']} fő")
                        st.write(f"📦 **Kínálat:** {match['supply']} db")
                        st.write(f"📈 **D/S arány:** {match['demand_supply_ratio']:.1f}")
                        
                        # Saját prioritás
                        priority_badge = format_wishlist_priority_badge(match['user_priority'])
                        st.write(f"⭐ **Prioritásom:** {priority_badge}")
                        
                        # Frissesség
                        st.write(f"🕒 **Hozzáadva:** {format_days_ago(match['days_since_added'])}")
                    
                    with col3:
                        # Tulajdonos és feltételek
                        st.write(f"👤 **Tulajdonos:** {match['owner']}")
                        st.write(f"🏷️ **Állapot:** {match['condition']}")
                        
                        # Státusz és ár
                        if match['status'] == 'sell':
                            price_color = "🟢" if match['is_affordable'] else "🔴"
                            st.write(f"💰 **Ár:** {format_price(match['price'])}")
                            
                            if match['user_max_price']:
                                st.write(f"💸 **Max. áram:** {format_price(match['user_max_price'])}")
                            
                            if match['is_affordable']:
                                st.success("✅ Megfizethető!")
                            else:
                                st.error("❌ Túl drága!")
                                
                        elif match['status'] == 'trade':
                            st.info("🔄 **Cserére elérhető**")
                        
                        st.divider()
                        
                        # Akciógombok
                        if st.button(f"💬 Üzenet", key=f"msg_buy_{match['user_card_id']}", use_container_width=True):
                            # Üzenet sablon létrehozása
                            inquiry_type = "buy" if match['status'] == 'sell' else "trade"
                            
                            # Kártya adatok összeállítása
                            card_data = {
                                'card_number': match['card_number'],
                                'player_name': match['player_name'],
                                'variant_name': match['variant_name'],
                                'series_name': match['series_name'],
                                'condition': match['condition'],
                                'price': match['price']
                            }
                            
                            template_data, error = create_card_inquiry_message(
                                inquirer_id=st.session_state.user_id,
                                card_owner_name=match['owner'],
                                user_card_id=match['user_card_id'],
                                card_data=card_data,
                                inquiry_type=inquiry_type
                            )
                            
                            if template_data:
                                # Session state-be rakjuk az üzenet adatokat
                                st.session_state.message_template = template_data
                                st.session_state.target_user = match['owner']
                                st.switch_page("pages/05_📨_Üzenetek.py")
                            else:
                                st.error(f"❌ {error}")
                        
                        if st.button(f"📊 Részletes", key=f"detail_buy_{match['user_card_id']}", use_container_width=True):
                            # Részletes kártya info modal
                            with st.popover("📊 Részletes információk"):
                                st.write(f"**🃏 {match['player_name']}**")
                                st.write(f"📚 Sorozat: {match['series_name']} ({match['series_year']})")
                                st.write(f"💎 Változat: {match['variant_name']}")
                                st.write(f"🏷️ Állapot: {match['condition']}")
                                
                                if match['team']:
                                    st.write(f"👥 Csapat: {match['team']}")
                                
                                st.write(f"👤 Tulajdonos: {match['owner']}")
                                
                                # Piaci adatok
                                st.divider()
                                st.write("📈 **Piaci helyzet:**")
                                st.write(f"👥 Kereslet: {match['demand']} fő")
                                st.write(f"📦 Kínálat: {match['supply']} db")
                                st.write(f"📊 D/S arány: {match['demand_supply_ratio']:.2f}")
                                
                                # Match pontszám részletezés
                                st.divider()
                                st.write("🎯 **Match pontszám elemzés:**")
                                priority_points = (5 - match['user_priority']) * 10
                                rarity_points = match['rarity_level'] * 5
                                
                                st.write(f"⭐ Prioritás: {priority_points} pont")
                                st.write(f"💎 Ritkasági: {rarity_points} pont")
                                st.write(f"📊 **Összesen: {match['match_score']} pont**")
        else:
            st.warning("🤷 Nincsenek találatok a megadott szűrőkkel.")
            st.info("💡 Próbáld meg csökkenteni a match pontszám küszöböt vagy a szűrőket.")

if match_type == "💰 Amit kínálok (eladás/csere)" or match_type == "🎯 Mind a kettő":
    
    if match_type == "🎯 Mind a kettő":
        st.divider()
    
    with st.container():
        st.header("💰 Amit kínálok - Ki érdeklődik?")
        
        # Fordított matchek lekérése
        with st.spinner("🔄 Érdeklődők keresése..."):
            reverse_matches = find_reverse_matches(st.session_state.user_id, limit=50)
        
        if reverse_matches:
            # Csoportosítás kártyánként
            from collections import defaultdict
            cards_interest = defaultdict(list)
            
            for match in reverse_matches:
                card_key = f"{match['card_number']:03d}_{match['player_name']}_{match['variant_name']}"
                cards_interest[card_key].append(match)
            
            # Megjelenítés
            for card_key, interested_users in cards_interest.items():
                match_sample = interested_users[0]
                total_interest = len(interested_users)
                avg_interest_score = sum(u['interest_score'] for u in interested_users) / total_interest
                
                with st.expander(
                    f"🃏 {match_sample['player_name']} ({match_sample['variant_name']}) - {total_interest} érdeklődő",
                    expanded=(total_interest >= 3)
                ):
                    
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        # Kártya adatok
                        variant_colored = f"<span style='color: {match_sample['color_code']}; font-weight: bold;'>●</span> {match_sample['variant_name']}"
                        st.markdown(f"**#{match_sample['card_number']:03d} {match_sample['player_name']}**")
                        st.markdown(f"📚 {match_sample['series_name']}")
                        st.markdown(f"💎 {variant_colored} - {get_rarity_text(match_sample['rarity_level'])}", unsafe_allow_html=True)
                        
                        # Saját kártya státusz
                        status_icons = {"trade": "🔄 Cserélnék", "sell": "💰 Eladnám"}
                        st.write(f"**Státuszom:** {status_icons.get(match_sample['status'], match_sample['status'])}")
                        
                        if match_sample['price']:
                            st.write(f"**Áram:** {format_price(match_sample['price'])}")
                        
                        st.metric("🔥 Érdeklődési szint", f"{avg_interest_score:.0f} pont")
                    
                    with col2:
                        # Érdeklődők listája
                        st.subheader(f"👥 Érdeklődők ({total_interest})")
                        
                        # Rangsorolás érdeklődési pontszám alapján
                        sorted_users = sorted(interested_users, key=lambda x: x['interest_score'], reverse=True)
                        
                        for user in sorted_users:
                            user_col1, user_col2, user_col3 = st.columns([2, 2, 1])
                            
                            with user_col1:
                                st.write(f"👤 **{user['interested_user']}**")
                                priority_badge = format_wishlist_priority_badge(user['their_priority'])
                                st.write(f"⭐ Prioritás: {priority_badge}")
                            
                            with user_col2:
                                if user['their_max_price']:
                                    st.write(f"💸 Max. ár: {format_price(user['their_max_price'])}")
                                else:
                                    st.write("💸 Nincs ár limit")
                                
                                st.write(f"🎯 Érdeklődés: {user['interest_score']} pont")
                            
                            with user_col3:
                                if st.button(f"💬", key=f"msg_sell_{user['interested_user_id']}_{match_sample['my_card_id']}", help="Üzenet"):
                                    # Válasz üzenet sablon készítése
                                    template = {
                                        'subject': f"Válasz érdeklődésre: {match_sample['player_name']} ({match_sample['variant_name']})",
                                        'content': f"""Szia {user['interested_user']}!

Láttam, hogy érdeklődsz a következő kártyám iránt:

🃏 Kártya: #{match_sample['card_number']:03d} {match_sample['player_name']}
💎 Változat: {match_sample['variant_name']}
📚 Sorozat: {match_sample['series_name']}

Jelenleg {"eladásra kínálom" if match_sample['status'] == 'sell' else "cserére elérhető"}.
{"" if not match_sample['price'] else f"Ár: {format_price(match_sample['price'])}"}

Írj vissza, ha érdekel! 

Üdvözlettel,
{st.session_state.username}""",
                                        'related_card_id': match_sample['my_card_id']
                                    }
                                    
                                    st.session_state.message_template = template
                                    st.session_state.target_user_id = user['interested_user_id']
                                    st.switch_page("pages/05_📨_Üzenetek.py")
                            
                            st.write("---")
        else:
            st.info("🤷 Senki sem keresi a kártyáidat jelenleg.")
            st.info("💡 Próbáld meg hozzáadni kártyáidat cserére vagy eladásra!")

if match_type == "📊 Piaci insights":
    
    with st.container():
        st.header("📊 Piaci Insights és Elemzések")
        
        # Market insights lekérése
        with st.spinner("📈 Piaci adatok elemzése..."):
            insights = get_market_insights(st.session_state.user_id)
        
        # Legnépszerűbb kártyáim
        if insights['most_wanted_cards']:
            st.subheader("🔥 Legnépszerűbb kártyáim")
            st.markdown("*Ezeket a kártyáidat keresik a legtöbben*")
            
            for i, card in enumerate(insights['most_wanted_cards']):
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    variant_colored = f"<span style='color: {card[3]}; font-weight: bold;'>●</span> {card[2]}"
                    st.markdown(f"**#{card[0]:03d} {card[1]}** ({card[4]})")
                    st.markdown(f"💎 {variant_colored}", unsafe_allow_html=True)
                
                with col2:
                    st.metric("👥 Kereslet", f"{card[5]} fő")
                    status_icons = {"owned": "🏠", "trade": "🔄", "sell": "💰"}
                    st.write(f"Státusz: {status_icons.get(card[6], '❓')} {card[6]}")
                
                with col3:
                    if card[7]:  # price
                        st.write(f"💰 {format_price(card[7])}")
                    
                    if card[6] != 'trade' and card[6] != 'sell':
                        st.info("💡 Cserére/eladásra?")
                
                st.divider()
        
        # Legritkább kártyáim
        if insights['rarest_cards']:
            st.subheader("💎 Legritkább kártyáim")
            st.markdown("*Ezek a legértékesebb kártyáid*")
            
            for card in insights['rarest_cards']:
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    variant_colored = f"<span style='color: {card[3]}; font-weight: bold;'>●</span> {card[2]}"
                    st.markdown(f"**#{card[0]:03d} {card[1]}** ({card[4]})")
                    st.markdown(f"💎 {variant_colored}", unsafe_allow_html=True)
                
                with col2:
                    st.metric("💎 Ritkasági szint", card[5])
                    st.metric("🌐 Összesen létezik", f"{card[7]} db")
                
                with col3:
                    rarity_value = {1: "Gyakori", 2: "Ritka", 3: "Különleges", 
                                   4: "Nagyon ritka", 5: "Legendás", 6: "Epikus"}
                    st.write(f"📊 {rarity_value.get(card[5], 'Ismeretlen')}")
                    
                    if card[7] <= 5:
                        st.success("🔥 Ultra ritka!")
                    elif card[7] <= 10:
                        st.warning("⚡ Nagyon ritka!")
                
                st.divider()
        
        # Ár összehasonlítások
        if insights['price_comparisons']:
            st.subheader("💰 Ár összehasonlítások")
            st.markdown("*Hogyan árazod a kártyáidat a piachoz képest?*")
            
            for price_data in insights['price_comparisons']:
                col1, col2, col3 = st.columns([2, 2, 2])
                
                with col1:
                    st.write(f"**#{price_data[1]:03d} {price_data[2]}**")
                    st.write(f"💎 {price_data[3]}")
                
                with col2:
                    st.metric("💰 Saját áram", format_price(price_data[4]))
                    st.metric("📊 Piaci átlag", format_price(price_data[5]))
                
                with col3:
                    st.metric("📉 Min. piaci ár", format_price(price_data[6]))
                    st.metric("📈 Max. piaci ár", format_price(price_data[7]))
                    st.caption(f"📊 {price_data[8]} piaci minta")
                    
                    # Ár ajánlás
                    recommendation, rec_type = get_price_recommendation(
                        price_data[4], price_data[5], price_data[6], price_data[7], price_data[8]
                    )
                    
                    if rec_type == "success":
                        st.success(recommendation)
                    elif rec_type == "warning":
                        st.warning(recommendation)
                    elif rec_type == "error":
                        st.error(recommendation)
                    else:
                        st.info(recommendation)
                
                st.divider()

# Sidebar statisztikák frissítése
with st.sidebar:
    if 'matches' in locals():
        filtered_count = len(filtered_matches) if 'filtered_matches' in locals() else 0
        st.metric("🔍 Szűrt találatok", filtered_count)
    
    if 'reverse_matches' in locals():
        st.metric("💰 Érdeklődők", len(reverse_matches))
    
    # Algoritmus magyarázat
    with st.expander("🤖 Algoritmus magyarázat"):
        st.markdown("""
        **Match pontszám kalkuláció:**
        - 🎯 Kívánságlista prioritás: 10-40 pont
        - 💎 Ritkasági bónusz: 5-30 pont  
        - 📊 Kereslet/kínálat arány: 0-30 pont
        - 👥 Népszerűség: 0-20 pont
        - 💰 Ár megfelelőség: 0-15 pont
        - 🕒 Frissesség: 0-10 pont
        
        **Max. pontszám:** 145 pont
        **Kiváló match:** 80+ pont
        """)

st.markdown("---")
st.caption("🤖 Intelligens matchmaking algoritmus - A pontszámok folyamatosan frissülnek")