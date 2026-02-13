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

# --- CONFIGURAZIONE EMAIL (PARAMETRI LIBRAESVA) ---
# Inserisci qui i dati del tuo pannello Libraesva
SMTP_SERVER = "INSERISCI_IP_O_FQDN_LIBRAESVA" 
SMTP_PORT = 587
EMAIL_MITTENTE = "IL_TUO_USERNAME_LIBRAESVA" 
PASS_EMAIL = "LA_TUA_PASSWORD_LIBRAESVA" 

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
    if not destinatati: return
    try:
        # Connessione autenticata tramite Libraesva
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() 
        server.login(EMAIL_MITTENTE, PASS_EMAIL)
        msg = MIMEText(f"Ciao! Il ristorante ha aggiornato il menu:\n\n{testo_menu}\n\nAccedi al portale per ordinare.")
        msg['Subject'] = "🍴 Nuovo Menu Mensa Disponibile"
        msg['From'] = f"Mensa Aziendale <{EMAIL_MITTENTE}>" 
        msg['To'] = ", ".join(destinatari)
        server.sendmail(EMAIL_MITTENTE, destinatari, msg.as_string())
        server.quit()
        st.success("Notifiche inviate con successo tramite Libraesva!")
    except Exception as e:
        st.error(f"Errore relay Libraesva: {e}")

def get_iniziali(nome):
    parti = str(nome).replace('.', ' ').split()
    return f"{parti[0][0].upper()}.{parti[1][0].upper()}." if len(parti) >= 2 else str(nome)[:2].upper()

# --- LOGICA DI ACCESSO ---
u_db = pd.read_csv(UTENTI_FILE)
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍴 Portale Mensa")
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
    # --- SETUP PRIMO ACCESSO (EMAIL E CAMBIO PASSWORD) ---
    if st.session_state.primo and st.session_state.ruolo == 'User':
        st.warning("🔒 Benvenuto! Completa il tuo profilo per continuare.")
        with st.form("setup"):
            mail = st.text_input("Inserisci la tua Email aziendale")
            pw = st.text_input("Inserisci una nuova Password", type="password")
            if st.form_submit_button("Salva e Accedi"):
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

    # --- TAB ORDINI (WHATSAPP + INTERNO) ---
    with tabs[0]:
        if st.session_state.ruolo in ['User', 'Admin']:
            s = pd.read_csv(SETTINGS_FILE).iloc[0]
            m = pd.read_csv(MENU_FILE)
            g = st.selectbox("Giorno", m['Giorno'].tolist())
            dati = m[m['Giorno'] == g].iloc[0]
            iniz = get_iniziali(st.session_state.user)

            if not s['sblocco_manuale']:
                st.error("🚫 Invio interno chiuso. Usa WhatsApp per l'invio diretto.")
                with st.container():
                    c1, c2 = st.columns(2)
                    p_w = c1.selectbox("Principale", dati['Principale'].split(','))
                    c_w = c1.selectbox("Contorno", dati['Contorno'].split(','))
                    do_w = c2.selectbox("Dolce", dati['Dolce'].split(','))
                    b_w = c2.selectbox("Bevanda", dati['Bevanda'].split(','))
                    n_w = st.text_input("Note/Allergie", key="wa_note")
                    
                    t_wa = f"*ORDINE* ({g})\n*Dipendente:* {st.session_state.user} ({iniz})\n----------\n🍜 {p_w}\n🥗 {c_w}\n🍰 {do_w}\n🥤 {b_w}\n📝 Note: {n_w}"
                    l_wa = f"https://wa.me/39333000000?text={urllib.parse.quote(t_wa)}"
                    st.markdown(f'<a href="{l_wa}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:10px;border-radius:5px;text-align:center;font-weight:bold;">📲 INVIA VIA WHATSAPP</div></a>', unsafe_allow_html=True)
            else:
                with st.form("ord_interno"):
                    c1, c2 = st.columns(2)
                    p = c1.selectbox("Principale", dati['Principale'].split(','))
                    c = c1.selectbox("Contorno", dati['Contorno'].split(','))
                    do = c2.selectbox("Dolce", dati['Dolce'].split(','))
                    b = c2.selectbox("Bevanda", dati['Bevanda'].split(','))
                    n = st.text_input("Note/Allergie")
                    if st.form_submit_button("Registra nel Portale"):
                        o = pd.read_csv(ORDINI_FILE)
                        o = o[~((o['Giorno'] == g) & (o['User'] == st.session_state.user))]
                        det = f"{p}|{c}|{do}|{b}|{n}"
                        new = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), g, st.session_state.user, iniz, det]], columns=o.columns)
                        pd.concat([o, new]).to_csv(ORDINI_FILE, index=False)
                        st.success("Registrato!")

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

    # --- TAB RISTORANTE (MANUALE + EXCEL) ---
    with tabs[2]:
        if st.session_state.ruolo in ['Admin', 'Ristorante']:
            st.header("Gestione Menu")
            with st.expander("📂 Carica Excel/CSV"):
                uploaded = st.file_uploader("Scegli file", type=['csv', 'xlsx'])
                if uploaded:
                    new_m = pd.read_excel(uploaded) if uploaded.name.endswith('xlsx') else pd.read_csv(uploaded)
                    if st.button("Conferma File"):
                        new_m.to_csv(MENU_FILE, index=False)
                        invia_email_menu("Nuovo menu caricato da file.")
            with st.expander("✍️ Inserimento Manuale"):
                m_df = pd.read_csv(MENU_FILE)
                with st.form("manual"):
                    g_ed = st.selectbox("Giorno", m_df['Giorno'].tolist())
                    c1, c2 = st.columns(2)
                    p_n = c1.text_area("Principali (separa con virgola)")
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