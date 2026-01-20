#!/usr/bin/env python
"""
Convenience script to run the Patient Digital Twin application.

Usage:
    python run.py                              # Run with defaults (Google Gemini)
    python run.py --seed                       # Seed the database first, then run
    python run.py --index                      # Index patient data for RAG, then run
    python run.py --llm anthropic              # Use Anthropic Claude
    python run.py --llm openai --model gpt-4o  # Use OpenAI GPT-4o
    python run.py --llm google --model gemini-2.0-flash  # Use Gemini Flash

LLM Providers and Models:
    anthropic: claude-sonnet-4-20250514, claude-opus-4-20250514
    openai:    gpt-4o, gpt-4-turbo, gpt-4o-mini
    google:    gemini-2.5-pro (default), gemini-2.0-flash, gemini-1.5-pro
"""

import argparse
import os
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
    parser = argparse.ArgumentParser(
        description="Run the Patient Digital Twin application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
LLM Providers and recommended models:
  anthropic  claude-sonnet-4-20250514, claude-opus-4-20250514
  openai     gpt-4o, gpt-4-turbo, gpt-4o-mini
  google     gemini-2.5-pro (default), gemini-2.0-flash, gemini-1.5-pro
        """,
    )

    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed the database with synthetic patients before running",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Index patient data for RAG search before running",
    )
    parser.add_argument(
        "--llm",
        choices=["anthropic", "openai", "google"],
        default="google",
        help="LLM provider to use (default: google)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name (default: provider-specific default)",
    )

    args = parser.parse_args()

    # Set default model based on provider if not specified
    default_models = {
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4o",
        "google": "gemini-2.5-pro",
    }

    model = args.model or default_models[args.llm]

    # Set environment variables for the LLM configuration
    os.environ["LLM_PROVIDER"] = args.llm
    os.environ["MODEL_NAME"] = model

    print(f"Using LLM: {args.llm} / {model}")

    if args.seed:
        seed_database()

    if args.index:
        index_patients()

    run_app()


if __name__ == "__main__":
    main()
