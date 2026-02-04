import streamlit as st
import pandas as pd
import random
from sqlalchemy import text

# ================= CONFIGURATION =================
st.set_page_config(
    page_title="RIM-Orientation",
    page_icon="🇲🇷",
    layout="centered"
)

# ================= CONNEXION À POSTGRES =================
# Assurez-vous que votre fichier .streamlit/secrets.toml est correct
try:
    conn = st.connection("postgresql", type="sql")
except Exception:
    st.error("⚠️ Impossible de se connecter à la base de données (vérifiez secrets.toml)")
    st.stop()

# ================= SESSION =================
if "step" not in st.session_state:
    st.session_state.step = 0           # 0 = accueil
    st.session_state.pseudo = ""
    st.session_state.scores = {"R":0,"I":0,"A":0,"S":0,"E":0,"C":0}
    st.session_state.seed = random.randint(0, 1000)
    st.session_state.saved = False

# ================= TITRE =================
st.title("🇲🇷 RIM-Orientation")
st.write("Découvrez votre avenir selon votre personnalité (RIASEC).")

# ================= PAGE D’ACCUEIL =================
if st.session_state.step == 0:
    st.subheader("🎓 Bienvenue")
    pseudo = st.text_input("Entrez votre nom ou pseudo :", max_chars=50)

    if st.button("▶️ Commencer le test"):
        if pseudo.strip() == "":
            st.warning("Veuillez entrer un nom.")
        else:
            st.session_state.pseudo = pseudo.strip()
            st.session_state.step = 1
            st.rerun()

# ================= QUESTIONNAIRE =================
elif st.session_state.step >= 1:
    # Récupération des questions
    questions = conn.query("SELECT * FROM orientation_questions ORDER BY ordre_affichage")
    
    if questions.empty:
        st.error("La table orientation_questions est vide ou n'existe pas.")
        st.stop()

    # Si on est encore dans les questions
    if st.session_state.step <= len(questions):
        q = questions.iloc[st.session_state.step - 1]

        st.progress(st.session_state.step / len(questions))
        st.subheader(f"Question {st.session_state.step} / {len(questions)}")
        st.markdown(f"### {q['question_fr']}")
        if 'question_ar' in q and pd.notna(q['question_ar']):
            st.info(f"*{q['question_ar']}*")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("❌ Pas du tout", key=f"no_{st.session_state.step}", use_container_width=True):
                st.session_state.step += 1
                st.rerun()
        with col2:
            if st.button("🟡 Un peu", key=f"maybe_{st.session_state.step}", use_container_width=True):
                st.session_state.scores[q["dimension"]] += 1
                st.session_state.step += 1
                st.rerun()
        with col3:
            if st.button("✅ Beaucoup", key=f"yes_{st.session_state.step}", use_container_width=True):
                st.session_state.scores[q["dimension"]] += 2
                st.session_state.step += 1
                st.rerun()

    # ================= RÉSULTATS =================
    else:
        st.balloons()
        st.success("Analyse terminée!")

        # 1. Tri correct des scores
        order_dict = {"R":0,"I":1,"A":2,"S":3,"E":4,"C":5}
        scores_items = list(st.session_state.scores.items())

        # Tri par score décroissant, puis par ordre RIASEC en cas d'égalité
        sorted_scores = sorted(
            scores_items,
            key=lambda x: (-x[1], order_dict[x[0]])
        )

        # Extraction des lettres uniquement
        l1, l2, l3 = [item[0] for item in sorted_scores[:3]]
        code_final = f"{l1}{l2}{l3}"

        st.subheader(f"Votre profil RIASEC dominant est : **{code_final}**")

        # --- CORRECTION MAJEURE ICI (Sauvegarde) ---
        # 2. Sauvegarde en base de données
        if not st.session_state.saved:
            try:
                # On utilise un bloc 'with' pour gérer la transaction proprement
                with conn.session as session:
                    query_sql = text("""
                        INSERT INTO sessions_utilisateurs (pseudo, code_riasec_obtenu) 
                        VALUES (:p, :c)
                    """)
                    session.execute(query_sql, {"p": st.session_state.pseudo, "c": code_final})
                    session.commit()  # IMPORTANT : Valide l'écriture
                
                st.session_state.saved = True
                st.success(f"✅ Résultat enregistré pour {st.session_state.pseudo} dans la base de données !")
                
            except Exception as e:
                st.error(f"❌ Erreur d'enregistrement SQL : {e}")
        # -------------------------------------------

        # 3. Calcul de distance (Algorithme de compatibilité)
        def get_dist(a, b):
            d = abs(order_dict[a] - order_dict[b])
            return min(d, 6 - d)

        def compute_fit(db_code):
            if not db_code or len(db_code) < 1:
                return 99 # Pénalité si code vide

            dist = get_dist(db_code[0], l1) * 3
            if len(db_code) >= 2:
                dist += get_dist(db_code[1], l2) * 2
            if len(db_code) >= 3:
                dist += get_dist(db_code[2], l3)
            return dist

        # 4. Affichage des filières
        try:
            filieres = conn.query("SELECT filiere_nom, etablissement, code_riasec FROM filieres")
            
            if not filieres.empty:
                filieres = filieres[filieres["code_riasec"].notna()].copy()
                filieres["distance"] = filieres["code_riasec"].apply(compute_fit)

                random.seed(st.session_state.seed)
                # On mélange un peu (sample) puis on trie par meilleure distance
                filieres = filieres.sample(frac=1).sort_values("distance")

                st.write("### Voici les licences les plus adaptées à votre personnalité :")
                st.table(filieres.head(5)[["filiere_nom", "etablissement", "code_riasec"]])
            else:
                st.warning("Aucune filière trouvée dans la base de données.")
                
        except Exception as e:
            st.warning(f"Impossible de charger les filières (table 'filieres' manquante ?) : {e}")

        # 5. Boutons finaux
        col_res, col_reset = st.columns(2)
        with col_res:
            if st.button("🎲 Autres suggestions"):
                st.session_state.seed = random.randint(0, 1000)
                st.rerun()
        with col_reset:
            if st.button("🔄 Recommencer le test"):
                st.session_state.step = 0
                st.session_state.scores = {"R":0,"I":0,"A":0,"S":0,"E":0,"C":0}
                st.session_state.saved = False
                st.rerun()
