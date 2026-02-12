import streamlit as st
import pandas as pd
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURAZIONE SMTP ---
# Sostituisci con i tuoi dati reali e una "Password per le App"
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
    # Inizializza Menu Settimanale
    if not os.path.exists(MENU_FILE):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
        pd.DataFrame({
            'Giorno': giorni,
            'Principale': ['Pasta'] * 5,
            'Contorno': ['Insalata'] * 5,
            'Extra': ['Frutta/Acqua'] * 5
        }).to_csv(MENU_FILE, index=False)
    
    # Inizializza Storico Ordini
    if not os.path.exists(ORDINI_FILE):
        pd.DataFrame(columns=['Data', 'User', 'Iniziali', 'Scelta', 'Note']).to_csv(ORDINI_FILE, index=False)

    # Inizializza Database Utenti (Admin e alcuni utenti di test)
    if not os.path.exists(UTENTI_FILE):
        pd.DataFrame([
            {'User': 'Admin', 'Password': '123', 'Email': '', 'Ruolo': 'Admin'},
            {'User': 'walid.ouakili', 'Password': '456', 'Email': '', 'Ruolo': 'User'}
        ]).to_csv(UTENTI_FILE, index=False)

init_all()

# --- FUNZIONI UTILITY ---
def invia_email(destinatari, oggetto, corpo):
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_MITTENTE, PASSWORD_MITTENTE)
        for mail in destinatari:
            if mail:
                msg = MIMEText(corpo)
                msg['Subject'] = oggetto
                msg['To'] = mail
                server.send_message(msg)
        server.quit()
    except:
        pass # Silenzioso se non configurato

def get_iniziali(nome):
    parti = nome.split()
    return f"{parti[0][0]}.{parti[1][0]}." if len(parti) >= 2 else nome[:2].upper()

# --- LOGICA DI ACCESSO ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍴 Portale Mensa Aziendale")
    u_db = pd.read_csv(UTENTI_FILE)
    user_input = st.selectbox("Seleziona Utente", [""] + u_db['User'].tolist())
    pass_input = st.text_input("Password", type="password")
    
    if st.button("Accedi"):
        user_row = u_db[(u_db['User'] == user_input) & (u_db['Password'] == str(pass_input))]
        if not user_row.empty:
            st.session_state.auth = True
            st.session_state.user = user_input
            st.session_state.ruolo = user_row.iloc[0]['Ruolo']
            st.rerun()
        else:
            st.error("Credenziali non corrette")
