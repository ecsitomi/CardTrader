import streamlit as st
import re
from database import create_user, authenticate_user

def is_valid_email(email):
    """Email cím validálása"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_username(username):
    """Felhasználónév validálása"""
    if len(username) < 3:
        return False, "A felhasználónév legalább 3 karakter hosszú legyen!"
    if len(username) > 20:
        return False, "A felhasználónév maximum 20 karakter lehet!"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "A felhasználónév csak betűket, számokat és aláhúzást tartalmazhat!"
    return True, ""

def is_valid_password(password):
    """Jelszó validálása"""
    if len(password) < 6:
        return False, "A jelszó legalább 6 karakter hosszú legyen!"
    if len(password) > 50:
        return False, "A jelszó maximum 50 karakter lehet!"
    return True, ""

def login_page():
    """Bejelentkezési oldal"""
    st.subheader("🔐 Bejelentkezés")
    
    with st.form("login_form"):
        username = st.text_input("👤 Felhasználónév", placeholder="Add meg a felhasználóneved")
        password = st.text_input("🔒 Jelszó", type="password", placeholder="Add meg a jelszavad")
        
        submit_button = st.form_submit_button("🚪 Bejelentkezés", use_container_width=True)
        
        if submit_button:
            if not username or not password:
                st.error("❌ Minden mezőt ki kell tölteni!")
                return
            
            # Hitelesítés
            success, user_data = authenticate_user(username, password)
            
            if success:
                # Session state beállítása
                st.session_state.logged_in = True
                st.session_state.user_id = user_data['id']
                st.session_state.username = user_data['username']
                st.session_state.email = user_data['email']
                
                st.success(f"✅ Sikeres bejelentkezés! Üdvözöl {username}!")
                st.rerun()
            else:
                st.error("❌ Hibás felhasználónév vagy jelszó!")

def register_page():
    """Regisztrációs oldal"""
    st.subheader("📝 Regisztráció")
    
    with st.form("register_form"):
        username = st.text_input("👤 Felhasználónév", placeholder="Válassz egy egyedi felhasználónevet")
        email = st.text_input("📧 Email cím", placeholder="add@email.com")
        password = st.text_input("🔒 Jelszó", type="password", placeholder="Legalább 6 karakter")
        password_confirm = st.text_input("🔒 Jelszó megerősítése", type="password", placeholder="Jelszó újra")
        
        # Felhasználási feltételek
        terms_accepted = st.checkbox("✅ Elfogadom a felhasználási feltételeket és az adatvédelmi szabályzatot")
        
        submit_button = st.form_submit_button("📝 Regisztráció", use_container_width=True)
        
        if submit_button:
            # Validáció
            errors = []
            
            if not username or not email or not password or not password_confirm:
                errors.append("❌ Minden mezőt ki kell tölteni!")
            
            if not terms_accepted:
                errors.append("❌ El kell fogadnod a felhasználási feltételeket!")
            
            # Felhasználónév validálás
            username_valid, username_error = is_valid_username(username)
            if not username_valid:
                errors.append(f"❌ {username_error}")
            
            # Email validálás
            if email and not is_valid_email(email):
                errors.append("❌ Érvénytelen email cím formátum!")
            
            # Jelszó validálás
            password_valid, password_error = is_valid_password(password)
            if not password_valid:
                errors.append(f"❌ {password_error}")
            
            # Jelszó egyezés
            if password != password_confirm:
                errors.append("❌ A jelszavak nem egyeznek!")
            
            # Ha van hiba, megjeleníjük
            if errors:
                for error in errors:
                    st.error(error)
                return
            
            # Regisztráció
            success, message = create_user(username, email, password)
            
            if success:
                st.success(f"✅ {message}")
                st.info("🎉 Most már bejelentkezhetsz!")
                
                # Automatikus bejelentkezés
                auth_success, user_data = authenticate_user(username, password)
                if auth_success:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_data['id']
                    st.session_state.username = user_data['username']
                    st.session_state.email = user_data['email']
                    st.rerun()
            else:
                st.error(f"❌ {message}")

def logout_user():
    """Felhasználó kijelentkeztetése"""
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.email = None
    
    # Töröljük az összes session state-et
    for key in list(st.session_state.keys()):
        if key not in ['logged_in', 'user_id', 'username', 'email']:
            del st.session_state[key]

def require_login():
    """Bejelentkezés ellenőrzése (decorator-szerű funkció)"""
    if not st.session_state.get('logged_in', False):
        st.warning("⚠️ Ehhez a funkcióhoz be kell jelentkezned!")
        st.stop()
        return False
    return True

def get_current_user():
    """Aktuális felhasználó adatainak lekérése"""
    if st.session_state.get('logged_in', False):
        return {
            'id': st.session_state.user_id,
            'username': st.session_state.username,
            'email': st.session_state.email
        }
    return None

# Hasznos wrapper függvény az oldalakhoz
def with_auth(page_function):
    """Wrapper függvény, ami ellenőrzi a bejelentkezést"""
    def wrapper(*args, **kwargs):
        if require_login():
            return page_function(*args, **kwargs)
    return wrapper

# Felhasználási feltételek (egyszerű verzió)
def show_terms_modal():
    """Felhasználási feltételek modal"""
    if st.button("📋 Felhasználási feltételek"):
        with st.expander("📋 Felhasználási feltételek és Adatvédelmi szabályzat", expanded=True):
            st.markdown("""
            ## Felhasználási feltételek
            
            ### 1. Általános rendelkezések
            - A platform kártyagyűjtők közötti csere és eladás megkönnyítésére szolgál
            - A felhasználók felelősek a megadott információk pontosságáért
            - Tilos bármilyen káros, sértő vagy illegális tartalom közzététele
            
            ### 2. Felelősség
            - A platform nem vállal felelősséget a felhasználók közötti tranzakciókért
            - A cserék és eladások a felhasználók saját felelősségére történnek
            - Ajánlott óvatosság és megfelelő ellenőrzés minden tranzakció előtt
            
            ### 3. Adatvédelem
            - Az adatokat kizárólag a platform működtetéséhez használjuk fel
            - Nem adjuk át harmadik félnek személyes adatokat
            - A jelszavak titkosítva tárolódnak
            
            ### 4. Viselkedési szabályok
            - Tiszteletteljes kommunikáció elvárva
            - Spam és kéretlen üzenetek tiltva
            - Hamis információk megadása tiltva
            
            Frissítve: 2024. augusztus
            """)
            
            if st.button("✅ Elfogadom", key="accept_terms"):
                st.success("Feltételek elfogadva!")
                return True
    return False