import streamlit as st
import pandas as pd
import random

# ================= CONFIGURATION =================
st.set_page_config(
    page_title="RIM-Orientation",
    page_icon="🇲🇷",
    layout="centered"
)

# ================= SESSION =================
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.scores = {"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0}

# ================= CHARGEMENT QUESTIONS =================
questions = pd.read_csv("data/orientation_questions.csv")

if questions.empty:
    st.error("La table orientation_questions est vide.")
    st.stop()

# ================= TITRE =================
st.title("🇲🇷 RIM-Orientation")
st.write("Découvrez votre avenir selon votre personnalité (RIASEC).")

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
            st.experimental_rerun()

    with col2:
        if st.button("🟡 Un peu", key=f"maybe_{st.session_state.step}", use_container_width=True):
            st.session_state.scores[q["dimension"]] += 1
            st.session_state.step += 1
            st.experimental_rerun()

    with col3:
        if st.button("✅ Beaucoup", key=f"yes_{st.session_state.step}", use_container_width=True):
            st.session_state.scores[q["dimension"]] += 2
            st.session_state.step += 1
            st.experimental_rerun()

# ================= RÉSULTATS =================
else:
    st.balloons()
    st.success("Analyse terminée !")

    scores_items = list(st.session_state.scores.items())
    random.shuffle(scores_items)
    sorted_scores = sorted(scores_items, key=lambda x: x[1], reverse=True)

    top_letters = [item[0] for item in sorted_scores[:3]]
    lettre1, lettre2, lettre3 = top_letters

    st.subheader(f"Votre profil RIASEC dominant est : **{lettre1}{lettre2}{lettre3}**")
    st.write("Détail de vos scores :")
    st.json(st.session_state.scores)

    # ================= FILIERES =================
    rank_map = {"R": 1, "I": 2, "A": 3, "S": 4, "E": 5, "C": 6}

    r1 = rank_map[lettre1]
    r2 = rank_map[lettre2]

    filieres = pd.read_csv("data/filieres.csv")

    def distance(code, r1, r2):
        # code example: "RI", "AS", "C" ...
        if len(code) == 1:
            # add a dummy second letter (same as first)
            code = code + code

        c1 = rank_map[code[0]]
        c2 = rank_map[code[1]]

        # distance circulaire (1..6)
        d1 = min(abs(c1 - r1), 6 - abs(c1 - r1))
        d2 = min(abs(c2 - r2), 6 - abs(c2 - r2))
        return d1 * 2 + d2

    filieres["distance"] = filieres["code_riasec"].apply(lambda x: distance(str(x), r1, r2))

    filieres = filieres.sort_values(["distance", "filiere_nom", "etablissement"])
    filieres = filieres.drop_duplicates(subset=["filiere_nom", "etablissement"])

    st.write("Voici les filières mauritaniennes les plus proches de votre profil :")
    st.table(filieres.head(5)[["filiere_nom", "etablissement", "code_riasec", "distance"]])

    # ================= BOUTON "GÉNÉRER D'AUTRES RÉPONSES" =================
    if st.button("🎲 Générer d'autres réponses"):
        st.experimental_rerun()

    # ================= RESET =================
    if st.button("🔄 Recommencer le test"):
        st.session_state.step = 1
        st.session_state.scores = {"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0}
        st.experimental_rerun()
