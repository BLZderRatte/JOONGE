"""
Schulnoten-Manager – Ultimate Version
Features: Schüler/Fächer/Noten-Verwaltung • Deutsche Tendenz-Noten mit Dropdown & Dezimal-Umrechnung • Autom. Durchschnitte • JSON-Persistenz • Schöne farbige UI • Suche/Filter • CSV-Export/Import • Klassenstatistiken
"""

import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import plotly.express as px
from io import StringIO

# ────────────────────────────────────────────────
#   Konfiguration & Hilfsdaten
# ────────────────────────────────────────────────

DATA_FILE = "noten_db.json"

NOTE_TEXT_TO_DECIMAL = {
    "1+": 0.7, "1": 1.0, "1-": 1.3,
    "2+": 1.7, "2": 2.0, "2-": 2.3,
    "3+": 2.7, "3": 3.0, "3-": 3.3,
    "4+": 3.7, "4": 4.0, "4-": 4.3,
    "5+": 4.7, "5": 5.0, "5-": 5.3,
    "6":  6.0
}

ALL_GRADE_OPTIONS = list(NOTE_TEXT_TO_DECIMAL.keys())

# Farben für Noten
def get_note_color(decimal_grade):
    if decimal_grade < 2.0:
        return "background-color: #d4edda; color: #155724;"   # grün
    elif decimal_grade < 4.0:
        return "background-color: #fff3cd; color: #856404;"   # gelb/orange
    elif decimal_grade < 6.0:
        return "background-color: #f8d7da; color: #721c24;"   # rot
    else:
        return "background-color: #6c757d; color: white;"     # dunkelrot (6)

# ────────────────────────────────────────────────
#   Daten laden / speichern
# ────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            st.warning("Fehler beim Lesen der Datenbank → neue leere DB erstellt")
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ────────────────────────────────────────────────
#   Berechnungen
# ────────────────────────────────────────────────

def calculate_subject_average(grades):
    if not grades:
        return None
    return round(sum(grades) / len(grades), 2)

def calculate_student_average(subjects_data):
    subject_avgs = []
    for subj in subjects_data.values():
        avg = calculate_subject_average(subj.get("grades", []))
        if avg is not None:
            subject_avgs.append(avg)
    if not subject_avgs:
        return None
    return round(sum(subject_avgs) / len(subject_avgs), 2)

def grade_to_emoji(avg):
    if avg is None:
        return "—"
    if avg <= 1.3:
        return "😊👍"
    if avg <= 2.3:
        return "🙂"
    if avg <= 3.3:
        return "😐"
    if avg <= 4.3:
        return "😕"
    return "😟"

# ────────────────────────────────────────────────
#   Initialisierung
# ────────────────────────────────────────────────

if "data" not in st.session_state:
    st.session_state.data = load_data()

if "selected_student" not in st.session_state:
    st.session_state.selected_student = None

if "search_text" not in st.session_state:
    st.session_state.search_text = ""

# ────────────────────────────────────────────────
#   UI – Sidebar Navigation
# ────────────────────────────────────────────────

st.sidebar.title("Schulnoten-Manager")
page = st.sidebar.radio("Navigation", [
    "📋 Schülerübersicht",
    "✏️ Schüler & Noten bearbeiten",
    "📊 Statistiken"
])

# ────────────────────────────────────────────────
#   Seite: Schülerübersicht
# ────────────────────────────────────────────────