else:
    # --- APP DOPO LOGIN ---
    st.sidebar.title(f"Benvenuto, {st.session_state.user}")
    
    # Sezione Profilo in Sidebar
    with st.sidebar.expander("Il mio Profilo"):
        u_db = pd.read_csv(UTENTI_FILE)
        current_email = u_db.loc[u_db['User'] == st.session_state.user, 'Email'].values[0]
        nuova_mail = st.text_input("Aggiorna Email", value=str(current_email) if str(current_email) != 'nan' else "")
        if st.button("Salva Profilo"):
            u_db.loc[u_db['User'] == st.session_state.user, 'Email'] = nuova_mail
            u_db.to_csv(UTENTI_FILE, index=False)
            st.success("Profilo aggiornato")

    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    tab_menu, tab_admin, tab_ristorante = st.tabs(["📅 Menu e Ordini", "🛡️ Amministrazione", "👨‍🍳 Cucina"])

    # --- TAB MENU: ORDINI UTENTE ---
    with tab_menu:
        st.header("Calendario Settimanale")
        menu_df = pd.read_csv(MENU_FILE)
        st.dataframe(menu_df, use_container_width=True, hide_index=True)

        st.divider()
        oggi_str = datetime.now().strftime("%Y-%m-%d")
        
        # Stato Blocco Admin (Simulato con session_state per semplicità)
        if 'menu_aperto' not in st.session_state:
            st.session_state.menu_aperto = False

        if not st.session_state.menu_aperto:
            st.warning("⚠️ Le ordinazioni per oggi sono chiuse o non ancora sbloccate dall'Admin.")
        else:
            st.subheader(f"Ordine per oggi: {oggi_str}")
            ordini_df = pd.read_csv(ORDINI_FILE)
            mio_ordine = ordini_df[(ordini_df['Data'] == oggi_str) & (ordini_df['User'] == st.session_state.user)]

            if not mio_ordine.empty:
                st.info(f"Hai già ordinato: {mio_ordine.iloc[0]['Scelta']}")
                if st.button("Elimina il mio ordine"):
                    ordini_df = ordini_df[~((ordini_df['Data'] == oggi_str) & (ordini_df['User'] == st.session_state.user))]
                    ordini_df.to_csv(ORDINI_FILE, index=False)
                    st.rerun()
            else:
                with st.form("form_ordine"):
                    # Ottieni piatti di oggi dal menu settimanale
                    giorno_sett = datetime.now().strftime("%A") # Da mappare in italiano se necessario
                    pasto_default = "Menu del giorno" 
                    scelta_pasto = st.selectbox("Seleziona Pasto", ["Completo", "Solo Primo", "Solo Secondo"])
                    note_pasto = st.text_area("Note (es. No cipolla, Gluten Free)")
                    
                    if st.form_submit_button("Invia Ordine"):
                        iniz = get_iniziali(st.session_state.user)
                        nuovo_o = pd.DataFrame([[oggi_str, st.session_state.user, iniz, scelta_pasto, note_pasto]], 
                                               columns=['Data', 'User', 'Iniziali', 'Scelta', 'Note'])
                        nuovo_o.to_csv(ORDINI_FILE, mode='a', header=False, index=False)
                        st.success("Ordine registrato con successo!")
                        st.rerun()

    # --- TAB ADMIN: GESTIONE UTENTI E BLOCCO ---
    with tab_admin:
        if st.session_state.ruolo != 'Admin':
            st.error("Accesso riservato agli amministratori.")
        else:
            st.header("Controllo Accessi")
            st.session_state.menu_aperto = st.toggle("Sblocca ordinazioni per tutti gli utenti", value=st.session_state.menu_aperto)
            
            st.subheader("Stato Utenti e Ordini")
            u_db = pd.read_csv(UTENTI_FILE)
            ordini_df = pd.read_csv(ORDINI_FILE)
            ordini_oggi = ordini_df[ordini_df['Data'] == oggi_str]
            
            monitor_df = u_db[['User', 'Ruolo']].copy()
            monitor_df['Ha Ordinato'] = monitor_df['User'].isin(ordini_oggi['User'])
            st.table(monitor_df)

    # --- TAB RISTORANTE: CUCINA E MENU ---
    with tab_ristorante:
        if st.session_state.ruolo != 'Admin' and st.session_state.user != 'Ristorante':
            st.error("Accesso riservato al Ristorante/Admin.")
        else:
            st.header("Gestione Cucina")
            
            # Riepilogo Ordini
            ordini_df = pd.read_csv(ORDINI_FILE)
            ordini_oggi = ordini_df[ordini_df['Data'] == oggi_str]
            
            if ordini_oggi.empty:
                st.info("Nessun ordine ricevuto per oggi.")
            else:
                riepilogo = ordini_oggi.groupby('Scelta')['Iniziali'].apply(lambda x: ', '.join(x)).reset_index()
                riepilogo['Conteggio'] = ordini_oggi.groupby('Scelta')['User'].transform('count').unique() # Semplificato
                st.subheader("Conteggio Pasti per lo Chef")
                st.table(riepilogo)

            st.divider()
            st.subheader("Aggiorna Menu Settimanale")
            menu_df = pd.read_csv(MENU_FILE)
            nuovo_menu = st.data_editor(menu_df, key="editor_settimanale")
            
            col1, col2 = st.columns(2)
            if col1.button("Salva e Notifica Nuovo Menu"):
                nuovo_menu.to_csv(MENU_FILE, index=False)
                u_db = pd.read_csv(UTENTI_FILE)
                invia_email(u_db['Email'].tolist(), "Nuovo Menu Settimanale Pubblicato", "Ciao! Il nuovo menu della settimana è disponibile online.")
                st.success("Menu salvato e mail inviate!")
            
            if col2.button("Notifica Modifica Menu"):
                nuovo_menu.to_csv(MENU_FILE, index=False)
                u_db = pd.read_csv(UTENTI_FILE)
                invia_email(u_db['Email'].tolist(), "Aggiornamento Menu", "Attenzione: sono state apportate modifiche al menu della settimana.")
                st.success("Notifica di modifica inviata!")
