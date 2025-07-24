import streamlit as st
from datetime import datetime, date
import copy
import json
import requests
import os

st.set_page_config(page_title="Tri des Mots", page_icon="📝", layout="wide")

# Configuration - you'll need to set these as Streamlit secrets
GIST_ID = st.secrets.get("GIST_ID", "")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GIST_FILENAME = "mots.json"

# Categories available for sorting
CATEGORIES = {
    "Classique": {},
    "Torride": {},
    "Géographie": {},
    "Rejeté": {}
}

def fetch_gist_data():
    """Fetch data from GitHub Gist"""
    if not GIST_ID or not GITHUB_TOKEN:
        st.error("Configuration manquante. Veuillez configurer GIST_ID et GITHUB_TOKEN dans les secrets.")
        return None
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
        response.raise_for_status()
        gist_data = response.json()
        
        if GIST_FILENAME in gist_data["files"]:
            content = gist_data["files"][GIST_FILENAME]["content"]
            
            # Clean content - remove BOM and normalize whitespace
            content = content.strip()
            if content.startswith('\ufeff'):  # Remove BOM
                content = content[1:]
            
            # Replace non-breaking spaces with regular spaces
            content = content.replace('\xa0', ' ')
            
            return json.loads(content)
        else:
            st.error(f"Fichier {GIST_FILENAME} non trouvé dans le gist.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la récupération du gist: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Erreur lors du parsing JSON: {e}")
        st.error(f"Contenu problématique autour du caractère {e.pos}: {repr(content[max(0, e.pos-20):e.pos+20])}")
        return None

def update_gist_data(data):
    """Update GitHub Gist with new data"""
    if not GIST_ID or not GITHUB_TOKEN:
        return False
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "files": {
            GIST_FILENAME: {
                "content": json.dumps(data, indent=2, ensure_ascii=False)
            }
        }
    }
    
    try:
        response = requests.patch(f"https://api.github.com/gists/{GIST_ID}", 
                                headers=headers, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la mise à jour du gist: {e}")
        return False

def main():
    st.title("🔤 Tri des Mots")
    st.markdown("---")
    
    # Navigation
    tab1, tab2 = st.tabs(["Trier les mots", "Voir les mots déjà triés"])
    
    # Load data
    data = fetch_gist_data()
    if data is None:
        return
    
    with tab1:
        trier_les_mots(data)
    
    with tab2:
        voir_mots_tries(data)

def trier_les_mots(data):
    """Interface for sorting words"""
    st.header("Trier les mots")
    
    # Get unsorted words
    mots_non_tries = data.get("MotsNonTriés", [])
    
    if not mots_non_tries:
        st.info("Aucun mot à trier pour le moment.")
        return
    
    st.write(f"**{len(mots_non_tries)} mots** restants à trier")
    st.markdown("---")
    
    # Get the first word to sort
    mot_a_trier = mots_non_tries[0]
    
    # Display word in large font
    st.markdown(f"<h1 style='text-align: center; font-size: 4em; margin: 0.5em 0;'>{mot_a_trier}</h1>", 
                unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Create buttons for each category
    cols = st.columns(len(CATEGORIES))
    
    for i, categorie in enumerate(CATEGORIES.keys()):
        with cols[i]:
            if st.button(categorie, key=f"btn_{categorie}", use_container_width=True):
                trier_mot(data, mot_a_trier, categorie)

def trier_mot(data, mot, categorie):
    """Sort a word into a category"""
    if mot in data["MotsNonTriés"]:
        data["MotsNonTriés"].remove(mot)
        
        # Add to selected category
        if categorie not in data:
            data[categorie] = []
        if isinstance(data[categorie], dict):
            data[categorie] = []
        data[categorie].append(mot)
        
        # Update gist
        if update_gist_data(data):
            st.success(f"'{mot}' a été trié dans '{categorie}'!")
            st.rerun()
        else:
            st.error("Erreur lors de la sauvegarde.")

def voir_mots_tries(data):
    """Interface for viewing sorted words"""
    st.header("Mots déjà triés")
    
    # Show statistics
    mots_non_tries = len(data.get("MotsNonTriés", []))
    total_tries = sum(len(data.get(cat, [])) for cat in CATEGORIES.keys() if isinstance(data.get(cat, []), list))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Mots non triés", mots_non_tries)
    with col2:
        st.metric("Mots triés", total_tries)
    with col3:
        st.metric("Total", mots_non_tries + total_tries)
    
    st.markdown("---")
    
    # Show words by category
    for categorie in CATEGORIES.keys():
        mots = data.get(categorie, [])
        if isinstance(mots, list) and mots:
            with st.expander(f"**{categorie}** ({len(mots)} mots)"):
                # Display words in columns for better layout
                if mots:
                    cols = st.columns(4)
                    for i, mot in enumerate(sorted(mots)):
                        with cols[i % 4]:
                            st.write(f"• {mot}")

if __name__ == "__main__":
    main()