if page == "📋 Schülerübersicht":

    st.header("Schülerübersicht")

    # Suche
    search = st.text_input("Schüler suchen …", value=st.session_state.search_text, key="search_input")
    st.session_state.search_text = search.lower()

    # Tabelle vorbereiten
    rows = []
    for student_id, student in st.session_state.data.items():
        name = student.get("name", "—")
        class_ = student.get("class", "—")
        avg = calculate_student_average(student.get("subjects", {}))
        emoji = grade_to_emoji(avg)

        if st.session_state.search_text and st.session_state.search_text not in name.lower():
            continue

        rows.append({
            "ID": student_id,
            "Name": name,
            "Klasse": class_,
            "Gesamtdurchschnitt": f"{avg:.2f} {emoji}" if avg else "—",
            "⌀ numerisch": avg if avg else float("nan")
        })

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("⌀ numerisch", ascending=True).reset_index(drop=True)
        df_display = df.drop(columns=["⌀ numerisch"])

        # Farbige Formatierung
        def highlight_row(row):
            styles = ["" for _ in row]
            try:
                val = float(row["Gesamtdurchschnitt"].split()[0])
                styles[row.index.get_loc("Gesamtdurchschnitt")] = get_note_color(val)
            except:
                pass
            return styles

        st.dataframe(
            df_display.style.apply(highlight_row, axis=1)
            .format({"Gesamtdurchschnitt": lambda x: x}, na_rep="—"),
            use_container_width=True
        )

        if st.button("Alle Schüler auswählen zurücksetzen"):
            st.session_state.selected_student = None
            st.rerun()

    else:
        st.info("Keine Schüler vorhanden oder Suche ergab keine Treffer.")

# ────────────────────────────────────────────────
#   Seite: Schüler & Noten bearbeiten
# ────────────────────────────────────────────────

