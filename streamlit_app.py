# streamlit_app.py
import streamlit as st
import pandas as pd
import ast
import io
import sqlite3
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

from langgraph_workflow import run_graph, get_schema
import streamlit.components.v1 as components   # For mic input


# ==============================================================  
# Session State Initialization  
# ==============================================================  
if "history" not in st.session_state:
    st.session_state.history = []

if "question_input" not in st.session_state:
    st.session_state.question_input = ""

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None


SQLITE_DB_PATH = "database.db"


# ##############################################################
# 7B FEATURE — SQL EXPLANATION (LOCAL)
# ##############################################################
def explain_sql(sql):
    sql_lower = sql.lower()
    explanation = []

    if "select" in sql_lower:
        explanation.append("• The query retrieves data from the database.")

    if " from " in sql_lower:
        table_name = sql_lower.split(" from ")[1].split()[0]
        explanation.append(f"• It reads data from the **{table_name}** table.")

    if " where " in sql_lower:
        condition = sql_lower.split(" where ")[1].split("order by")[0]
        explanation.append(f"• It filters rows using: **{condition.strip()}**.")

    if " order by " in sql_lower:
        order_col = sql_lower.split(" order by ")[1].split()[0]
        explanation.append(f"• Ordered using: **{order_col}**.")

    if " group by " in sql_lower:
        group_col = sql_lower.split(" group by ")[1].split()[0]
        explanation.append(f"• Groups rows using: **{group_col}**.")

    if " join " in sql_lower:
        explanation.append("• Query involves a JOIN between tables.")

    if " limit " in sql_lower:
        limit_val = sql_lower.split(" limit ")[1].split()[0]
        explanation.append(f"• Output limited to **{limit_val}** rows.")

    if not explanation:
        return "No explanation available."

    return "\n".join(explanation)


# ##############################################################
# 7D FEATURE — SQL OPTIMIZER (LOCAL)
# ##############################################################
def optimize_sql(sql, schema):
    optimized = sql.strip()
    optimized = optimized.replace("DISTINCT DISTINCT", "DISTINCT")

    while "  " in optimized:
        optimized = optimized.replace("  ", " ")

    if "select *" in optimized.lower():
        try:
            tbl = optimized.lower().split(" from ")[1].split()[0]
            if tbl in schema:
                cols = ", ".join([c["name"] for c in schema[tbl]])
                optimized = optimized.replace("*", cols)
        except:
            pass

    optimized = optimized.replace("( ", "(").replace(" )", ")")
    optimized = optimized.replace("= TRUE", " = 1").replace("= FALSE", " = 0")

    if "limit" not in optimized.lower():
        optimized += " LIMIT 100"

    for kw in ["select", "from", "where", "group by", "order by", "limit", "join"]:
        optimized = optimized.replace(kw, kw.upper())
        optimized = optimized.replace(kw.title(), kw.upper())

    return optimized


# ##############################################################
# 7C FEATURE — SQL FIXER ENGINE
# ##############################################################
def fix_sql(sql, schema):
    s = sql.strip()

    while ",," in s:
        s = s.replace(",,", ",")

    s = s.replace(", FROM", " FROM")

    parts = s.lower().split("select")
    if len(parts) > 1 and "from" in parts[1]:
        cols_section = parts[1].split("from")[0]
        if " " in cols_section and "," not in cols_section:
            s = s.replace(cols_section, ", ".join(cols_section.strip().split()))

    if "from" not in s.lower():
        tables = list(schema.keys())
        if tables:
            s += f" FROM {tables[0]}"

    if " join " in s.lower() and " on " not in s.lower():
        s += " ON 1=1"

    if s.lower().startswith("select") and "from" in s.lower():
        after = s.lower().split("select")[1].split("from")[0].strip()
        if after == "":
            tbl = s.lower().split("from")[1].split()[0]
            if tbl in schema:
                cols = ", ".join([c["name"] for c in schema[tbl]])
                s = s.replace("SELECT", f"SELECT {cols}")

    if "order by" in s.lower():
        try:
            tbl = s.lower().split("from")[1].split()[0]
            valid = [c["name"] for c in schema.get(tbl, [])]
            col = s.lower().split("order by")[1].strip().split()[0]
            if col not in valid:
                s = s.replace(f"ORDER BY {col}", "")
        except:
            pass

    return s.strip()


# ==============================================================  
# PAGE CONFIG  
# ==============================================================  
st.set_page_config(page_title="SQL Agent UI", layout="wide")


