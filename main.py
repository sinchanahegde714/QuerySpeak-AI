import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import initialize_agent, AgentType


# --------------------------------------
# LOAD ENV VARIABLES
# --------------------------------------
load_dotenv()


# --------------------------------------
# BUILD THE LLM (Groq - stable model)
# --------------------------------------
def build_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing in .env")

    llm = ChatGroq(
        api_key=api_key,
        model="llama-3.1-8b-instant",   # ✅ stable & supported model
        temperature=0
    )
    return llm


# --------------------------------------
# BUILD SQL AGENT
# --------------------------------------
def build_agent(llm):
    db = SQLDatabase.from_uri("sqlite:///database.db")

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
    return agent


# --------------------------------------
# MAIN LOOP
# --------------------------------------
def main():
    print("\n🚀 SQL Agent Starting...\n")

    llm = build_llm()
    agent = build_agent(llm)

    print("✨ SQL Agent Ready!")
    print("Ask anything about the employees table.")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("❓ Your Question: ")

        if question.lower() in ["exit", "quit"]:
            print("\n👋 Goodbye!")
            break

        try:
            answer = agent.invoke({"input": question})["output"]  # invoke instead of run
            print("\n🟢 Answer:\n", answer, "\n")

        except Exception as e:
            print("\n❌ Error:", e, "\n")


# --------------------------------------
# RUN
# --------------------------------------
if __name__ == "__main__":
    main()
