import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
import pytz # Per orario italiano

# --- CONFIGURAZIONE ---
MENU_FILE = "menu_settimanale.csv"
ORDINI_FILE = "ordini_storico.csv"
UTENTI_FILE = "database_utenti.csv"
SETTINGS_FILE = "settings.csv"

# --- 1. INIZIALIZZAZIONE ---
def init_all():
    if not os.path.exists(MENU_FILE):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
        pd.DataFrame({
            'Giorno': giorni,
            'Principale': ['Pasta, Riso'] * 5, 'Contorno': ['Insalata, Patate'] * 5,
            'Dolce': ['Frutta, Torta'] * 5, 'Bevanda': ['Acqua, Bibita'] * 5
        }).to_csv(MENU_FILE, index=False)
    
    if not os.path.exists(ORDINI_FILE):
        pd.DataFrame(columns=['Data', 'Giorno', 'User', 'Iniziali', 'Dettaglio']).to_csv(ORDINI_FILE, index=False)

    if not os.path.exists(UTENTI_FILE):
        pd.DataFrame([
            {'User': 'Admin', 'Password': '123', 'Ruolo': 'Admin'},
            {'User': 'walid.ouakili', 'Password': '456', 'Ruolo': 'User'},
            {'User': 'Ristorante', 'Password': '789', 'Ruolo': 'Ristorante'}
        ]).to_csv(UTENTI_FILE, index=False)
        
    if not os.path.exists(SETTINGS_FILE):
        pd.DataFrame([{'chiusura': '10:30', 'sblocco_manuale': False}]).to_csv(SETTINGS_FILE, index=False)

init_all()

# --- UTILITY ---
def get_iniziali(nome):
    parti = nome.replace('.', ' ').split()
    return f"{parti[0][0].upper()}.{parti[1][0].upper()}." if len(parti) >= 2 else nome[:2].upper()

def is_ordine_aperto():
    settings = pd.read_csv(SETTINGS_FILE).iloc[0]
    if settings['sblocco_manuale']: return True
    tz = pytz.timezone('Europe/Rome')
    ora_attuale = datetime.now(tz).time()
    ora_limite = datetime.strptime(settings['chiusura'], "%H:%M").time()
    return ora_attuale < ora_limite

# --- LOGIN ---
u_db = pd.read_csv(UTENTI_FILE)
u_db['User'] = u_db['User'].astype(str).str.strip()
u_db['Password'] = u_db['Password'].astype(str).str.strip()

if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍴 Sistema Mensa Integrato")
    u_sel = st.selectbox("Utente", [""] + u_db['User'].tolist())
    p_sel = st.text_input("Password", type="password")
    if st.button("Accedi"):
        user_row = u_db[(u_db['User'] == u_sel) & (u_db['Password'] == p_sel)]
        if not user_row.empty:
            st.session_state.auth, st.session_state.user, st.session_state.ruolo = True, u_sel, user_row.iloc[0]['Ruolo']
            st.rerun()
        else: st.error("Credenziali errate")