# ==============================================================  
# DARK MODE + BABY PINK LIGHT MODE FIX  
# INCLUDING THE FIX FOR WHITE TOP SPACE  
# ==============================================================  
def apply_theme():
    st.markdown(
        """
        <style>

/* Reset */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

/* App background */
html, body, .stApp {
    background: linear-gradient(180deg, #05070c, #020409) !important;
    color: #e5e7eb !important;
    font-family: Inter, system-ui, sans-serif;
}

/* Header */
header[data-testid="stHeader"] {
    background: #05070c !important;
    border-bottom: 1px solid #0f172a !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #070b14 !important;
    border-right: 1px solid #0f172a !important;
}

/* Sidebar buttons */
section[data-testid="stSidebar"] button {
    background: #0b1220 !important;
    color: #e5e7eb !important;
    border-radius: 12px !important;
    border: 1px solid #1e293b !important;
    padding: 12px !important;
    margin-bottom: 8px !important;
}

section[data-testid="stSidebar"] button:hover {
    background: #111827 !important;
}

/* Main buttons */
.stButton > button {
    background: linear-gradient(135deg, #1e3a8a, #2563eb) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 12px 22px !important;
    font-weight: 600 !important;
    border: none !important;
}

/* Inputs */
.stTextInput input {
    background: #0b1220 !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
    color: #e5e7eb !important;
}

/* File uploader */
div[data-testid="stFileUploader"] {
    background: #070b14 !important;
    border: 2px dashed #1e3a8a !important;
    border-radius: 16px !important;
    padding: 20px !important;
}

/* Expanders & tables */
div[data-testid="stExpander"],
div[data-testid="stDataFrame"],
div[data-testid="stAlert"] {
    background: #070b14 !important;
    border: 1px solid #0f172a !important;
    border-radius: 16px !important;
}

/* Hide footer */
footer {
    visibility: hidden;
}

        </style>
        """,
        unsafe_allow_html=True
    )
apply_theme()



# ==============================================================  
# Helper Functions  
# ==============================================================  
def parse_sql_rows(rows):
    if isinstance(rows, str):
        try:
            return ast.literal_eval(rows)
        except:
            return rows
    return rows


def add_to_history(question, sql, rows):
    st.session_state.history = [
        item for item in st.session_state.history
        if item["question"].lower() != question.lower()
    ]
    st.session_state.history.append({
        "question": question,
        "sql": sql,
        "rows": rows,
        "time": datetime.now().strftime("%H:%M:%S")
    })
    st.session_state.history = st.session_state.history[-15:]


def df_from_rows(rows):
    if isinstance(rows, list) and len(rows) > 0:
        first = rows[0]
        if isinstance(first, tuple):
            df = pd.DataFrame([list(r) for r in rows])
            df.columns = [f"Column {i+1}" for i in range(df.shape[1])]
            return df
        elif isinstance(first, dict):
            return pd.DataFrame(rows)
    return None


# ==============================================================  
# Download Helpers  
# ==============================================================  
def export_as_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def export_as_excel(df):
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name="Results")
    return buf.getvalue()


def export_as_pdf(df):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    data = [df.columns.tolist()] + df.values.tolist()

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7C3AED")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
    ]))

    doc.build([table])
    return buf.getvalue()


# ==============================================================  
# 9C — LOCAL SQL DEBUGGER  
# ==============================================================  
def debug_sql(sql):
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()

        try:
            cur.execute(sql)
            rows = cur.fetchall()

            return {
                "ok": True,
                "message": "SQL executed successfully!",
                "rows": rows[:10]
            }

        except Exception as e:
            err = str(e).lower()

            if "no such table" in err:
                return {
                    "ok": False,
                    "message": f"❌ Table does not exist.\n\nDetails: {e}\n\nHint: Check table name."
                }

            if "no such column" in err:
                return {
                    "ok": False,
                    "message": f"❌ Column not found.\n\nDetails: {e}\n\nHint: Verify column names."
                }

            if "syntax error" in err:
                return {
                    "ok": False,
                    "message": f"❌ SQL Syntax Error.\n\nDetails: {e}\n\nHint: Check commas, parentheses, missing keywords."
                }

            return {
                "ok": False,
                "message": f"❌ Unknown SQL Error:\n\n{e}"
            }

    except Exception as e:
        return {"ok": False, "message": f"❌ Severe Error: {e}"}


# ==============================================================  
# Sidebar  
# ==============================================================  
with st.sidebar:
    

    st.markdown("---")

    st.header("🧠 Smart Suggestions")
    for text in [
        "List all tables and their row counts",
        "List all employees with their project names",
        "List all rows from employees",
        "Top 5 rows by id in employees",
        "Show average, min and max of id in employees",
    ]:
        if st.button(text):
            st.session_state.question_input = text
            st.rerun()

    st.markdown("---")

    st.header("📚 Database Schema")
    try:
        schema = get_schema()
        if schema:
            for table, cols in schema.items():
                with st.expander(f"📂 {table}"):
                    for col in cols:
                        st.markdown(f"- **{col['name']}** — {col['type']}")
    except:
        st.error("Schema error")

    st.markdown("---")

    st.header("🕘 Query History")
    for i, item in enumerate(reversed(st.session_state.history)):
        if st.button(f"↺ {item['question']} ({item['time']})", key=f"hist{i}"):
            st.session_state.question_input = item["question"]
            res = run_graph(item["question"])
            st.session_state.latest_result = res
            add_to_history(item["question"], res["sql"], res["rows"])
            st.rerun()


# ==============================================================  
# MAIN UI  
# ==============================================================  
st.title("🧠QuerySpeak AI")
st.write("Ask natural language questions about your database.")


# ----------------------- 🔥 FEATURE 13A-1 — MICROPHONE INPUT -----------------------
st.markdown("### 🎤 Voice Input")

