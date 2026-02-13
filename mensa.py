import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- FILE DATABASE ---
MENU_FILE = "menu_settimanale.csv"
ORDINI_FILE = "ordini_storico.csv"
UTENTI_FILE = "database_utenti.csv"

# --- INIZIALIZZAZIONE ---
def init_all():
    if not os.path.exists(MENU_FILE):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
        # Menu espanso con più opzioni per sezione (separate da virgola)
        pd.DataFrame({
            'Giorno': giorni,
            'Principale': ['Pasta al forno, Risotto, Zuppa'] * 5,
            'Contorno': ['Insalata, Patate, Verdure cotte'] * 5,
            'Dolce': ['Tiramisù, Frutta, Gelato'] * 5,
            'Bevanda': ['Acqua Nat, Acqua Gas, Vino, Bibita'] * 5
        }).to_csv(MENU_FILE, index=False)
    
    if not os.path.exists(ORDINI_FILE):
        pd.DataFrame(columns=['Data', 'Giorno', 'User', 'Dettaglio']).to_csv(ORDINI_FILE, index=False)

init_all()

# --- CARICAMENTO DATI ---
u_db = pd.read_csv(UTENTI_FILE)
u_db['User'] = u_db['User'].astype(str).str.strip()
u_db['Password'] = u_db['Password'].astype(str).str.strip()

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍴 Gestione Mensa Avanzata")
    user_input = st.selectbox("Utente", [""] + u_db['User'].tolist())
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

    tab_ordine, tab_admin = st.tabs(["📝 Prenota Pasto", "🛡️ Pannello Controllo"])

    # --- TAB ORDINE: SELEZIONE GIORNALIERA DETTAGLIATA ---
    with tab_ordine:
        st.header("Scegli il tuo Menu")
        menu_df = pd.read_csv(MENU_FILE)
        
        giorno_scelto = st.selectbox("Per quale giorno vuoi ordinare?", menu_df['Giorno'].tolist())
        dati_giorno = menu_df[menu_df['Giorno'] == giorno_scelto].iloc[0]

        st.info(f"Stai ordinando per: **{giorno_scelto}**")
        
        with st.form("form_multi_scelta"):
            col1, col2 = st.columns(2)
            with col1:
                p_scelto = st.radio("Piatto Principale", dati_giorno['Principale'].split(', '))
                c_scelto = st.radio("Contorno", dati_giorno['Contorno'].split(', '))
            with col2:
                d_scelto = st.radio("Dolce", dati_giorno['Dolce'].split(', '))
                b_scelto = st.radio("Bevanda", dati_giorno['Bevanda'].split(', '))
            
            note = st.text_input("Note particolari")
            
            if st.form_submit_button("Conferma Ordine"):
                ordini_df = pd.read_csv(ORDINI_FILE)
                # Rimuovi ordine precedente per quel giorno/utente
                ordini_df = ordini_df[~((ordini_df['Giorno'] == giorno_scelto) & (ordini_df['User'] == st.session_state.user))]
                
                dettaglio = f"{p_scelto} | {c_scelto} | {d_scelto} | {b_scelto}"
                nuovo_ordine = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), giorno_scelto, st.session_state.user, dettaglio]], 
                                            columns=['Data', 'Giorno', 'User', 'Dettaglio'])
                
                nuovo_ordine.to_csv(ORDINI_FILE, mode='a', header=False, index=False)
                st.success(f"Ordine per {giorno_scelto} salvato correttamente!")

    # --- TAB ADMIN: CALENDARIO SETTIMANALE DIPENDENTI ---
    with tab_admin:
        if st.session_state.ruolo != 'Admin':
            st.error("Accesso riservato.")
        else:
            st.header("Stato Ordini Settimanali")
            ordini_df = pd.read_csv(ORDINI_FILE)
            utenti_list = u_db[u_db['Ruolo'] == 'User']['User'].tolist()
            giorni_sett = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì']
            
            # Creazione griglia calendario
            calendario_data = []
            for utente in utenti_list:
                fila = {'Dipendente': utente}
                for g in giorni_sett:
                    ordine = ordini_df[(ordini_df['User'] == utente) & (ordini_df['Giorno'] == g)]
                    fila[g] = "✅ " + ordine.iloc[0]['Dettaglio'] if not ordine.empty else "❌"
                calendario_data.append(fila)
            
            grid_df = pd.DataFrame(calendario_data)
            st.dataframe(grid_df, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("Modifica Menu Settimanale")
            nuovo_menu = st.data_editor(menu_df, use_container_width=True, hide_index=True)
            if st.button("Aggiorna Menu per Tutti"):
                nuovo_menu.to_csv(MENU_FILE, index=False)
                st.success("Menu aggiornato con successo!")