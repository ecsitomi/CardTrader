import streamlit as st
import sys
import os
from pathlib import Path

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import require_login
from database import (
    get_inbox_messages, get_sent_messages, send_message, get_message_thread,
    mark_message_as_read, delete_message, get_unread_message_count,
    search_users_for_messaging, get_conversation_partners, create_card_inquiry_message
)
from utils import (
    format_message_time, truncate_message_content, get_message_priority_badge,
    format_message_subject, validate_message_content, create_message_thread_display,
    get_quick_reply_templates, format_price
)

# Bejelentkezés ellenőrzése
if not require_login():
    st.stop()

# Segédfunkciók
def clear_message_session():
    """Üzenet session adatok törlése"""
    keys_to_clear = ['selected_message', 'reply_to_message', 'message_content', 'show_compose', 'selected_conversation']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def show_compose_message():
    """Új üzenet írása"""
    st.header("✍️ Új üzenet írása")
    
    # Ha válaszolunk egy üzenetre
    if 'reply_to_message' in st.session_state:
        original_msg_id = st.session_state.reply_to_message
        thread = get_message_thread(original_msg_id, st.session_state.user_id)
        
        if thread:
            original_msg = thread[0]  # Eredeti üzenet
            st.info(f"💬 **Válasz erre:** {original_msg[3]}")  # subject
            st.write(f"👤 **Eredeti feladó:** {original_msg[9]}")  # sender_name
            
            # Előre kitöltött adatok
            default_receiver_id = original_msg[1]  # sender_id
            default_subject = f"Re: {original_msg[3]}"
            parent_message_id = original_msg_id
        else:
            st.error("Eredeti üzenet nem található!")
            return
    else:
        default_receiver_id = None
        default_subject = ""
        parent_message_id = None
    
    with st.form("compose_message"):
        # Címzett választása (ha nem válasz)
        if not default_receiver_id:
            st.subheader("👤 Címzett")
            
            # Felhasználó keresés
            user_search = st.text_input("🔍 Felhasználó keresése", placeholder="Írj be felhasználónevet...")
            
            if user_search:
                found_users = search_users_for_messaging(user_search, exclude_user_id=st.session_state.user_id)
                
                if found_users:
                    user_options = []
                    user_ids = []
                    
                    for user in found_users:
                        user_id, username, created_at, card_count, last_activity = user
                        user_display = f"{username} ({card_count} kártya)"
                        user_options.append(user_display)
                        user_ids.append(user_id)
                    
                    selected_user_idx = st.selectbox("Válassz felhasználót:", range(len(user_options)), 
                                                    format_func=lambda x: user_options[x])
                    
                    selected_receiver_id = user_ids[selected_user_idx]
                else:
                    st.warning("🤷 Nincs ilyen felhasználó.")
                    selected_receiver_id = None
            else:
                # Beszélgetőpartnerek gyors választása
                partners = get_conversation_partners(st.session_state.user_id, limit=5)
                
                if partners:
                    st.write("**💬 Vagy válassz a korábbi beszélgetőpartnerek közül:**")
                    partner_options = ["Válassz..."] + [f"{p[1]} (utolsó üzenet: {format_message_time(p[2])})" for p in partners]
                    partner_ids = [None] + [p[0] for p in partners]
                    
                    partner_idx = st.selectbox("Korábbi partnerek:", range(len(partner_options)), 
                                             format_func=lambda x: partner_options[x])
                    
                    selected_receiver_id = partner_ids[partner_idx]
                else:
                    selected_receiver_id = None
        else:
            selected_receiver_id = default_receiver_id
        
        st.divider()
        
        # Üzenet tartalom
        st.subheader("📝 Üzenet")
        
        subject = st.text_input("📋 Tárgy", value=default_subject, max_chars=100,
                               placeholder="Üzenet tárgya...")
        
        # Gyors sablonok
        if not parent_message_id:  # Csak új üzenethez
            st.write("**🚀 Gyors sablonok:**")
            templates = get_quick_reply_templates()
            
            col1, col2 = st.columns(2)
            for i, template in enumerate(templates[:6]):
                col = col1 if i % 2 == 0 else col2
                with col:
                    if st.button(f"📝 {template[:25]}...", key=f"template_{i}"):
                        st.session_state.message_content = st.session_state.get('message_content', '') + template
        
        # Üzenet tartalom
        message_content = st.text_area("💬 Üzenet tartalom", 
                                      value=st.session_state.get('message_content', ''),
                                      height=200, max_chars=2000,
                                      placeholder="Írd ide az üzeneted...")
        
        # Kapcsolódó kártya (opcionális)
        st.subheader("🃏 Kapcsolódó kártya (opcionális)")
        related_card_help = st.checkbox("🔗 Ez az üzenet egy konkrét kártyáról szól")
        
        related_card_id = None
        if related_card_help:
            st.info("💡 A kártya ID-t általában a matchmaking oldalról kapod automatikusan.")
            card_id_input = st.number_input("Kártya ID", min_value=1, value=1, 
                                           help="Ez általában automatikusan kitöltődik a matchmaking oldalról")
            related_card_id = card_id_input
        
        # Küldés
        col1, col2 = st.columns(2)
        
        with col1:
            submit_button = st.form_submit_button("📨 Üzenet küldése", use_container_width=True)
        
        with col2:
            if st.form_submit_button("❌ Mégse", use_container_width=True):
                # Session state tisztítás
                for key in ['reply_to_message', 'message_content', 'show_compose']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        # Üzenet küldés feldolgozása
        if submit_button:
            # Validáció
            errors = validate_message_content(subject, message_content)
            
            if not selected_receiver_id:
                errors.append("Válassz címzettet!")
            
            if selected_receiver_id == st.session_state.user_id:
                errors.append("Nem küldhetsz üzenetet önmagadnak!")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Üzenet küldése
                success, result = send_message(
                    sender_id=st.session_state.user_id,
                    receiver_id=selected_receiver_id,
                    subject=subject,
                    content=message_content,
                    parent_message_id=parent_message_id,
                    related_card_id=related_card_id
                )
                
                if success:
                    st.success("✅ Üzenet sikeresen elküldve!")
                    
                    # Session state tisztítás
                    for key in ['reply_to_message', 'message_content', 'show_compose']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.rerun()
                else:
                    st.error(f"❌ Hiba történt: {result}")

