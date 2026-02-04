import streamlit as st
import pandas as pd
import random

# ================= CONFIGURATION =================
st.set_page_config(
    page_title="RIM-Orientation",
    page_icon="🇲🇷",
    layout="centered"
)

# ================= CONNEXION À POSTGRES =================
try:
    conn = st.connection("postgresql", type="sql")
except Exception:
    st.error("⚠️ Impossible de se connecter à la base de données (secrets.toml)")
    st.stop()

# ================= SESSION =================
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.scores = {"R":0,"I":0,"A":0,"S":0,"E":0,"C":0}
    st.session_state.seed = 0

# ================= TITRE =================
st.title("🇲🇷 RIM-Orientation")
st.write("Découvrez votre avenir selon votre personnalité (RIASEC).")

# ================= CHARGEMENT QUESTIONS =================
questions = conn.query("SELECT * FROM orientation_questions ORDER BY ordre_affichage")
if questions.empty:
    st.error("La table orientation_questions est vide.")
    st.stop()

# ================= QUESTIONNAIRE =================
if st.session_state.step <= len(questions):
    q = questions.iloc[st.session_state.step - 1]

    st.progress(st.session_state.step / len(questions))
    st.subheader(f"Question {st.session_state.step} / {len(questions)}")

    st.markdown(f"### {q['question_fr']}")
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
    st.success("Analyse terminée !")

    # ======= 1) Calcul du profil RIASEC stable =======
    order = {"R":0,"I":1,"A":2,"S":3,"E":4,"C":5}
    scores_items = list(st.session_state.scores.items())

    # Tri stable : score desc, puis ordre RIASEC
    sorted_scores = sorted(
        scores_items,
        key=lambda x: (-x[1], order[x[0]])
    )

    lettre1, lettre2, lettre3 = [item[0] for item in sorted_scores[:3]]

    st.subheader(f"Votre profil RIASEC dominant est : **{lettre1}{lettre2}{lettre3}**")
    st.write("Détail de vos scores :")
    st.json(st.session_state.scores)

    # ======= 2) Calcul de distance =======
    order_map = {"R":0, "I":1, "A":2, "S":3, "E":4, "C":5}

    def circular_distance(a, b):
        diff = abs(order_map[a] - order_map[b])
        return min(diff, 6 - diff)

    def distance_profile(code):
        code = code.upper()
        d = 0
        if len(code) >= 1:
            d += circular_distance(code[0], lettre1) * 3
        if len(code) >= 2:
            d += circular_distance(code[1], lettre2) * 2
        if len(code) >= 3:
            d += circular_distance(code[2], lettre3) * 1
        return d

    # ======= 3) Récupération des filières =======
    filieres = conn.query("SELECT filiere_nom, etablissement, code_riasec FROM filieres")
    filieres = filieres[filieres["code_riasec"].str.len().isin([2, 3])]
    filieres["distance"] = filieres["code_riasec"].apply(distance_profile)

    # supprimer les doublons
    filieres = filieres.drop_duplicates(subset=["filiere_nom", "etablissement"])

    # tri par distance
    filieres = filieres.sort_values(["distance"])

    # ======= 4) Sélection intelligente (0 -> 1 -> 2...) =======
    selected = pd.DataFrame()
    d = 0
    max_distance = filieres["distance"].max()

    while len(selected) < 5 and d <= max_distance:
        group = filieres[filieres["distance"] == d]

        if len(group) > 0:
            # Pour que le bouton change vraiment les réponses
            # on prend un pool plus grand par distance, puis on sample
            random.seed(st.session_state.seed + d)
            group = group.sample(frac=1).reset_index(drop=True)

            needed = 5 - len(selected)
            selected = pd.concat([selected, group.head(needed)], ignore_index=True)

        d += 1

    # tri final par distance (ordre garanti)
    selected = selected.sort_values("distance")

    st.table(selected[["filiere_nom", "etablissement", "code_riasec", "distance"]])

    # ======= 5) Bouton "Générer d'autres réponses" =======
    if st.button("🎲 Générer d'autres réponses"):
        st.session_state.seed += 1
        st.rerun()

    # ======= 6) Reset =======
    if st.button("🔄 Recommencer le test"):
        st.session_state.step = 1
        st.session_state.scores = {"R":0,"I":0,"A":0,"S":0,"E":0,"C":0}
        st.session_state.seed = 0
        st.rerun()
