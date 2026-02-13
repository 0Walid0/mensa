import streamlit as st
import pandas as pd
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURAZIONE SMTP ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_MITTENTE = "tua_email@gmail.com" 
PASSWORD_MITTENTE = "xxxx xxxx xxxx xxxx" 

# --- FILE DATABASE ---
MENU_FILE = "menu_settimanale.csv"
ORDINI_FILE = "ordini_storico.csv"
UTENTI_FILE = "database_utenti.csv"

# --- INIZIALIZZAZIONE DATI ---
def init_all():
    if not os.path.exists(MENU_FILE):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
        pd.DataFrame({
            'Giorno': giorni,
            'Principale': ['Pasta'] * 5,
            'Contorno': ['Insalata'] * 5,
            'Extra': ['Frutta/Acqua'] * 5
        }).to_csv(MENU_FILE, index=False)
    
    if not os.path.exists(ORDINI_FILE):
        pd.DataFrame(columns=['Data', 'User', 'Iniziali', 'Scelta', 'Note']).to_csv(ORDINI_FILE, index=False)

    # Inizializzazione Database Utenti (Password forzata come stringa)
    if not os.path.exists(UTENTI_FILE):
        pd.DataFrame([
            {'User': 'Admin', 'Password': '123', 'Email': '', 'Ruolo': 'Admin'},
            {'User': 'walid.ouakili', 'Password': '456', 'Email': '', 'Ruolo': 'User'}
        ]).to_csv(UTENTI_FILE, index=False)

init_all()

# --- FUNZIONI UTILITY ---
def get_iniziali(nome):
    nome_pulito = str(nome).replace('.', ' ')
    parti = nome_pulito.split()
    if len(parti) >= 2:
        return f"{parti[0][0].upper()}.{parti[1][0].upper()}."
    return str(nome)[:2].upper()

# --- LOGICA DI ACCESSO ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

# Caricamento database utenti
u_db = pd.read_csv(UTENTI_FILE)

if not st.session_state.auth:
    st.title("🍴 Portale Mensa Aziendale")
    
    # Pulizia automatica degli utenti nel database per il confronto
    u_db['User'] = u_db['User'].astype(str).str.strip()
    u_db['Password'] = u_db['Password'].astype(str).str.strip()
    
    user_input = st.selectbox("Seleziona Utente", [""] + u_db['User'].tolist())
    pass_input = st.text_input("Password", type="password")
    
    # --- SEZIONE DEBUG (Commenta queste righe dopo il successo) ---
    # st.write("Database attuale:", u_db) 
    # st.write(f"Tentativo con: '{user_input}' e '{pass_input}'")

    if st.button("Accedi"):
        # Confronto super-sicuro: forziamo tutto a stringa e togliamo gli spazi
        user_row = u_db[
            (u_db['User'] == str(user_input).strip()) & 
            (u_db['Password'] == str(pass_input).strip())
        ]
        
        if not user_row.empty:
            st.session_state.auth = True
            st.session_state.user = user_input
            st.session_state.ruolo = user_row.iloc[0]['Ruolo']
            st.rerun()
        else:
            st.error("Credenziali non corrette")
else:
    # --- APP DOPO IL LOGIN ---
    st.sidebar.title(f"👤 {st.session_state.user}")
    
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    tab_menu, tab_admin, tab_ristorante = st.tabs(["📅 Menu e Ordini", "🛡️ Amministrazione", "👨‍🍳 Cucina"])

    # --- TAB MENU: ORDINI ---
    with tab_menu:
        st.header("Calendario Settimanale")
        menu_df = pd.read_csv(MENU_FILE)
        st.dataframe(menu_df, use_container_width=True, hide_index=True)

        st.divider()
        oggi_str = datetime.now().strftime("%Y-%m-%d")
        
        if 'menu_aperto' not in st.session_state:
            st.session_state.menu_aperto = False

        if not st.session_state.menu_aperto and st.session_state.ruolo != 'Admin':
            st.warning("⚠️ Le ordinazioni per oggi sono chiuse.")
        else:
            st.subheader(f"Ordine per oggi: {oggi_str}")
            ordini_df = pd.read_csv(ORDINI_FILE)
            mio_ordine = ordini_df[(ordini_df['Data'] == oggi_str) & (ordini_df['User'] == st.session_state.user)]

            if not mio_ordine.empty:
                st.info(f"Hai ordinato: {mio_ordine.iloc[0]['Scelta']}")
                if st.button("Elimina il mio ordine"):
                    ordini_df = ordini_df[~((ordini_df['Data'] == oggi_str) & (ordini_df['User'] == st.session_state.user))]
                    ordini_df.to_csv(ORDINI_FILE, index=False)
                    st.rerun()
            else:
                with st.form("form_ordine", clear_on_submit=True):
                    scelta_pasto = st.selectbox("Seleziona Pasto", ["Menu Completo", "Solo Primo", "Solo Secondo"])
                    note_pasto = st.text_area("Note")
                    if st.form_submit_button("Invia Ordine"):
                        iniz = get_iniziali(st.session_state.user)
                        nuovo_o = pd.DataFrame([[oggi_str, st.session_state.user, iniz, scelta_pasto, note_pasto]], 
                                               columns=['Data', 'User', 'Iniziali', 'Scelta', 'Note'])
                        nuovo_o.to_csv(ORDINI_FILE, mode='a', header=False, index=False)
                        st.success("Ordine registrato!")
                        st.rerun()

    # --- TAB ADMIN ---
    with tab_admin:
        if st.session_state.ruolo != 'Admin':
            st.error("Accesso riservato.")
        else:
            st.header("Controllo Accessi")
            st.session_state.menu_aperto = st.toggle("Sblocca ordinazioni", value=st.session_state.menu_aperto)
            
            ordini_oggi = pd.read_csv(ORDINI_FILE)
            ordini_oggi = ordini_oggi[ordini_oggi['Data'] == oggi_str]
            monitor_df = u_db[['User', 'Ruolo']].copy()
            monitor_df['Stato'] = monitor_df['User'].apply(lambda x: "✅" if x in ordini_oggi['User'].values else "❌")
            st.table(monitor_df)