elif page == "✏️ Schüler & Noten bearbeiten":

    st.header("Schüler & Noten verwalten")

    col1, col2 = st.columns([3,2])

    with col1:
        student_names = {k: v["name"] for k,v in st.session_state.data.items()}
        options = ["Neuen Schüler anlegen"] + [f"{name} ({k})" for k,name in student_names.items()]

        selected = st.selectbox(
            "Schüler auswählen oder neuen anlegen",
            options,
            index=0 if not st.session_state.selected_student else options.index(next((f"{v['name']} ({k})" for k,v in st.session_state.data.items() if k == st.session_state.selected_student), 0))
        )

        if selected == "Neuen Schüler anlegen":
            with st.form("new_student_form"):
                new_name = st.text_input("Name des Schülers", key="new_name")
                new_class = st.text_input("Klasse / Jahrgang (optional)", key="new_class")
                submitted = st.form_submit_button("Schüler anlegen")

                if submitted:
                    if not new_name.strip():
                        st.error("Name darf nicht leer sein!")
                    else:
                        new_id = f"schueler_{len(st.session_state.data)+1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        st.session_state.data[new_id] = {
                            "name": new_name.strip(),
                            "class": new_class.strip(),
                            "subjects": {}
                        }
                        st.session_state.selected_student = new_id
                        save_data(st.session_state.data)
                        st.success(f"Schüler {new_name} angelegt!")
                        st.rerun()

        else:
            student_id = selected.split("(")[-1].strip(")")
            st.session_state.selected_student = student_id

            student = st.session_state.data[student_id]
            st.subheader(f"{student['name']} • {student.get('class','—')}")

            # Schüler bearbeiten / löschen
            col_a, col_b = st.columns(2)
            with col_a:
                new_name = st.text_input("Name ändern", value=student["name"], key=f"name_{student_id}")
                new_class = st.text_input("Klasse ändern", value=student.get("class",""), key=f"class_{student_id}")
                if st.button("Änderungen speichern"):
                    if not new_name.strip():
                        st.error("Name darf nicht leer sein!")
                    else:
                        student["name"] = new_name.strip()
                        student["class"] = new_class.strip()
                        save_data(st.session_state.data)
                        st.success("Daten aktualisiert")
                        st.rerun()

            with col_b:
                if st.button("Schüler löschen", type="primary"):
                    st.session_state["confirm_delete_student"] = student_id

            if st.session_state.get("confirm_delete_student") == student_id:
                st.warning(f"**Wirklich {student['name']} löschen?**")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Ja, löschen"):
                        del st.session_state.data[student_id]
                        st.session_state.selected_student = None
                        save_data(st.session_state.data)
                        st.success("Schüler gelöscht")
                        st.rerun()
                with col_no:
                    if st.button("Abbrechen"):
                        st.session_state.pop("confirm_delete_student", None)
                        st.rerun()

            # ── Fächer ───────────────────────────────────────
            st.markdown("### Fächer")
            subjects = student.setdefault("subjects", {})

            new_subject = st.text_input("Neues Fach hinzufügen", key=f"new_subj_{student_id}")
            if st.button("Fach hinzufügen") and new_subject.strip():
                subj_key = new_subject.strip().lower().replace(" ", "_")
                if subj_key not in subjects:
                    subjects[subj_key] = {"name": new_subject.strip(), "grades": []}
                    save_data(st.session_state.data)
                    st.success(f"Fach '{new_subject}' hinzugefügt")
                else:
                    st.warning("Fach existiert bereits")
                st.rerun()

            # Fächer anzeigen
            for subj_key, subj_data in list(subjects.items()):
                with st.expander(f"{subj_data['name']} – ⌀ {calculate_subject_average(subj_data['grades']):.2f}" if subj_data['grades'] else f"{subj_data['name']} – keine Noten"):
                    col_del, col_rename = st.columns([1,4])
                    with col_del:
                        if st.button("×", key=f"del_subj_{student_id}_{subj_key}", help="Fach löschen"):
                            del subjects[subj_key]
                            save_data(st.session_state.data)
                            st.rerun()

                    grades = subj_data["grades"]

                    # Notenliste
                    if grades:
                        grade_df = pd.DataFrame({
                            "Note": [list(NOTE_TEXT_TO_DECIMAL.keys())[list(NOTE_TEXT_TO_DECIMAL.values()).index(g)] for g in grades],
                            "Dezimal": grades
                        })
                        grade_df_styled = grade_df.style.applymap(
                            lambda v: get_note_color(v) if isinstance(v, (int,float)) else "",
                            subset=["Dezimal"]
                        )
                        st.dataframe(grade_df_styled, hide_index=True, use_container_width=True)

                    # Note hinzufügen
                    new_grade = st.selectbox("Note hinzufügen", ["—"] + ALL_GRADE_OPTIONS, key=f"add_grade_{student_id}_{subj_key}")
                    if st.button("Note speichern", key=f"save_grade_{student_id}_{subj_key}") and new_grade != "—":
                        grades.append(NOTE_TEXT_TO_DECIMAL[new_grade])
                        save_data(st.session_state.data)
                        st.rerun()

                    # Bestehende Noten bearbeiten/löschen
                    for i, grade in enumerate(grades):
                        col_note, col_del = st.columns([4,1])
                        with col_note:
                            current_text = [k for k,v in NOTE_TEXT_TO_DECIMAL.items() if v == grade][0]
                            edited = st.selectbox(
                                f"Note {i+1}",
                                ALL_GRADE_OPTIONS,
                                index=ALL_GRADE_OPTIONS.index(current_text),
                                key=f"edit_grade_{student_id}_{subj_key}_{i}"
                            )
                            if edited != current_text:
                                grades[i] = NOTE_TEXT_TO_DECIMAL[edited]
                                save_data(st.session_state.data)
                                st.rerun()

                        with col_del:
                            if st.button("×", key=f"del_grade_{student_id}_{subj_key}_{i}", help="Note löschen"):
                                del grades[i]
                                save_data(st.session_state.data)
                                st.rerun()

    with col2:
        st.markdown("**Hilfe / Tipps**")
        st.info(
            "• Noten immer über Dropdown eingeben → vermeidet Tippfehler\n"
            "• Änderungen werden automatisch in **noten_db.json** gespeichert\n"
            "• CSV-Export/-Import im Reiter Statistiken"
        )

# ────────────────────────────────────────────────
#   Seite: Statistiken
# ────────────────────────────────────────────────

