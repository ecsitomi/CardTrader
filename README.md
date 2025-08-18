# 🃏 Kártya Csere Platform - Újragondolt Struktúra

Sport kártyák cseréjére és eladására szolgáló online platform sorozat-alapú rendszerrel.

## 🎯 Új adatbázis struktúra

### 📊 Logika:
1. **Felhasználó** regisztrál
2. **Sorozatok** (pl. FIFA 2023, NBA 2024) 
3. **Kártyák** sorozatonként 1-400-ig számozva
4. **6 változat** minden kártyához: Base, Silver, Pink, Red, Blue, Epic
5. **Státusz** minden kártyának: Megvan / Cserélnék / Eladnám (ár megadással)

### 💎 Kártya változatok:
- **Base** (szürke) - Alapkártya
- **Silver** (ezüst) - Ezüst változat  
- **Pink** (rózsaszín) - Rózsaszín változat
- **Red** (piros) - Piros változat
- **Blue** (kék) - Kék változat
- **Epic** (arany) - Legritkább változat

## 🚀 Gyors indítás

### 1. Fájlok elhelyezése
Hozd létre a projekt mappáját és másold be a fájlokat:

```
kártya_platform/
│
├── main.py
├── database.py
├── auth.py
├── utils.py
├── requirements.txt
│
└── pages/
    ├── 01_🏠_Főoldal.py         (üresen hagyhatod)
    ├── 02_🃏_Kártyáim.py
    ├── 03_🔍_Keresés.py         (később)
    ├── 04_⭐_Kívánságlista.py   (később)
    ├── 05_📨_Üzenetek.py        (később)
    └── 06_👤_Profil.py          (később)
```

### 2. Telepítés

```bash
# Virtual environment létrehozása (ajánlott)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Függőségek telepítése
pip install streamlit

# Vagy requirements.txt használata
pip install -r requirements.txt
```

### 3. Indítás

```bash
cd kártya_platform
streamlit run main.py
```

### 4. Első használat

1. **Regisztráció:** Hozz létre egy felhasználói fiókot
2. **Tesztadatok:** Az első indításkor automatikusan létrejönnek:
   - FIFA 2023 sorozat (Messi, Ronaldo, stb.)
   - NBA 2023-24 sorozat (LeBron, Curry, stb.)  
   - Formula 1 2023 sorozat (Verstappen, Hamilton, stb.)
3. **Kártyák hozzáadása:** 
   - Válassz sorozatot → kártyát → változatot → státuszt
   - Vagy hozz létre új sorozatokat és kártyákat
4. **Gyűjtemény kezelése:** 
   - Jelöld be, mit szeretnél cserélni/eladni
   - Add meg az árakat eladáshoz
   - Kövesd a teljesítettséged sorozatonként

## 📊 Funkciók

### ✅ Elkészült (MVP v2.1)
- 👤 Felhasználói regisztráció/bejelentkezés
- 📚 Sorozat kezelés (létrehozás, böngészés)
- 🃏 Kártya hozzáadása (1-400 számozással)
- 💎 6 különböző kártya változat
- 📦 Gyűjtemény megtekintése szűrőkkel
- 📊 Státusz kezelés (megvan/cserélnék/eladnám)
- 💰 Ár megadás eladáshoz
- 📈 Részletes statisztikák
- 🎯 Sorozat teljesítettség
- 🤖 **INTELLIGENS MATCHMAKING ALGORITMUS**
- 🔥 **RANGSOROLT TALÁLATOK**
- 📊 **PIACI INSIGHTS ÉS ELEMZÉSEK**
- 💾 SQLite adatbázis

### 🚧 Fejlesztés alatt
- 🔍 Kártya keresés és böngészés
- ⭐ Kívánságlista kezelés  
- 📨 Üzenetküldés rendszer
- 🎯 Automatikus matchmaking
- 👤 Felhasználói profil

### 🔮 Jövőbeli funkciók
- 📷 Kártya képek feltöltése
- 💹 Ár statisztikák és trendek
- 🔔 Push értesítések
- 📱 Mobil optimalizáció
- 🌐 Deploy production környezetbe
- 🏆 Ranglisták és achievement-ek

## 🛠️ Technológiai stack

- **Frontend:** Streamlit
- **Backend:** Python
- **Adatbázis:** SQLite
- **Hitelesítés:** Egyszerű hash-alapú
- **Deploy:** Streamlit Cloud (ingyenes)

## 📁 Fájlok leírása

- `main.py` - Főalkalmazás, routing, bejelentkezés
- `database.py` - Adatbázis műveletek és táblák
- `auth.py` - Regisztráció, bejelentkezés, validáció
- `utils.py` - Segédfunkciók, formázás, statisztikák
- `pages/` - Streamlit oldalak (multipage app)

## 🐛 Hibaelhárítás

### Gyakori problémák:

**ModuleNotFoundError:**
```bash
pip install streamlit
```

**Adatbázis hiba:**
```bash
# Töröld a cards_platform.db fájlt és indítsd újra
rm cards_platform.db
```

**Import hiba a pages mappában:**
```python
# Minden pages/*.py fájl tetején:
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
```

## 🚀 Deploy opciók