else:
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Logout"): 
        st.session_state.auth = False
        st.rerun()

    # --- LOGICA TAB PER RUOLO ---
    if st.session_state.ruolo == 'User':
        tabs = st.tabs(["📝 Prenota Pasto"])
    elif st.session_state.ruolo == 'Admin':
        tabs = st.tabs(["📝 Prenota Pasto", "🛡️ Amministrazione", "👨‍🍳 Cucina"])
    else: # Ristorante
        tabs = st.tabs(["👨‍🍳 Cucina"])

    # --- TAB ORDINE (Solo User e Admin) ---
    if st.session_state.ruolo in ['User', 'Admin']:
        with tabs[0]:
            if not is_ordine_aperto() and st.session_state.ruolo != 'Admin':
                st.warning("⚠️ Ordini chiusi per oggi.")
            else:
                st.header("Compila il tuo ordine")
                menu_df = pd.read_csv(MENU_FILE)
                g_scelto = st.selectbox("Giorno", menu_df['Giorno'].tolist())
                dati = menu_df[menu_df['Giorno'] == g_scelto].iloc[0]
                with st.form("f_ordine"):
                    c1, c2 = st.columns(2)
                    p = c1.radio("Principale", dati['Principale'].split(', '))
                    c = c1.radio("Contorno", dati['Contorno'].split(', '))
                    d = c2.radio("Dolce", dati['Dolce'].split(', '))
                    b = c2.radio("Bevanda", dati['Bevanda'].split(', '))
                    if st.form_submit_button("Invia"):
                        df_o = pd.read_csv(ORDINI_FILE)
                        df_o = df_o[~((df_o['Giorno'] == g_scelto) & (df_o['User'] == st.session_state.user))]
                        new = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), g_scelto, st.session_state.user, get_iniziali(st.session_state.user), f"{p}|{c}|{d}|{b}"]], columns=df_o.columns)
                        pd.concat([df_o, new]).to_csv(ORDINI_FILE, index=False)
                        st.success("Ordine salvato!")

    # --- TAB ADMIN ---
    if st.session_state.ruolo == 'Admin':
        with tabs[1]:
            st.header("Impostazioni Sistema")
            settings = pd.read_csv(SETTINGS_FILE)
            nuova_ora = st.text_input("Orario chiusura automatica (HH:MM)", settings.iloc[0]['chiusura'])
            sblocco = st.toggle("Sblocco manuale forzato (Ignora orario)", settings.iloc[0]['sblocco_manuale'])
            if st.button("Salva Impostazioni"):
                pd.DataFrame([{'chiusura': nuova_ora, 'sblocco_manuale': sblocco}]).to_csv(SETTINGS_FILE, index=False)
                st.success("Impostazioni aggiornate!")
            
            st.divider()
            st.subheader("Stato Presenze Settimanali")
            df_o = pd.read_csv(ORDINI_FILE)
            utenti = u_db[u_db['Ruolo'] == 'User']['User'].tolist()
            grid = []
            for u in utenti:
                f = {'Dipendente': u}
                for g in ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']:
                    f[g] = "✅" if not df_o[(df_o['User'] == u) & (df_o['Giorno'] == g)].empty else "❌"
                grid.append(f)
            st.table(pd.DataFrame(grid))

    # --- TAB RISTORANTE ---
    idx_rist = 2 if st.session_state.ruolo == 'Admin' else 0
    if st.session_state.ruolo in ['Admin', 'Ristorante']:
        with tabs[idx_rist]:
            st.header("Gestione Cucina")
            # Modifica Menu
            with st.expander("Modifica Menu Settimanale"):
                m_df = pd.read_csv(MENU_FILE)
                edit_m = st.data_editor(m_df, use_container_width=True, hide_index=True)
                if st.button("Pubblica Nuovo Menu"):
                    edit_m.to_csv(MENU_FILE, index=False)
                    st.success("Menu aggiornato!")

            st.divider()
            # Visualizzazione Ordini
            g_chef = st.selectbox("Vedi ordini per:", ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì'])
            df_o = pd.read_csv(ORDINI_FILE)
            df_g = df_o[df_o['Giorno'] == g_chef]
            
            if df_g.empty: st.info("Nessun ordine.")
            else:
                st.subheader(f"Riepilogo {g_chef}")
                # Logica per contare e raggruppare iniziali
                for i, cat in enumerate(['Principale', 'Contorno', 'Dolce', 'Bevanda']):
                    st.write(f"**{cat}**")
                    choices = df_g['Dettaglio'].apply(lambda x: x.split('|')[i])
                    summary = []
                    for piatto in choices.unique():
                        inits = df_g[df_g['Dettaglio'].apply(lambda x: x.split('|')[i] == piatto)]['Iniziali'].tolist()
                        summary.append({'Piatto': piatto, 'Totale': len(inits), 'Chi': ", ".join(inits)})
                    st.table(pd.DataFrame(summary))