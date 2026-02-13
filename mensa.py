import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- FILE DATABASE ---
MENU_FILE = "menu_settimanale.csv"
ORDINI_FILE = "ordini_storico.csv"
UTENTI_FILE = "database_utenti.csv"

# --- 1. INIZIALIZZAZIONE (Deve avvenire PRIMA di ogni lettura) ---
def init_all():
    # Inizializza Menu Settimanale con le nuove sezioni
    if not os.path.exists(MENU_FILE):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
        pd.DataFrame({
            'Giorno': giorni,
            'Principale': ['Pasta al forno, Risotto, Zuppa'] * 5,
            'Contorno': ['Insalata, Patate, Verdure cotte'] * 5,
            'Dolce': ['Tiramisù, Frutta, Gelato'] * 5,
            'Bevanda': ['Acqua Nat, Acqua Gas, Bibita'] * 5
        }).to_csv(MENU_FILE, index=False)
    
    # Inizializza Storico Ordini
    if not os.path.exists(ORDINI_FILE):
        pd.DataFrame(columns=['Data', 'Giorno', 'User', 'Dettaglio']).to_csv(ORDINI_FILE, index=False)

    # Inizializza Database Utenti (Password forzata come stringa)
    if not os.path.exists(UTENTI_FILE):
        pd.DataFrame([
            {'User': 'Admin', 'Password': '123', 'Ruolo': 'Admin'},
            {'User': 'walid.ouakili', 'Password': '456', 'Ruolo': 'User'}
        ]).to_csv(UTENTI_FILE, index=False)

# Eseguiamo l'inizializzazione subito
init_all()

# --- 2. CARICAMENTO DATI (Ora i file esistono sicuramente) ---
u_db = pd.read_csv(UTENTI_FILE)
u_db['User'] = u_db['User'].astype(str).str.strip()
u_db['Password'] = u_db['Password'].astype(str).str.strip()

# --- LOGICA DI ACCESSO ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍴 Portale Mensa Aziendale")
    user_input = st.selectbox("Seleziona Utente", [""] + u_db['User'].tolist())
    pass_input = st.text_input("Password", type="password")
    
    if st.button("Accedi"):
        user_row = u_db[(u_db['User'] == str(user_input)) & (u_db['Password'] == str(pass_input))]
        if not user_row.empty:
            st.session_state.auth = True
            st.session_state.user = user_input
            st.session_state.ruolo = user_row.iloc[0]['Ruolo']
            st.rerun()
        else:
            st.error("Credenziali non corrette")
else:
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    tab_ordine, tab_admin = st.tabs(["📝 Prenota Pasto", "🛡️ Pannello Amministratore"])

    # --- TAB ORDINE: SELEZIONE GIORNALIERA DETTAGLIATA ---
    with tab_ordine:
        st.header("Seleziona il tuo ordine")
        menu_df = pd.read_csv(MENU_FILE)
        
        # Scelta del giorno
        giorno_scelto = st.selectbox("Per quale giorno vuoi ordinare?", menu_df['Giorno'].tolist())
        dati_giorno = menu_df[menu_df['Giorno'] == giorno_scelto].iloc[0]

        st.subheader(f"Opzioni per {giorno_scelto}")
        
        with st.form("form_ordine_dettagliato"):
            # Griglia di selezione per ogni sezione
            col1, col2 = st.columns(2)
            with col1:
                p_scelto = st.radio("Piatto Principale", dati_giorno['Principale'].split(', '))
                c_scelto = st.radio("Contorno", dati_giorno['Contorno'].split(', '))
            with col2:
                d_scelto = st.radio("Dolci", dati_giorno['Dolce'].split(', '))
                b_scelto = st.radio("Bevande", dati_giorno['Bevanda'].split(', '))
            
            note = st.text_input("Note/Allergie")
            
            if st.form_submit_button("Conferma Ordine"):
                ordini_df = pd.read_csv(ORDINI_FILE)
                # Rimuove ordine precedente per evitare duplicati
                ordini_df = ordini_df[~((ordini_df['Giorno'] == giorno_scelto) & (ordini_df['User'] == st.session_state.user))]
                
                dettaglio = f"{p_scelto} | {c_scelto} | {d_scelto} | {b_scelto}"
                nuovo_ordine = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), giorno_scelto, st.session_state.user, dettaglio]], 
                                            columns=['Data', 'Giorno', 'User', 'Dettaglio'])
                
                ordini_df = pd.concat([ordini_df, nuovo_ordine])
                ordini_df.to_csv(ORDINI_FILE, index=False)
                st.success(f"Ordine per {giorno_scelto} salvato!")

    # --- TAB ADMIN: CALENDARIO SETTIMANALE ---
    with tab_admin:
        if st.session_state.ruolo != 'Admin':
            st.error("Accesso riservato.")
        else:
            st.header("Calendario Riepilogo Ordini")
            ordini_df = pd.read_csv(ORDINI_FILE)
            utenti_list = u_db[u_db['Ruolo'] == 'User']['User'].tolist()
            giorni_sett = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
            
            # Costruzione della griglia calendario per l'Admin
            grid_data = []
            for utente in utenti_list:
                fila = {'Dipendente': utente}
                for g in giorni_sett:
                    ordine_check = ordini_df[(ordini_df['User'] == utente) & (ordini_df['Giorno'] == g)]
                    if not ordine_check.empty:
                        # Mostra il dettaglio sintetico dell'ordine
                        fila[g] = "✅ " + ordine_check.iloc[0]['Dettaglio'].split('|')[0] 
                    else:
                        fila[g] = "❌"
                grid_data.append(fila)
            
            st.table(pd.DataFrame(grid_data))