def show_message_thread(message_id):
    """Üzenet szál megtekintése"""
    thread = get_message_thread(message_id, st.session_state.user_id)
    
    if not thread:
        st.error("Üzenet nem található!")
        return
    
    thread_data = create_message_thread_display(thread, st.session_state.user_id)
    
    st.header("💬 Üzenet szál")
    
    # Vissza gomb
    if st.button("⬅️ Vissza"):
        if 'selected_message' in st.session_state:
            del st.session_state.selected_message
        st.rerun()
    
    st.divider()
    
    # Üzenetek megjelenítése
    for i, msg_data in enumerate(thread_data):
        with st.container():
            if msg_data['is_mine']:
                # Saját üzenet - jobbra igazítva
                col1, col2 = st.columns([1, 3])
                with col2:
                    st.markdown(f"""
                    <div style='background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                        <strong>{msg_data['message_icon']} Te</strong><br>
                        <small>{msg_data['formatted_time']}</small><br>
                        {msg_data['content']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Mások üzenete - balra igazítva
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                    <div style='background-color: #f5f5f5; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                        <strong>{msg_data['message_icon']} {msg_data['sender_name']}</strong><br>
                        <small>{msg_data['formatted_time']}</small><br>
                        {msg_data['content']}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Kapcsolódó kártya info
            if msg_data['related_card_info']:
                st.info(f"🃏 Kapcsolódó kártya: {msg_data['related_card_info']}")
    
    st.divider()
    
    # Gyors válasz
    with st.form("quick_reply"):
        st.subheader("💬 Gyors válasz")
        
        reply_content = st.text_area("Válasz:", height=100, max_chars=1000)
        
        if st.form_submit_button("📨 Válasz küldése"):
            if reply_content.strip():
                # Eredeti üzenet adatok
                original_msg = thread_data[0]
                other_user_id = original_msg['sender_id'] if not original_msg['is_mine'] else original_msg['receiver_id']
                
                success, result = send_message(
                    sender_id=st.session_state.user_id,
                    receiver_id=other_user_id,
                    subject=f"Re: {original_msg['subject']}",
                    content=reply_content,
                    parent_message_id=original_msg['id'],
                    related_card_id=original_msg.get('related_card_id')
                )
                
                if success:
                    st.success("✅ Válasz elküldve!")
                    st.rerun()
                else:
                    st.error(f"❌ Hiba: {result}")
            else:
                st.error("❌ A válasz nem lehet üres!")

def show_main_messages():
    """Fő üzenet lista (beérkezett és elküldött)"""
    
    tab1, tab2, tab3 = st.tabs(["📥 Beérkezett", "📤 Elküldött", "✍️ Új üzenet"])
    
    with tab1:
        st.header("📥 Beérkezett üzenetek")
        
        # Üzenetek lekérése
        inbox_messages = get_inbox_messages(st.session_state.user_id, limit=50)
        
        if not inbox_messages:
            st.info("📭 Nincs beérkezett üzeneted.")
            st.info("💡 Amikor valaki üzenetet küld, itt fogod látni.")
        else:
            # Szűrés opciók
            col1, col2 = st.columns([2, 1])
            
            with col1:
                filter_unread = st.checkbox("🔴 Csak olvasatlanok", value=False)
                filter_with_cards = st.checkbox("🃏 Kártya-specifikus üzenetek", value=False)
            
            with col2:
                if st.button("✅ Összes olvasottnak jelölés"):
                    for msg in inbox_messages:
                        if not msg[5]:  # is_read
                            mark_message_as_read(msg[0], st.session_state.user_id)
                    st.success("Összes üzenet olvasottnak jelölve!")
                    st.rerun()
            
            st.divider()
            
            # Szűrt üzenetek
            filtered_messages = []
            for msg in inbox_messages:
                if filter_unread and msg[5]:  # is_read = True, de mi csak olvasatlanokat akarunk
                    continue
                if filter_with_cards and not msg[7]:  # related_card_id
                    continue
                filtered_messages.append(msg)
            
            # Üzenetek megjelenítése
            for msg in filtered_messages:
                msg_id, sender_id, subject, content, sent_at, is_read, parent_id, card_id, sender_name, card_info, reply_count = msg
                
                # Üzenet konténer
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        # Tárgy és feladó
                        read_style = "" if is_read else "font-weight: bold;"
                        
                        st.markdown(f"<div style='{read_style}'>📩 {format_message_subject(subject)}</div>", 
                                   unsafe_allow_html=True)
                        st.write(f"👤 **{sender_name}** • {format_message_time(sent_at)}")
                        
                        # Tartalom előnézet
                        preview = truncate_message_content(content, max_length=80)
                        st.write(f"💭 {preview}")
                        
                        # Kapcsolódó kártya
                        if card_info:
                            st.info(f"🃏 Kapcsolódó kártya: {card_info}")
                    
                    with col2:
                        # Üzenet jellemzők
                        badges = get_message_priority_badge(is_read, reply_count, card_info)
                        if badges:
                            st.write(f"🏷️ {badges}")
                        
                        # Válaszok
                        if reply_count > 0:
                            st.success(f"💬 {reply_count} válasz")
                    
                    with col3:
                        # Műveletek
                        if st.button("👁️ Megnyitás", key=f"open_inbox_{msg_id}"):
                            if not is_read:
                                mark_message_as_read(msg_id, st.session_state.user_id)
                            st.session_state.selected_message = msg_id
                            st.rerun()
                        
                        if st.button("💬 Válasz", key=f"reply_inbox_{msg_id}"):
                            st.session_state.reply_to_message = msg_id
                            st.rerun()
                        
                        if st.button("🗑️", key=f"delete_inbox_{msg_id}", help="Törlés"):
                            if delete_message(msg_id, st.session_state.user_id):
                                st.success("Üzenet törölve!")
                                st.rerun()
                    
                    st.divider()
    
    with tab2:
        st.header("📤 Elküldött üzenetek")
        
        # Üzenetek lekérése
        sent_messages = get_sent_messages(st.session_state.user_id, limit=50)
        
        if not sent_messages:
            st.info("📭 Még nem küldtél üzenetet.")
            st.info("💡 Használd az 'Új üzenet' fület üzenet küldéséhez.")
        else:
            # Üzenetek megjelenítése
            for msg in sent_messages:
                msg_id, receiver_id, subject, content, sent_at, is_read, parent_id, card_id, receiver_name, card_info, reply_count = msg
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"📨 **{format_message_subject(subject)}**")
                        st.write(f"👤 Címzett: **{receiver_name}** • {format_message_time(sent_at)}")
                        
                        # Tartalom előnézet
                        preview = truncate_message_content(content, max_length=80)
                        st.write(f"💭 {preview}")
                        
                        # Kapcsolódó kártya
                        if card_info:
                            st.info(f"🃏 Kapcsolódó kártya: {card_info}")
                    
                    with col2:
                        # Olvasott státusz
                        if is_read:
                            st.success("✅ Elolvasva")
                        else:
                            st.warning("⏳ Olvasatlan")
                        
                        # Válaszok
                        if reply_count > 0:
                            st.info(f"💬 {reply_count} válasz")
                    
                    with col3:
                        if st.button("👁️ Megnyitás", key=f"open_sent_{msg_id}"):
                            st.session_state.selected_message = msg_id
                            st.rerun()
                        
                        if st.button("🗑️", key=f"delete_sent_{msg_id}", help="Törlés"):
                            if delete_message(msg_id, st.session_state.user_id):
                                st.success("Üzenet törölve!")
                                st.rerun()
                    
                    st.divider()
    
    with tab3:
        show_compose_message()

# Fő logika
# Olvasatlan üzenetek száma
unread_count = get_unread_message_count(st.session_state.user_id)

st.title(f"📨 Üzenetek {f'({unread_count} új)' if unread_count > 0 else ''}")

# Sidebar - Beszélgetőpartnerek
with st.sidebar:
    st.header("💬 Beszélgetőpartnerek")
    
    # Gyors statisztikák
    st.metric("📥 Olvasatlan", unread_count)
    
    # Legutóbbi beszélgetőpartnerek
    partners = get_conversation_partners(st.session_state.user_id, limit=10)
    
    if partners:
        st.subheader("🕒 Legutóbbi")
        
        for partner in partners[:5]:
            partner_id, partner_name, last_time, msg_count, unread = partner
            
            # Partner gomb
            button_text = f"👤 {partner_name}"
            if unread > 0:
                button_text += f" ({unread} új)"
            
            if st.button(button_text, key=f"partner_{partner_id}", use_container_width=True):
                # Beszélgetés megnyitása - egyszerűsítjük
                st.info(f"💬 Beszélgetés {partner_name}-vel hamarosan elérhető!")
                st.info("💡 Egyelőre használd a beérkezett/elküldött üzenetek füleket.")
    else:
        st.info("🤷 Még nincs üzenetváltásod.")
    
    st.divider()
    
    # Gyors műveletek
    st.subheader("⚡ Gyors műveletek")
    
    if st.button("✍️ Új üzenet", use_container_width=True):
        st.session_state.show_compose = True
        st.rerun()
    
    if st.button("🔄 Frissítés", use_container_width=True):
        st.rerun()
    
    # Matchmaking integráció
    st.divider()
    st.subheader("🎯 Kapcsolódó")
    
    if st.button("🎯 Matchmaking", use_container_width=True):
        st.switch_page("pages/07_🎯_Matchmaking.py")
    
    st.info("💡 **Tipp:** A matchmaking oldalról könnyedén küldhetsz üzeneteket kártyák kapcsán!")

# Fő tartalom megjelenítése
# Speciális üzenet megjelenítés ha van kiválasztott üzenet
if 'selected_message' in st.session_state:
    show_message_thread(st.session_state.selected_message)
elif 'reply_to_message' in st.session_state:
    show_compose_message()
elif 'show_compose' in st.session_state and st.session_state.show_compose:
    show_compose_message()
else:
    show_main_messages()

# Alsó rész - tippek és session tisztítás
st.markdown("---")
col1, col2 = st.columns([3, 1])

with col1:
    st.caption("💡 **Tipp:** Használd a matchmaking oldalt könnyű üzenetküldéshez kártyák kapcsán!")

with col2:
    if st.button("🧹 Session tisztítás", help="Ha elakadtál valahol"):
        clear_message_session()
        st.success("Session megtisztítva!")
        st.rerun()