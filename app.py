import streamlit as st
import pandas as pd
import random
import os

# ================= CONFIGURATION =================
st.set_page_config(
    page_title="RIM-Orientation",
    page_icon="🇲🇷",
    layout="centered"
)

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

QUESTIONS_PATH = os.path.join(BASE_DIR, "orientation_questions.csv")
FILIERES_PATH = os.path.join(BASE_DIR, "filieres.csv")

# ================= LOAD DATA =================
try:
    questions = pd.read_csv(QUESTIONS_PATH)
    filieres = pd.read_csv(FILIERES_PATH)
except Exception as e:
    st.error("❌ Impossible de charger les fichiers CSV")
    st.stop()

# ================= SESSION =================
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.scores = {
        "R": 0, "I": 0, "A": 0,
        "S": 0, "E": 0, "C": 0
    }
    st.session_state.seed = random.randint(0, 999999)

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
        if st.button("❌ Pas du tout", use_container_width=True):
            st.session_state.step += 1
            st.rerun()

    with col2:
        if st.button("🟡 Un peu", use_container_width=True):
            st.session_state.scores[q["dimension"]] += 1
            st.session_state.step += 1
            st.rerun()

    with col3:
        if st.button("✅ Beaucoup", use_container_width=True):
            st.session_state.scores[q["dimension"]] += 2
            st.session_state.step += 1
            st.rerun()

# ================= RÉSULTATS =================
else:
    st.balloons()
    st.success("Analyse terminée !")

    # --- Tri RIASEC avec mélange contrôlé ---
    random.seed(st.session_state.seed)
    items = list(st.session_state.scores.items())
    random.shuffle(items)
    items.sort(key=lambda x: x[1], reverse=True)

    lettre1, lettre2, lettre3 = [x[0] for x in items[:3]]

    st.subheader(
        f"Votre profil RIASEC dominant est : **{lettre1}{lettre2}{lettre3}**"
    )

    st.write("Détail de vos scores :")
    st.json(st.session_state.scores)

    # ================= DISTANCE HOLLAND =================
    rank = {"R": 1, "I": 2, "A": 3, "S": 4, "E": 5, "C": 6}

    r1 = rank[lettre1]
    r2 = rank[lettre2]

    def holland_distance(code):
        code = str(code).strip().upper()

        if len(code) == 1:
            code = code * 2

        c1 = rank.get(code[0], r1)
        c2 = rank.get(code[1], r2)

        d1 = min(abs(c1 - r1), 6 - abs(c1 - r1))
        d2 = min(abs(c2 - r2), 6 - abs(c2 - r2))

        return d1 * 2 + d2

    filieres["distance"] = filieres["code_riasec"].apply(holland_distance)

    filieres = (
        filieres
        .sort_values(["distance", "filiere_nom", "etablissement"])
        .drop_duplicates(subset=["filiere_nom", "etablissement"])
    )

    st.write(
        "Voici les filières mauritaniennes les plus proches de votre profil :"
    )

    st.table(
        filieres.head(5)[
            ["filiere_nom", "etablissement", "code_riasec", "distance"]
        ]
    )
