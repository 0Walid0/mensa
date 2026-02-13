import streamlit as st
import pandas as pd
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
import urllib.parse

# --- CONFIGURAZIONE FILE ---
MENU_FILE = "menu_settimanale.csv"
ORDINI_FILE = "ordini_storico.csv"
UTENTI_FILE = "database_utenti.csv"
SETTINGS_FILE = "settings.csv"

# --- CONFIGURAZIONE EMAIL (LIBRAESVA) ---
# Sostituisci con i tuoi dati reali
SMTP_SERVER = "securemail04.netx64.cloud" 
SMTP_PORT = 587
EMAIL_MITTENTE = "relaynetx64" 
PASS_EMAIL = "3(aw&nBQyiPn8ab4" 

# --- INIZIALIZZAZIONE ---
def init_all():
    if not os.path.exists(MENU_FILE):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
        pd.DataFrame({'Giorno': giorni, 'Principale': 'Pasta', 'Contorno': 'Insalata', 'Dolce': 'Frutta', 'Bevanda': 'Acqua'}).to_csv(MENU_FILE, index=False)
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

def invia_email_menu(testo_menu):
    u_db = pd.read_csv(UTENTI_FILE)
    destinatari = u_db[u_db['Email'].str.contains('@', na=False)]['Email'].tolist()
    if not destinatari: return
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() 
        server.login(EMAIL_MITTENTE, PASS_EMAIL)
        msg = MIMEText(f"Il ristorante ha aggiornato il menu:\n\n{testo_menu}")
        msg['Subject'] = "🍴 Nuovo Menu Mensa Disponibile"
        msg['From'] = f"Mensa Aziendale <{EMAIL_MITTENTE}>" 
        msg['To'] = ", ".join(destinatari)
        server.sendmail(EMAIL_MITTENTE, destinatari, msg.as_string())
        server.quit()
        st.success("Notifiche inviate!")
    except Exception as e: st.error(f"Errore Email: {e}")

def get_iniziali(nome):
    parti = str(nome).replace('.', ' ').split()
    return f"{parti[0][0].upper()}.{parti[1][0].upper()}." if len(parti) >= 2 else str(nome)[:2].upper()

# --- ACCESSO ---
u_db = pd.read_csv(UTENTI_FILE)
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍴 Portale Mensa")
    u_sel = st.selectbox("Utente", [""] + u_db['User'].tolist())
    p_sel = st.text_input("Password", type="password")
    if st.button("Accedi"):
        row = u_db[(u_db['User'] == u_sel) & (u_db['Password'].astype(str) == str(p_sel))]
        if not row.empty:
            st.session_state.auth, st.session_state.user, st.session_state.ruolo = True, u_sel, row.iloc[0]['Ruolo']
            st.session_state.primo = row.iloc[0]['PrimoAccesso']
            st.rerun()
        else: st.error("Credenziali errate")
