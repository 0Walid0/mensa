import streamlit as st
import pandas as pd
from datetime import datetime
import os
import pytz
import smtplib
from email.mime.text import MIMEText
import urllib.parse

# --- CONFIGURAZIONE FILE ---
MENU_FILE = "menu_settimanale.csv"
ORDINI_FILE = "ordini_storico.csv"
UTENTI_FILE = "database_utenti.csv"
SETTINGS_FILE = "settings.csv"

# --- CONFIGURAZIONE EMAIL ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_MITTENTE = "tua_email@gmail.com" 
PASS_EMAIL = "xxxx xxxx xxxx xxxx" 

# --- INIZIALIZZAZIONE ---
def init_all():
    if not os.path.exists(MENU_FILE):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
        pd.DataFrame({'Giorno': giorni, 'Principale': '', 'Contorno': '', 'Dolce': '', 'Bevanda': ''}).to_csv(MENU_FILE, index=False)
    
    if not os.path.exists(ORDINI_FILE):
        pd.DataFrame(columns=['Data', 'Giorno', 'User', 'Iniziali', 'Dettaglio']).to_csv(ORDINI_FILE, index=False)

    if not os.path.exists(UTENTI_FILE):
        pd.DataFrame([
            {'User': 'Admin', 'Password': '123', 'Email': '', 'Ruolo': 'Admin', 'PrimoAccesso': False},
            {'User': 'walid.ouakili', 'Password': '456', 'Email': '', 'Ruolo': 'User', 'PrimoAccesso': True},
            {'User': 'Ristorante', 'Password': '789', 'Email': '', 'Ruolo': 'Ristorante', 'PrimoAccesso': False}
        ]).to_csv(UTENTI_FILE, index=False)
        
    if not os.path.exists(SETTINGS_FILE):
        pd.DataFrame([{'chiusura': '10:30', 'sblocco_manuale': False, 'richiesta_apertura': False}]).to_csv(SETTINGS_FILE, index=False)

init_all()

# --- FUNZIONI CORE ---
def invia_email_menu(testo_menu):
    u_db = pd.read_csv(UTENTI_FILE)
    destinatari = u_db[(u_db['Email'] != '') & (u_db['Email'].notna())]['Email'].tolist()
    if not destinatari: return
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_MITTENTE, PASS_EMAIL)
        msg = MIMEText(f"Il ristorante ha aggiornato il menu:\n\n{testo_menu}")
        msg['Subject'] = "🍴 Nuovo Menu Mensa Disponibile"
        msg['From'] = EMAIL_MITTENTE
        msg['To'] = ", ".join(destinatari)
        server.sendmail(EMAIL_MITTENTE, destinatari, msg.as_string())
        server.quit()
        st.success("Notifiche email inviate!")
    except Exception as e:
        st.error(f"Errore email: {e}")

def get_iniziali(nome):
    parti = str(nome).replace('.', ' ').split()
    return f"{parti[0][0].upper()}.{parti[1][0].upper()}." if len(parti) >= 2 else str(nome)[:2].upper()

# --- LOGICA DI ACCESSO ---
u_db = pd.read_csv(UTENTI_FILE)
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍴 Portale Mensa Aziendale")
    u_sel = st.selectbox("Seleziona Utente", [""] + u_db['User'].tolist())
    p_sel = st.text_input("Password", type="password")
    if st.button("Accedi"):
        row = u_db[(u_db['User'] == u_sel) & (u_db['Password'].astype(str) == str(p_sel))]
        if not row.empty:
            st.session_state.auth, st.session_state.user, st.session_state.ruolo = True, u_sel, row.iloc[0]['Ruolo']
            st.session_state.primo = row.iloc[0]['PrimoAccesso']
            st.rerun()
        else: st.error("Credenziali non corrette")
