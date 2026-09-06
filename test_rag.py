"""Test and CLI demonstration script for Telecom RAG Chatbot."""

import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from src.config import settings, validate_config
from src.ingestion import ingest_all_sources, get_vectorstore
from src.retriever import get_merged_retriever
from src.rag_chain import query_telecom_rag

console = Console()

TEST_QUERIES = [
    {
        "domain": "FAQ & Customer Billing / Roaming",
        "question": "What are the roaming charges in the EU, and how do I activate international roaming?",
        "expected_source": "faqs.csv",
    },
    {
        "domain": "Technical Reference Guide (Network Diagnostics)",
        "question": "What are the diagnostic steps for troubleshooting mobile connectivity issues and poor signal strength?",
        "expected_source": "telecom_technical_guide.pdf",
    },
    {
        "domain": "Operations Database (Tickets & Outages)",
        "question": "Are there any active cell tower outages in the Northridge area, and what was the resolution for ticket TK-001 regarding mobile internet?",
        "expected_source": "tickets.db",
    },
]


def check_and_prepare_collections(force: bool = False):
    """Ensure all three Chroma collections are populated."""
    vs_faqs = get_vectorstore(settings.COLLECTION_FAQS)
    vs_manuals = get_vectorstore(settings.COLLECTION_MANUALS)
    vs_db = get_vectorstore(settings.COLLECTION_DB)

    counts = {
        settings.COLLECTION_FAQS: vs_faqs._collection.count(),
        settings.COLLECTION_MANUALS: vs_manuals._collection.count(),
        settings.COLLECTION_DB: vs_db._collection.count(),
    }

    if force or any(c == 0 for c in counts.values()):
        console.print("[yellow][*] One or more vector collections are empty or --reingest specified. Starting ingestion...[/yellow]")
        return ingest_all_sources(force=force)

    console.print("[green][+] ChromaDB Collections Verified:[/green]")
    for name, count in counts.items():
        console.print(f"    - [cyan]{name}[/cyan]: [bold]{count}[/bold] vectors")
    return counts


def display_query_result(query: str, result: dict):
    """Render retrieved sources and LLM answer in formatted Rich panels."""
    table = Table(title="Retrieved Knowledge Chunks", border_style="dim", header_style="bold magenta")
    table.add_column("#", justify="center", style="cyan", width=3)
    table.add_column("Source File", style="green", width=24)
    table.add_column("Type / Section", style="yellow", width=18)
    table.add_column("Snippet Preview", style="white")

    for idx, doc in enumerate(result["source_documents"], 1):
        src = doc.metadata.get("source", "Unknown")
        src_type = doc.metadata.get("source_type", "doc")
        details = []
        if "page" in doc.metadata:
            details.append(f"p. {doc.metadata['page']}")
        if "ticket_id" in doc.metadata:
            details.append(f"{doc.metadata['ticket_id']}")
        if "category" in doc.metadata:
            details.append(f"{doc.metadata['category']}")
        tag = f"{src_type} ({', '.join(details)})" if details else src_type

        snippet = doc.page_content.replace("\n", " ")[:95] + "..."
        table.add_row(str(idx), src, tag, snippet)

    console.print(table)
    console.print()

    console.print(Panel(
        Markdown(result["answer"]),
        title="[bold green]Telecom AI Response[/bold green]",
        border_style="green"
    ))
    console.print()


def run_benchmark_tests():
    """Execute test queries across the 3 distinct knowledge domains."""
    console.print(Panel.fit(
        "[bold cyan]TELECOM RAG CHATBOT - VERIFICATION SUITE[/bold cyan]\n"
        "[dim]Testing Multi-Collection Merged Retrieval (FAQ + PDF Guide + SQLite DB) with Google Gemini[/dim]",
        border_style="cyan"
    ))

    retriever = get_merged_retriever(k_faqs=2, k_manuals=3, k_db=2)

    for i, test_case in enumerate(TEST_QUERIES, 1):
        console.rule(f"[bold yellow]Test Case {i}: {test_case['domain']}[/bold yellow]")
        console.print(f"[bold white]Query:[/bold white] [green]{test_case['question']}[/green]\n")

        with console.status("[bold cyan]Retrieving context across all 3 ChromaDB collections and querying Gemini...[/bold cyan]"):
            result = query_telecom_rag(test_case["question"], retriever=retriever)

        display_query_result(test_case["question"], result)


def run_interactive_mode():
    """Run an interactive CLI chat loop where questions are asked by the user."""
    console.print(Panel.fit(
        "[bold green]Telecom RAG Interactive Terminal Chat[/bold green]\n"
        "[dim]Ask any question about customer plans, network diagnostics, outages, or support tickets.[/dim]\n\n"
        "[bold yellow]💡 Example questions you can ask:[/bold yellow]\n"
        "  [white]• What are the roaming charges in the EU, and how do I activate it?[/white]\n"
        "  [white]• Why is my mobile internet slow and how can I fix it?[/white]\n"
        "  [white]• What are the diagnostic steps for troubleshooting poor signal strength?[/white]\n"
        "  [white]• Are there any active cell tower outages in the Northridge area?[/white]\n"
        "  [white]• What was the resolution for ticket TK-001 regarding mobile internet?[/white]\n"
        "  [white]• How do I replace a lost SIM card or enable VoLTE?[/white]\n\n"
        "[dim]Type 'exit' or 'quit' to end session.[/dim]",
        border_style="green"
    ))

    retriever = get_merged_retriever(k_faqs=2, k_manuals=3, k_db=2)

    while True:
        try:
            user_query = console.input("[bold cyan]Ask Question > [/bold cyan]").strip()
            if not user_query:
                continue
            if user_query.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Exiting session. Goodbye![/yellow]")
                break

            with console.status("[bold green]Retrieving multi-source context and thinking...[/bold green]"):
                result = query_telecom_rag(user_query, retriever=retriever)

            display_query_result(user_query, result)

        except KeyboardInterrupt:
            console.print("\n[yellow]Session cancelled by user.[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")


def main():
    parser = argparse.ArgumentParser(
        description="Telecom RAG Chatbot - Ask questions interactively or via CLI argument"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Direct telecom question to ask the chatbot (e.g. 'How do I activate roaming?')"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive terminal chat session where you can ask questions"
    )
    parser.add_argument(
        "--benchmark", "-b",
        action="store_true",
        help="Run pre-set automated benchmark verification tests"
    )
    parser.add_argument(
        "--reingest",
        action="store_true",
        help="Force re-ingest all files into ChromaDB"
    )
    args = parser.parse_args()

    try:
        validate_config()
    except Exception as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)

    # Verify collections
    check_and_prepare_collections(force=args.reingest)

    if args.query:
        # User passed a question directly via command line
        console.print(f"\n[bold white]User Question:[/bold white] [green]{args.query}[/green]\n")
        retriever = get_merged_retriever(k_faqs=2, k_manuals=3, k_db=2)
        with console.status("[bold green]Retrieving multi-source context and thinking...[/bold green]"):
            result = query_telecom_rag(args.query, retriever=retriever)
        display_query_result(args.query, result)
    elif args.benchmark:
        run_benchmark_tests()
    else:
        # Default mode: interactive chat where questions are asked by the user
        run_interactive_mode()


if __name__ == "__main__":
    main()
