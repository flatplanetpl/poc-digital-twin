#!/usr/bin/env python3
"""Check Qdrant index statistics and health.

Usage:
    python scripts/check_index.py
    python scripts/check_index.py --test-query "what did I talk about with John?"
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexer import VectorStore
from src.storage.contact_registry import ContactRegistry
from src.storage.document_registry import DocumentRegistry


def main():
    parser = argparse.ArgumentParser(description="Check Qdrant index statistics")
    parser.add_argument(
        "--test-query",
        type=str,
        help="Run a test search query",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of results for test query (default: 3)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("INDEX HEALTH CHECK")
    print("=" * 60)

    # Check Qdrant
    print("\n📊 Qdrant Vector Store:")
    try:
        vs = VectorStore()
        stats = vs.get_stats()

        if stats["exists"]:
            print(f"   ✅ Collection exists")
            print(f"   📄 Points (chunks): {stats['points_count']:,}")
            print(f"   🔄 Status: {stats['status']}")
        else:
            print("   ❌ Collection does not exist")
            print("   Run: python scripts/ingest.py --source ./data/")
            return
    except Exception as e:
        print(f"   ❌ Error connecting to Qdrant: {e}")
        print("   Make sure Qdrant is running: docker-compose up -d")
        return

    # Check Contact Registry
    print("\n👥 Contact Registry:")
    try:
        cr = ContactRegistry()
        contact_stats = cr.get_stats()
        print(f"   📇 Total contacts: {contact_stats['total_contacts']:,}")
        print(f"   💬 Total messages tracked: {contact_stats['total_messages']:,}")
        if contact_stats["by_source"]:
            print(f"   📁 By source:")
            for source, count in contact_stats["by_source"].items():
                print(f"      - {source}: {count:,}")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

    # Check Document Registry (chunk details)
    print("\n📦 Document Registry (chunk details):")
    try:
        dr = DocumentRegistry()
        chunk_stats = dr.get_chunk_details_stats()
        if chunk_stats["total_chunks"] > 0:
            print(f"   📄 Chunks with heavy metadata: {chunk_stats['total_chunks']:,}")
            print(f"   📌 Pinned: {chunk_stats['pinned_count']}")
            print(f"   ✓ Approved: {chunk_stats['approved_count']}")
            if chunk_stats["by_source"]:
                print(f"   📁 By source:")
                for source, count in chunk_stats["by_source"].items():
                    print(f"      - {source}: {count:,}")
        else:
            print("   ℹ️  No chunk details stored (--optimize not used)")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

    # Test query
    if args.test_query:
        print(f"\n🔍 Test Query: \"{args.test_query}\"")
        print("-" * 60)
        try:
            results = vs.search(args.test_query, top_k=args.top_k)
            if results:
                for i, r in enumerate(results, 1):
                    print(f"\n   [{i}] Score: {r['score']:.4f}")
                    print(f"       Source: {r['metadata'].get('source_type', 'unknown')}")
                    if r['metadata'].get('sender'):
                        print(f"       Sender: {r['metadata']['sender']}")
                    if r['metadata'].get('date'):
                        print(f"       Date: {r['metadata']['date'][:10]}")
                    content_preview = r['content'][:150].replace('\n', ' ')
                    print(f"       Content: {content_preview}...")
            else:
                print("   No results found")
        except Exception as e:
            print(f"   ❌ Search error: {e}")

    print("\n" + "=" * 60)
    print("✅ Health check complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
