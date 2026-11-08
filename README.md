# Personal Finance Agent

A personal finance assistant I built using LangGraph, OpenAI, and Supabase. My goal with this project was to create an AI agent that goes beyond simple chat, utilizing a structured workflow to track expenses, perform secure Text-to-SQL budget analytics, and fetch live bank campaigns via the web.

## Architecture & Features

I designed the system around a LangGraph StateGraph for deterministic routing and robust state management:

* Semantic Router: Classifies user intent (expense tracking, budget analysis, or campaign search) using strict Pydantic validation.
* Expense Tracker: Extracts structured financial data (amount, category, description) from unstructured text and logs it securely to PostgreSQL.
* Text-to-SQL Analytics: Translates natural language questions into safe, read-only SQL queries. I implemented PostgreSQL connection pooling to ensure strict data isolation per user.
* Live Campaign Intelligence: Instead of relying on static data or fragile web scrapers, the agent uses the Tavily Search API to dynamically search, filter, and summarize real-time credit card and brand campaigns, effectively bypassing SEO spam.
* Streamlit UI: A clean, session-aware chat interface for interaction.

## Tech Stack

* Orchestration: LangGraph, LangChain
* LLM: OpenAI (gpt-4o) with Structured Outputs
* Database: Supabase (PostgreSQL)
* Web Search Engine: Tavily API
* Frontend: Streamlit

## Getting Started

### Prerequisites
* Python 3.12+
* Supabase Account & Project
* OpenAI API Key
* Tavily API Key

### Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/yourusername/personal-finance-agent.git](https://github.com/yourusername/personal-finance-agent.git)
   cd personal-finance-agent
   ```

2. Set up the environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure Environment Variables:
   Rename .env.example to .env and fill in your credentials:
   ```env
   OPENAI_API_KEY="sk-..."
   SUPABASE_URL="[https://your-project.supabase.co](https://your-project.supabase.co)"
   SUPABASE_KEY="your-anon-key"
   DATABASE_URL="postgresql://postgres.[project-id]:[password]@[aws-0-...pooler.supabase.com:6543/postgres](https://aws-0-...pooler.supabase.com:6543/postgres)"
   TAVILY_API_KEY="tvly-..."
   ```

4. Initialize the Database:
   Run the SQL commands provided in database/schema.sql in your Supabase SQL Editor to create the necessary tables and indexes.

5. Run the Application:
   ```bash
   streamlit run app.py
   ```

## Design & Security Considerations

While building this, I focused heavily on making the agent reliable and secure:
* Data Isolation: All SQL queries are strictly filtered by user ID to prevent cross-tenant data leaks.
* Read-Only Analytics: The Text-to-SQL agent is restricted to SELECT operations.
* Tooling Choices: I specifically avoided fragile HTML scraping and opted for an LLM-native search tool (Tavily) to ensure the campaign extraction remains stable and deterministic.