elif page == "📊 Statistiken":

    st.header("Klassen-Statistiken")

    if not st.session_state.data:
        st.info("Noch keine Daten vorhanden.")
    else:
        all_grades = []
        subject_grades = {}
        student_avgs = []

        for student in st.session_state.data.values():
            subjs = student.get("subjects", {})
            student_avg = calculate_student_average(subjs)
            if student_avg is not None:
                student_avgs.append(student_avg)

            for subj_name, subj_data in subjs.items():
                grades = subj_data.get("grades", [])
                all_grades.extend(grades)
                subject_grades.setdefault(subj_name, []).extend(grades)

        # Gesamtdurchschnitt
        if student_avgs:
            total_avg = round(sum(student_avgs)/len(student_avgs), 2)
            st.metric("⌀ Gesamtdurchschnitt der Klasse", f"{total_avg:.2f} {grade_to_emoji(total_avg)}")

        # Notenverteilung
        if all_grades:
            grade_text_counts = {}
            for g in all_grades:
                text = [k for k,v in NOTE_TEXT_TO_DECIMAL.items() if v == g][0]
                grade_text_counts[text] = grade_text_counts.get(text, 0) + 1

            df_dist = pd.DataFrame({
                "Note": list(grade_text_counts.keys()),
                "Anzahl": list(grade_text_counts.values())
            }).sort_values("Note")

            fig = px.bar(df_dist, x="Note", y="Anzahl", title="Notenverteilung (alle Fächer)", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

        # CSV Export
        st.subheader("Daten exportieren / importieren")

        # Export
        def convert_df_to_csv():
            export_rows = []
            for sid, s in st.session_state.data.items():
                for subj_key, subj in s.get("subjects", {}).items():
                    for grade in subj.get("grades", []):
                        export_rows.append({
                            "Schüler-ID": sid,
                            "Name": s["name"],
                            "Klasse": s.get("class",""),
                            "Fach": subj["name"],
                            "Note (Text)": [k for k,v in NOTE_TEXT_TO_DECIMAL.items() if v == grade][0],
                            "Note (Dezimal)": grade
                        })
            df_export = pd.DataFrame(export_rows)
            return df_export.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

        csv_data = convert_df_to_csv()
        st.download_button(
            label="CSV exportieren (alle Daten)",
            data=csv_data,
            file_name="schulnoten_export.csv",
            mime="text/csv"
        )

        # Import
        uploaded_file = st.file_uploader("CSV importieren", type="csv")
        if uploaded_file is not None:
            try:
                df_import = pd.read_csv(uploaded_file, encoding="utf-8-sig")
                st.write("Vorschau der importierten Daten:")
                st.dataframe(df_import.head(8))

                if st.button("**Import jetzt ausführen** (vorhandene Daten bleiben erhalten)"):
                    for _, row in df_import.iterrows():
                        sid = str(row["Schüler-ID"])
                        if sid not in st.session_state.data:
                            st.session_state.data[sid] = {
                                "name": row["Name"],
                                "class": row.get("Klasse",""),
                                "subjects": {}
                            }
                        subj_name = row["Fach"]
                        subj_key = subj_name.lower().replace(" ", "_")
                        if subj_key not in st.session_state.data[sid]["subjects"]:
                            st.session_state.data[sid]["subjects"][subj_key] = {"name": subj_name, "grades": []}
                        try:
                            decimal = NOTE_TEXT_TO_DECIMAL[row["Note (Text)"]]
                            st.session_state.data[sid]["subjects"][subj_key]["grades"].append(decimal)
                        except KeyError:
                            st.warning(f"Ungültige Note übersprungen: {row['Note (Text)']}")
                    save_data(st.session_state.data)
                    st.success("Import abgeschlossen!")
                    st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Einlesen der CSV: {e}")

st.markdown("---")
st.caption(f"Stand: {datetime.now().strftime('%d.%m.%Y %H:%M')} • Daten in noten_db.json")