else:
    # --- PROFILO PRIMO ACCESSO ---
    if st.session_state.primo and st.session_state.ruolo == 'User':
        st.warning("🔒 Configura il tuo profilo per continuare")
        with st.form("setup"):
            mail = st.text_input("Email Aziendale")
            pw = st.text_input("Nuova Password", type="password")
            if st.form_submit_button("Salva Profilo"):
                u_db.loc[u_db['User'] == st.session_state.user, ['Email', 'Password', 'PrimoAccesso']] = [mail, pw, False]
                u_db.to_csv(UTENTI_FILE, index=False)
                st.session_state.primo = False
                st.rerun()
        st.stop()

    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Logout"): 
        st.session_state.auth = False
        st.rerun()

    tabs = st.tabs(["📝 Ordini", "🛡️ Admin", "👨‍🍳 Ristorante"])

    # --- TAB ORDINI ---
    with tabs[0]:
        if st.session_state.ruolo in ['User', 'Admin']:
            s = pd.read_csv(SETTINGS_FILE).iloc[0]
            if not s['sblocco_manuale']:
                st.error("🚫 Menu Chiuso.")
                if st.button("🔔 Richiedi apertura"):
                    sd = pd.read_csv(SETTINGS_FILE)
                    sd.at[0, 'richiesta_apertura'] = True
                    sd.to_csv(SETTINGS_FILE, index=False)
                    st.info("Richiesta inviata.")
            else:
                m = pd.read_csv(MENU_FILE)
                g = st.selectbox("Giorno", m['Giorno'].tolist())
                dati = m[m['Giorno'] == g].iloc[0]
                with st.form("ord"):
                    c1, c2 = st.columns(2)
                    p = c1.selectbox("Principale", dati['Principale'].split(','))
                    c = c1.selectbox("Contorno", dati['Contorno'].split(','))
                    do = c2.selectbox("Dolce", dati['Dolce'].split(','))
                    b = c2.selectbox("Bevanda", dati['Bevanda'].split(','))
                    if st.form_submit_button("Ordina"):
                        o = pd.read_csv(ORDINI_FILE)
                        o = o[~((o['Giorno'] == g) & (o['User'] == st.session_state.user))]
                        det = f"{p}|{c}|{do}|{b}"
                        new = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), g, st.session_state.user, get_iniziali(st.session_state.user), det]], columns=o.columns)
                        pd.concat([o, new]).to_csv(ORDINI_FILE, index=False)
                        st.success("Fatto!")
                        link = urllib.parse.quote(f"Ordine {g}: {det}")
                        st.markdown(f"[📲 WhatsApp Ristorante](https://wa.me/39333000000?text={link})")

    # --- TAB ADMIN ---
    with tabs[1]:
        if st.session_state.ruolo == 'Admin':
            sd = pd.read_csv(SETTINGS_FILE)
            if sd.iloc[0]['richiesta_apertura']: st.warning("📢 Richiesta apertura ricevuta!")
            sd.at[0, 'sblocco_manuale'] = st.toggle("Apri Menu", sd.iloc[0]['sblocco_manuale'])
            if st.button("Salva e Reset"):
                sd.at[0, 'richiesta_apertura'] = False
                sd.to_csv(SETTINGS_FILE, index=False)
                st.rerun()

    # --- TAB RISTORANTE ---
    with tabs[2]:
        if st.session_state.ruolo in ['Admin', 'Ristorante']:
            st.header("Gestione Menu")
            
            # OPZIONE 1: CARICAMENTO FILE
            with st.expander("📂 Carica Menu da Excel/CSV"):
                uploaded = st.file_uploader("Scegli un file (Colonne: Giorno, Principale, Contorno, Dolce, Bevanda)", type=['csv', 'xlsx'])
                if uploaded:
                    try:
                        new_m = pd.read_excel(uploaded) if uploaded.name.endswith('xlsx') else pd.read_csv(uploaded)
                        if st.button("Conferma Caricamento File"):
                            new_m.to_csv(MENU_FILE, index=False)
                            st.success("Menu caricato da file!")
                            invia_email_menu("Nuovo menu settimanale caricato da file Excel.")
                    except: st.error("Errore nel formato del file.")

            # OPZIONE 2: INSERIMENTO MANUALE
            with st.expander("✍️ Inserimento Manuale"):
                m_df = pd.read_csv(MENU_FILE)
                with st.form("manual"):
                    g_ed = st.selectbox("Giorno", m_df['Giorno'].tolist())
                    c1, c2 = st.columns(2)
                    p_n = c1.text_area("Principali (virgola per separare)")
                    c_n = c1.text_area("Contorni")
                    d_n = c2.text_area("Dolci")
                    b_n = c2.text_area("Bevande")
                    if st.form_submit_button("Aggiorna e Invia Mail"):
                        m_df.loc[m_df['Giorno'] == g_ed, ['Principale','Contorno','Dolce','Bevanda']] = [p_n, c_n, d_n, b_n]
                        m_df.to_csv(MENU_FILE, index=False)
                        invia_email_menu(f"Aggiornamento {g_ed}: {p_n}")

            # RIEPILOGO CHEF
            st.divider()
            o_df = pd.read_csv(ORDINI_FILE)
            g_v = st.selectbox("Vedi per:", ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì'])
            dg = o_df[o_df['Giorno'] == g_v]
            if not dg.empty:
                st.write(f"Totali per {g_v}:")
                choices = dg['Dettaglio'].apply(lambda x: x.split('|')[0])
                st.write(choices.value_counts())
                st.dataframe(dg[['Iniziali', 'Dettaglio']])