mic_html = """
<script>
function startDictation() {
    if (!('webkitSpeechRecognition' in window)) {
        alert("Use Chrome Desktop");
        return;
    }

    var recognition = new webkitSpeechRecognition();
    recognition.lang = "en-US";
    recognition.start();

    recognition.onresult = function(e) {
        var text = e.results[0][0].transcript;

        const input = window.parent.document.querySelector(
            'input[placeholder="e.g., List all employees"]'
        );

        if (input) {
            input.value = text;
            input.dispatchEvent(new Event("input", { bubbles: true }));
        }

        recognition.stop();
    };
}
</script>

<button onclick="startDictation()"
style="padding:10px 20px;
background:#7C3AED;
color:white;
border:none;
border-radius:8px;
font-weight:600;">
🎤 Speak
</button>
"""

components.html(mic_html, height=70)

# ==============================================================  
# 11E FEATURE — UPLOAD CSV INTO SQLITE DATABASE
# ==============================================================  


st.markdown("---")
st.header("📂 Upload CSV into Database")

uploaded_file = st.file_uploader(
    "Upload a CSV file to store in the database",
    type=["csv"]
)

table_name_input = st.text_input(
    "Enter table name for this CSV data (SQLite)",
    key="upload_table_name"
)

# Session state
if "uploaded_df" not in st.session_state:
    st.session_state.uploaded_df = None

if "uploaded_table" not in st.session_state:
    st.session_state.uploaded_table = None


if st.button("📥 Upload CSV into SQLite"):
    if not uploaded_file:
        st.warning("Please upload a CSV file first.")
    elif not table_name_input.strip():
        st.warning("Please enter a valid table name.")
    else:
        try:
            df_upload = pd.read_csv(uploaded_file)

            conn = sqlite3.connect(SQLITE_DB_PATH)
            cursor = conn.cursor()

            # 🔥 IMPORTANT FIX: delete ALL old tables
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%';
            """)

            for table in cursor.fetchall():
                cursor.execute(f'DROP TABLE IF EXISTS "{table[0]}"')

            conn.commit()

            # Insert ONLY uploaded CSV
            df_upload.to_sql(
                table_name_input.strip(),
                conn,
                if_exists="replace",
                index=False
            )

            conn.close()

            # Store for preview
            st.session_state.uploaded_df = df_upload
            st.session_state.uploaded_table = table_name_input.strip()

            st.success(
                f"✅ Uploaded {len(df_upload)} rows into table "
                f"'{table_name_input.strip()}'"
            )

        except Exception as e:
            st.error(f"❌ Upload failed:\n\n{e}")


# ------------------ Preview ------------------

if st.session_state.uploaded_df is not None:
    st.markdown("### 👀 Preview of uploaded data")
    st.dataframe(
        st.session_state.uploaded_df,
        height=450,
        use_container_width=True
    )



# ----------------------- 📝 Question Input -----------------------

question = st.text_input(
    "Enter your question",
    key="question_input",
    placeholder="e.g., List all employees"
)

# ----------------------- ▶ Run SQL Agent -----------------------

if st.button("Run SQL Agent"):
    question = st.session_state.question_input

    if question.strip():
        with st.spinner("Running agent..."):
            ans = run_graph(question)

        st.session_state.latest_result = ans
        add_to_history(question, ans["sql"], ans["rows"])





# ==============================================================  
# RESULTS + FEATURE 7B + 7C + 7D + 9C  
# ==============================================================  
if st.session_state.latest_result:

    ans = st.session_state.latest_result
    sql_generated = ans["sql"]

    # ===================== RESULT CARD =====================
    st.markdown("### ✅ Result")

    st.markdown(
        f"""
        <div style="
            background:#0f172a;
            padding:16px;
            border-radius:10px;
            border:1px solid #1e293b;
            margin-bottom:10px;
        ">
        <b>Answer:</b><br>{ans['final']}
        </div>
        """,
        unsafe_allow_html=True
    )

    # ===================== SQL (COLLAPSED) =====================
    with st.expander("🔍 SQL", expanded=False):
        st.code(sql_generated)

# ===================== ACTION BUTTONS =====================
    b1 = st.columns(1)[0]

    with b1:
     explain = st.button("Explain")


    if explain:
        with st.expander("🧠 Explanation", expanded=True):
            st.markdown(explain_sql(sql_generated))

     # ===================== TABLE PREVIEW =====================
    rows = parse_sql_rows(ans["rows"])
    df = df_from_rows(rows)

    if df is not None:
        st.markdown("### 📊 Preview")
        st.dataframe(df.head(10), use_container_width=True)

        if len(df) > 10:
            with st.expander("Show full table"):
                st.dataframe(df, use_container_width=True)

        with st.expander("⬇️ Download", expanded=False):
            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button("CSV", export_as_csv(df), "results.csv")
            with d2:
                st.download_button("Excel", export_as_excel(df), "results.xlsx")
            with d3:
                st.download_button("PDF", export_as_pdf(df), "results.pdf")

else:
    st.info("Ask a question or select a suggestion.")






