#!/usr/bin/env python
"""
Convenience script to run the Patient Digital Twin application.

Usage:
    python run.py          # Run the Streamlit app
    python run.py --seed   # Seed the database first, then run
    python run.py --index  # Index patient data for RAG, then run
"""

import subprocess
import sys


def seed_database():
    """Seed the database with synthetic patients."""
    print("Seeding database...")
    from src.database.seed import seed_database

    seed_database()


def index_patients():
    """Index all patients for RAG search."""
    print("Indexing patients for RAG...")
    from src.rag import get_retriever

    retriever = get_retriever()
    count = retriever.index_all_patients()
    print(f"Indexed {count} documents")


def run_app():
    """Run the Streamlit application."""
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "src/app/streamlit_app.py"],
        check=True,
    )


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if "--seed" in args:
        seed_database()

    if "--index" in args:
        index_patients()

    run_app()


if __name__ == "__main__":
    main()