### Streamlit Cloud (ajánlott kezdetnek)
1. GitHub repo létrehozása
2. Streamlit Cloud regisztráció
3. Repo csatlakoztatása
4. Automatikus deploy

### Alternatívák:
- **Railway** - FastAPI-hoz jobb
- **Render** - PostgreSQL support
- **Heroku** - hagyományos choice

## 📝 Következő lépések

1. **Tesztelés** - Próbáld ki az új intelligens matchmaking-et! 🤖
2. **Kívánságlista oldal** - Mit keresek funkció (a matchmaking alapja)
3. **Üzenetek** - Levél típusú üzenetváltás
4. **Keresés oldal** - Kártyák böngészése és szűrése  
5. **Képek** - Kártya képek feltöltése
6. **Statisztikák** - Ár trendek és piaci adatok
7. **Értesítések** - Új match-ek esetén
8. **API** - Külső kártya adatbázisok integrálása

## 🎯 Új funkcionalitások

### Sorozat kezelés:
- Új sorozatok létrehozása (név, év, sport)
- Sorozatonként 1-400 kártya
- Teljesítettség követése

### Kártya változatok:
- Minden kártyának 6 változata van
- Színkódolt megjelenítés
- Ritkasági szintek

### Státusz rendszer:
- **Megvan**: Csak a gyűjteményben van
- **Cserélnék**: Cserére elérhető
- **Eladnám**: Eladásra kínált (ár megadással)

## 🤖 Intelligens Matchmaking Algoritmus

### 🎯 Hogyan működik?

**1. Amit keresek (vásárlás/csere):**
- Lekéri a kívánságlistámat
- Megkeresi, ki kínálja ezeket a kártyákat
- Rangsorolja őket intelligens pontszám alapján

**2. Amit kínálok (eladás/csere):**
- Lekéri a cserére/eladásra kínált kártyáimat
- Megkeresi, ki keresi ezeket
- Mutatja az érdeklődési szintet

### 📊 Rangsorolási algoritmus:

**Match pontszám kalkuláció (max. 145 pont):**
- 🎯 **Kívánságlista prioritás:** 10-40 pont
  - Sürgős (4): 40 pont
  - Magas (3): 30 pont  
  - Közepes (2): 20 pont
  - Alacsony (1): 10 pont

- 💎 **Ritkasági bónusz:** 5-30 pont
  - Epic (6): 30 pont
  - Blue (5): 25 pont
  - Red (4): 20 pont
  - Pink (3): 15 pont
  - Silver (2): 10 pont
  - Base (1): 5 pont

- 📊 **Kereslet/kínálat arány:** 0-30 pont
  - Nincs kínálat: 30 pont
  - 1 db kínálat: 25 pont
  - 2 db kínálat: 20 pont
  - 3-5 db kínálat: 15 pont
  - Sok kínálat: 0-10 pont

- 👥 **Népszerűség bónusz:** 0-20 pont
  - Kereslet × 3 pont (max. 20)

- 💰 **Ár megfelelőség:** 0-15 pont
  - Csere: 15 pont
  - Eladás max. áron belül: 15 pont
  - 10% túllépés: 10 pont
  - 20% túllépés: 5 pont
  - Túl drága: 0 pont

- 🕒 **Frissesség bónusz:** 0-10 pont
  - Ma hozzáadva: 10 pont
  - 1-3 napja: 7 pont
  - 4-7 napja: 5 pont
  - 8-30 napja: 2 pont

### 🏆 Match minősítés:
- **🔥 85+ pont:** Kiváló match!
- **⭐ 60-84 pont:** Jó match
- **👍 40-59 pont:** Megfelelő match
- **📊 <40 pont:** Gyenge match

### 📈 Piaci insights:
- **Legnépszerűbb kártyáim:** Mit keresnek a legtöbben
- **Legritkább kártyáim:** Legértékesebb tulajdonaim
- **Ár összehasonlítások:** Piaci árakhoz viszonyítás
- **Érdeklődési szintek:** Ki mennyire akarja a kártyáimat

## 🤝 Közreműködés

Ez egy learning project. Fejlesztési ötletek:
- UI/UX javítások
- Új funkciók
- Performance optimalizáció
- Biztonsági fejlesztések

---

**Verzió:** 2.1 - Intelligens Matchmaking  
**Készítette:** Junior Developer ➜ Senior Developer mentoring  
**Technológia:** Python + Streamlit + SQLite + AI Algoritmus  
**Cél:** Fejlett kártyagyűjtő platform intelligens javaslatokkal  

**Változások v2.1-ben:**
- 🤖 **Intelligens matchmaking algoritmus** 145 pontos értékeléssel
- 🎯 **Rangsorolt találatok** kereslet/kínálat alapján
- 📊 **Piaci insights** és elemzések
- 💰 **Ár összehasonlítások** piaci adatokkal
- 🔥 **Fordított matchmaking** - ki keresi az én kártyáimat
- 📈 **Részletes statisztikák** demand/supply arányokkal
- ⚡ **Optimalizált algoritmus** komplex SQL lekérdezésekkel

**Technikai fejlesztések:**
- Advanced SQL queries with CTE-k
- Market analysis algorithms  
- Price recommendation engine
- Multi-criteria decision making (MCDM)
- Real-time scoring system