else:
    if st.session_state.primo and st.session_state.ruolo == 'User':
        with st.form("setup"):
            st.warning("🔒 Configura il tuo profilo")
            m = st.text_input("Email")
            pw = st.text_input("Nuova Password", type="password")
            if st.form_submit_button("Salva"):
                u_db.loc[u_db['User'] == st.session_state.user, ['Email', 'Password', 'PrimoAccesso']] = [m, pw, False]
                u_db.to_csv(UTENTI_FILE, index=False)
                st.session_state.primo = False
                st.rerun()
        st.stop()

    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Logout"): 
        st.session_state.auth = False
        st.rerun()

    t_ord, t_admin, t_chef = st.tabs(["📝 Ordini", "🛡️ Admin", "👨‍🍳 Ristorante"])

    with t_ord:
        s = pd.read_csv(SETTINGS_FILE).iloc[0]
        m_df = pd.read_csv(MENU_FILE)
        
        # Controllo Giorno Selezionato
        g = st.selectbox("Seleziona il Giorno dell'Ordine", m_df['Giorno'].tolist())
        d = m_df[m_df['Giorno'] == g].iloc[0]
        
        def p(val): return str(val).split(',') if pd.notna(val) and str(val).strip() != "" else ["N/A"]

        if not s['sblocco_manuale']:
            st.error(f"🚫 Menu interno chiuso per {g}. Usa l'invio WhatsApp.")
            c1, c2 = st.columns(2)
            p_w = c1.selectbox("Principale", p(d['Principale']), key="pw")
            c_w = c1.selectbox("Contorno", p(d['Contorno']), key="cw")
            do_w = c2.selectbox("Dolce", p(d['Dolce']), key="dw")
            b_w = c2.selectbox("Bevanda", p(d['Bevanda']), key="bw")
            n_w = st.text_input("Note/Allergie", key="nw")
            
            # Formattazione messaggio con controllo giorno
            t_wa = f"*ORDINE MENSA* \n*Giorno:* {g}\n*Dipendente:* {st.session_state.user} ({get_iniziali(st.session_state.user)})\n----------\n🍜 *Primo:* {p_w}\n🥗 *Contorno:* {c_w}\n🍰 *Dolce:* {do_w}\n🥤 *Bevanda:* {b_w}\n📝 *Note:* {n_w}"
            l_wa = f"https://wa.me/3381161485?text={urllib.parse.quote(t_wa)}"
            
            st.markdown(f'<a href="{l_wa}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;font-size:18px;">📲 INVIA ORDINE {g.upper()} VIA WHATSAPP</div></a>', unsafe_allow_html=True)
        else:
            with st.form("ord"):
                st.success(f"✅ Menu aperto per {g}. Puoi registrare l'ordine nel sistema.")
                c1, c2 = st.columns(2)
                p_i = c1.selectbox("Principale", p(d['Principale']))
                c_i = c1.selectbox("Contorno", p(d['Contorno']))
                do_i = c2.selectbox("Dolce", p(d['Dolce']))
                b_i = c2.selectbox("Bevanda", p(d['Bevanda']))
                n_i = st.text_input("Note")
                if st.form_submit_button("Conferma Ordine nel Portale"):
                    o_df = pd.read_csv(ORDINI_FILE)
                    o_df = o_df[~((o_df['Giorno'] == g) & (o_df['User'] == st.session_state.user))]
                    new = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), g, st.session_state.user, get_iniziali(st.session_state.user), f"{p_i}|{c_i}|{do_i}|{b_i}|{n_i}"]], columns=o_df.columns)
                    pd.concat([o_df, new]).to_csv(ORDINI_FILE, index=False)
                    st.success(f"Ordine per {g} registrato!")

    with t_admin:
        if st.session_state.ruolo == 'Admin':
            sd = pd.read_csv(SETTINGS_FILE)
            sd.at[0, 'sblocco_manuale'] = st.toggle("Abilita Ordini Interni", sd.iloc[0]['sblocco_manuale'])
            if st.button("Salva Impostazioni"):
                sd.to_csv(SETTINGS_FILE, index=False)
                st.rerun()

    with t_chef:
        if st.session_state.ruolo in ['Admin', 'Ristorante']:
            st.header("Gestione Menu")
            with st.expander("📂 Carica Excel"):
                u_f = st.file_uploader("Scegli file", type=['csv', 'xlsx'])
                if u_f and st.button("Conferma"):
                    nm = pd.read_excel(u_f) if u_f.name.endswith('xlsx') else pd.read_csv(u_f)
                    nm.to_csv(MENU_FILE, index=False)
                    invia_email_menu("Nuovo menu caricato.")
            with st.expander("✍️ Inserimento Manuale"):
                with st.form("man"):
                    m_d = pd.read_csv(MENU_FILE)
                    g_e = st.selectbox("Giorno", m_d['Giorno'].tolist())
                    c1, c2 = st.columns(2)
                    p_n = c1.text_area("Principali")
                    c_n = c1.text_area("Contorni")
                    d_n = c2.text_area("Dolci")
                    b_n = c2.text_area("Bevande")
                    if st.form_submit_button("Salva e Invia Notifica"):
                        m_d.loc[m_d['Giorno'] == g_e, ['Principale','Contorno','Dolce','Bevanda']] = [p_n, c_n, d_n, b_n]
                        m_d.to_csv(MENU_FILE, index=False)
                        invia_email_menu(f"Aggiornamento {g_e}")