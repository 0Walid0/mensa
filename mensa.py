import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURAZIONE SMTP (Da compilare per le email) ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "tua_email@gmail.com"
SENDER_PASSWORD = "tua_password_app" # Usa una password per le app di Google

# --- DATABASE FILES ---
MENU_FILE = "menu_settimanale.csv"
ORDINI_FILE = "ordini_storico.csv"
USER_FILE = "profili_utenti.csv"

# --- INIZIALIZZAZIONE DATI ---
def init_db():
    if not os.path.exists(MENU_FILE):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
        df = pd.DataFrame({
            'Giorno': giorni,
            'Principale': ['Pasta'] * 5,
            'Contorno': ['Insalata'] * 5,
            'Extra': ['Frutta'] * 5
        })
        df.to_csv(MENU_FILE, index=False)
    
    if not os.path.exists(ORDINI_FILE):
        pd.DataFrame(columns=['Data', 'User', 'Iniziali', 'Pasto', 'Status']).to_csv(ORDINI_FILE, index=False)

    if 'admin_lock' not in st.session_state:
        st.session_state['admin_lock'] = True # Menu chiuso di default

# --- FUNZIONI EMAIL ---
def invia_notifica(destinatari, oggetto, messaggio):
    try:
        msg = MIMEText(messaggio)
        msg['Subject'] = oggetto
        msg['From'] = SENDER_EMAIL
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            for email in destinatari:
                msg['To'] = email
                server.send_message(msg)
        st.success("Notifiche email inviate!")
    except Exception as e:
        st.error(f"Errore invio email: {e}")

# --- LOGICA APP ---
st.set_page_config(page_title="Mensa Pro 2026", layout="wide")

# Login Simpatico
if 'auth' not in st.session_state:
    st.title("🔐 Accesso Mensa Aziendale")
    user = st.text_input("Nome Utente")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if user in ["Admin", "Ristorante"] or user.startswith("User"):
            st.session_state['auth'] = True
            st.session_state['user'] = user
            st.session_state['is_admin'] = (user == "Admin")
            st.rerun()
else:
    # Sidebar: Profilo e Logout
    st.sidebar.title(f"👤 {st.session_state['user']}")
    email_utente = st.sidebar.text_input("La tua Mail", placeholder="esempio@ditta.it")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📅 Menu e Ordini", "📊 Dashboard Admin", "👨‍🍳 Area Ristorante"])

    # --- TAB 1: UTENTE (VISUALIZZAZIONE CALENDARIO) ---
    with tab1:
        st.header("Menu Settimanale")
        menu_df = pd.read_csv(MENU_FILE)
        st.table(menu_df) # Visualizzazione a calendario

        st.divider()
        
        oggi = datetime.now().strftime("%A") # In inglese, andrebbe mappato
        data_oggi = datetime.now().strftime("%Y-%m-%d")

        st.subheader(f"Ordine per oggi ({data_oggi})")
        
        # Controllo Lock Admin
        if st.session_state.get('admin_lock', True) and not st.session_state['is_admin']:
            st.warning("⚠️ Il menu è attualmente chiuso dall'amministratore.")
        else:
            ordini_df = pd.read_csv(ORDINI_FILE)
            gia_ordinato = not ordini_df[(ordini_df['Data'] == data_oggi) & (ordini_df['User'] == st.session_state['user'])].empty

            if gia_ordinato:
                st.info("Hai già ordinato per oggi.")
                if st.button("Elimina il mio ordine"):
                    ordini_df = ordini_df[~((ordini_df['Data'] == data_oggi) & (ordini_df['User'] == st.session_state['user']))]
                    ordini_df.to_csv(ORDINI_FILE, index=False)
                    st.rerun()
            else:
                with st.form("nuovo_ordine"):
                    scelta = st.selectbox("Cosa vuoi mangiare?", ["Pasta", "Carne", "Insalatona"])
                    note = st.text_input("Note")
                    if st.form_submit_button("Conferma Ordine"):
                        # Salva ordine...
                        st.success("Ordine registrato!")

    # --- TAB 2: AMMINISTRATORE ---
    with tab3:
        if st.session_state['user'] == "Admin":
            st.header("Gestione Chiusura Menu")
            status = "CHIUSO" if st.session_state['admin_lock'] else "APERTO"
            st.write(f"Stato attuale: **{status}**")
            
            if st.button("Sblocca Menu per tutti"):
                st.session_state['admin_lock'] = False
                st.rerun()
            if st.button("Blocca Menu (Fine prenotazioni)"):
                st.session_state['admin_lock'] = True
                st.rerun()
            
            st.subheader("Stato Utenti")
            # Qui andrebbe una tabella che incrocia lista utenti con ordini del giorno
            st.write("Tabella monitoraggio utenti in fase di sviluppo...")

    # --- TAB 3: RISTORANTE ---
    with tab2:
        if st.session_state['user'] == "Ristorante" or st.session_state['is_admin']:
            st.header("Gestione Ristorante")
            
            # Modifica Menu e invio Mail
            with st.expander("Modifica Menu Settimanale"):
                nuovo_m = st.data_editor(menu_df)
                if st.button("Invia Notifica Modifica Menu"):
                    # invia_notifica([lista_mail], "Menu Modificato", "Il ristorante ha aggiornato il menu.")
                    nuovo_m.to_csv(MENU_FILE, index=False)

            st.divider()
            st.subheader("Riepilogo Ordini per la Cucina")
            # Logica conteggio:
            # conta = ordini_df['Pasto'].value_counts()
            # Mostra iniziali accanto a ogni piatto...
            st.info("Qui il ristorante vede: Piatto X -> Iniziali: W.K, M.R, G.B")
