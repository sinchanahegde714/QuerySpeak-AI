import os
import sqlite3
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase


# ====================================================
#               SETUP: LLM + DATABASE
# ====================================================

load_dotenv()

def build_llm():
    """Builds the Groq LLM used for SQL generation."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY missing in .env!")

    return ChatGroq(
        api_key=api_key,
        model="llama-3.1-8b-instant",
        temperature=0
    )


def build_db():
    """Connects to the local SQLite database."""
    return SQLDatabase.from_uri("sqlite:///database.db")


# ====================================================
#               FEATURE 2: GET DATABASE SCHEMA
# ====================================================

def get_schema():
    """
    Returns a clean structured schema for use in Streamlit.
    """
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = [t[0] for t in cursor.fetchall()]

    schema = {}

    for table in tables:
        cursor.execute(f'PRAGMA table_info("{table}");')
        cols = cursor.fetchall()

        schema[table] = [
            {"name": col[1], "type": col[2]}
            for col in cols
        ]

    conn.close()
    return schema


# ====================================================
#               NODE IMPLEMENTATIONS
# ====================================================

def inspect_schema(state):
    db = state["db"]
    schema = db.get_table_info()
    state["schema"] = schema
    return state


def generate_sql(state):
    llm = state["llm"]
    question = state["question"]
    schema = state["schema"]

    prompt = f"""
You are an expert SQL agent working with SQLite.

Below is the database schema.
Write ONE SQL query that accurately answers the user's question.

- Use table names exactly as shown.
- Do NOT include explanations.
- Output ONLY the SQL query.

DATABASE SCHEMA:
{schema}

USER QUESTION:
{question}

Write ONLY the SQL query:
"""

    sql = llm.invoke(prompt).content
    state["sql"] = sql
    return state


# ====================================================
# ✅ FIXED SQL EXECUTION (IMPORTANT)
# ====================================================

def execute_sql(state):
    """Executes SQL using sqlite3 directly (FULL RESULTS)."""
    sql = state["sql"]

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()

        state["rows"] = rows

    except Exception as e:
        state["rows"] = f"SQL Execution Error: {e}"

    return state


def format_result(state):
    rows = state["rows"]
    question = state["question"]

    formatted = f"Question: {question}\n\nResult:\n{rows}"
    state["final"] = formatted
    return state


# ====================================================
#               RUN WORKFLOW
# ====================================================

def run_graph(question: str):
    state = {
        "question": question,
        "llm": build_llm(),
        "db": build_db()
    }

    state = inspect_schema(state)
    state = generate_sql(state)
    state = execute_sql(state)
    state = format_result(state)

    return {
        "question": state["question"],
        "sql": state["sql"],
        "rows": state["rows"],
        "final": state["final"]
    }


# ====================================================
#               MANUAL CLI TESTING
# ====================================================

if __name__ == "__main__":
    print("\n🔵 LangGraph-Style SQL Agent (Expanded DB)\n")

    while True:
        q = input("❓ Question: ")
        if q.lower() in ["exit", "quit"]:
            break

        print(run_graph(q), "\n")
