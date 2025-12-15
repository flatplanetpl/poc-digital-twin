#!/usr/bin/env python3
"""CLI script for ingesting data into the vector store."""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.indexer import VectorStore
from src.loaders import EmailLoader, MessengerLoader, TextLoader, WhatsAppLoader


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest data into Digital Twin vector store"
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=settings.data_dir,
        help=f"Source directory containing data files (default: {settings.data_dir})",
    )

    parser.add_argument(
        "--types",
        nargs="+",
        choices=["text", "email", "whatsapp", "messenger", "all"],
        default=["all"],
        help="Types of data to ingest (default: all)",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing index before ingesting",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show index statistics and exit",
    )

    return parser.parse_args()


def get_loaders(types: list[str]) -> list:
    """Get loader instances based on requested types."""
    loaders = []

    if "all" in types:
        types = ["text", "email", "whatsapp", "messenger"]

    if "text" in types:
        loaders.append(TextLoader())
    if "email" in types:
        loaders.append(EmailLoader())
    if "whatsapp" in types:
        loaders.append(WhatsAppLoader())
    if "messenger" in types:
        loaders.append(MessengerLoader())

    return loaders


def main():
    """Main entry point for ingest script."""
    args = parse_args()

    # Initialize vector store
    print("Connecting to Qdrant...")
    try:
        vector_store = VectorStore()
    except Exception as e:
        print(f"Error connecting to Qdrant: {e}")
        print("Make sure Qdrant is running (docker-compose up -d)")
        sys.exit(1)

    # Show stats and exit if requested
    if args.stats:
        stats = vector_store.get_stats()
        print("\nIndex Statistics:")
        print(f"  Exists: {stats['exists']}")
        if stats["exists"]:
            print(f"  Documents: {stats['points_count']}")
            print(f"  Status: {stats['status']}")
        return

    # Reset index if requested
    if args.reset:
        print("Deleting existing index...")
        if vector_store.delete_collection():
            print("Index deleted.")
        else:
            print("No existing index found.")

    # Validate source directory
    if not args.source.exists():
        print(f"Error: Source directory not found: {args.source}")
        sys.exit(1)

    # Load documents
    print(f"\nLoading data from: {args.source}")
    loaders = get_loaders(args.types)

    all_documents = []
    for loader in loaders:
        print(f"  Loading {loader.source_type} files...")
        docs = loader.load(args.source)
        print(f"    Found {len(docs)} documents")
        all_documents.extend(docs)

    if not all_documents:
        print("\nNo documents found to ingest.")
        print("Make sure your data files are in the source directory.")
        return

    # Index documents
    print(f"\nIndexing {len(all_documents)} documents...")
    try:
        count = vector_store.add_documents(all_documents)
        print(f"Successfully indexed {count} documents.")
    except Exception as e:
        print(f"Error indexing documents: {e}")
        sys.exit(1)

    # Show final stats
    stats = vector_store.get_stats()
    print(f"\nIndex now contains {stats['points_count']} vectors.")


if __name__ == "__main__":
    main()
