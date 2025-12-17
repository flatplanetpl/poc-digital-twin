#!/usr/bin/env python3
"""Analyze metadata size across loaders to optimize chunk utilization.

This script helps identify which metadata fields are "heavy" and should
be moved to a separate DocumentRegistry (SQLite) instead of being stored
in Qdrant chunks.

Usage:
    python scripts/analyze_metadata.py --source ./data/
    python scripts/analyze_metadata.py --source ./data/ --detailed
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loaders import (
    AdsInterestsLoader,
    ContactsLoader,
    EmailLoader,
    LocationLoader,
    MessengerLoader,
    ProfileLoader,
    SearchHistoryLoader,
    TextLoader,
    WhatsAppLoader,
)
from src.storage.document_registry import (
    LIGHT_METADATA_FIELDS as ESSENTIAL_FIELDS,
    HEAVY_METADATA_FIELDS as MOVABLE_FIELDS,
)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (1 token ≈ 4 chars for English)."""
    return len(str(text)) // 4


def analyze_metadata(metadata: dict) -> dict:
    """Analyze a single metadata dict."""
    analysis = {
        "total_chars": 0,
        "total_tokens": 0,
        "fields": {},
        "heavy_fields": [],
        "movable_fields": [],
    }

    for key, value in metadata.items():
        value_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        char_count = len(value_str)
        token_count = estimate_tokens(value_str)

        analysis["total_chars"] += char_count
        analysis["total_tokens"] += token_count
        analysis["fields"][key] = {
            "chars": char_count,
            "tokens": token_count,
            "value_preview": value_str[:50] + "..." if len(value_str) > 50 else value_str,
        }

        # Mark heavy fields (>50 chars)
        if char_count > 50:
            analysis["heavy_fields"].append((key, char_count))

        # Mark movable fields
        if key in MOVABLE_FIELDS:
            analysis["movable_fields"].append((key, char_count))

    return analysis


def get_all_loaders() -> list:
    """Get all available loaders."""
    return [
        TextLoader(),
        EmailLoader(),
        WhatsAppLoader(),
        MessengerLoader(),
        ProfileLoader(),
        ContactsLoader(),
        LocationLoader(),
        SearchHistoryLoader(),
        AdsInterestsLoader(),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Analyze metadata size to optimize chunk utilization"
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Source directory containing data files",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed per-field breakdown",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024,
        help="Current chunk size in tokens (default: 1024)",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Error: Source directory not found: {args.source}")
        sys.exit(1)

    print("=" * 70)
    print("METADATA SIZE ANALYSIS")
    print("=" * 70)
    print(f"Source: {args.source}")
    print(f"Chunk size: {args.chunk_size} tokens")
    print()

    # Collect stats per loader
    loader_stats = defaultdict(lambda: {
        "doc_count": 0,
        "total_metadata_chars": 0,
        "total_metadata_tokens": 0,
        "movable_chars": 0,
        "movable_tokens": 0,
        "field_totals": defaultdict(int),
        "samples": [],
    })

    loaders = get_all_loaders()

    for loader in loaders:
        source_type = loader.source_type
        print(f"Loading {source_type}...", end=" ", flush=True)

        try:
            docs = loader.load(args.source)
        except Exception as e:
            print(f"Error: {e}")
            continue

        print(f"{len(docs)} documents")

        for doc in docs:
            metadata = doc.metadata
            analysis = analyze_metadata(metadata)

            stats = loader_stats[source_type]
            stats["doc_count"] += 1
            stats["total_metadata_chars"] += analysis["total_chars"]
            stats["total_metadata_tokens"] += analysis["total_tokens"]

            # Sum movable fields
            for field, chars in analysis["movable_fields"]:
                stats["movable_chars"] += chars
                stats["movable_tokens"] += estimate_tokens(str(chars))

            # Track field sizes
            for field, info in analysis["fields"].items():
                stats["field_totals"][field] += info["chars"]

            # Keep sample for detailed view
            if len(stats["samples"]) < 3:
                stats["samples"].append(analysis)

    print()
    print("=" * 70)
    print("RESULTS BY LOADER")
    print("=" * 70)

    total_docs = 0
    total_metadata_tokens = 0
    total_movable_tokens = 0
    total_content_space = 0

    for source_type, stats in sorted(loader_stats.items()):
        if stats["doc_count"] == 0:
            continue

        total_docs += stats["doc_count"]

        avg_metadata_tokens = stats["total_metadata_tokens"] // stats["doc_count"]
        avg_movable_tokens = stats["movable_tokens"] // stats["doc_count"] if stats["doc_count"] else 0
        content_space = args.chunk_size - avg_metadata_tokens
        content_after_optimization = args.chunk_size - (avg_metadata_tokens - avg_movable_tokens)

        total_metadata_tokens += stats["total_metadata_tokens"]
        total_movable_tokens += stats["movable_tokens"]
        total_content_space += content_space * stats["doc_count"]

        print(f"\n📁 {source_type.upper()}")
        print(f"   Documents: {stats['doc_count']}")
        print(f"   Avg metadata: {avg_metadata_tokens} tokens")
        print(f"   Avg content space: {content_space} tokens", end="")

        if content_space < 100:
            print(" ⚠️  CRITICAL - very little space for content!")
        elif content_space < 300:
            print(" ⚡ LOW")
        else:
            print(" ✅")

        if avg_movable_tokens > 0:
            print(f"   Movable to registry: ~{avg_movable_tokens} tokens")
            print(f"   After optimization: {content_after_optimization} tokens (+{avg_movable_tokens})")

        # Show heaviest fields
        if stats["field_totals"]:
            sorted_fields = sorted(
                stats["field_totals"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            print(f"   Top fields by size:")
            for field, total_chars in sorted_fields:
                avg_chars = total_chars // stats["doc_count"]
                movable = "📦" if field in MOVABLE_FIELDS else "🔒"
                print(f"      {movable} {field}: ~{avg_chars} chars")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 70)

    if total_docs == 0:
        print("No documents found to analyze.")
        return

    avg_metadata = total_metadata_tokens // total_docs
    avg_movable = total_movable_tokens // total_docs
    avg_content = args.chunk_size - avg_metadata
    avg_content_optimized = args.chunk_size - (avg_metadata - avg_movable)

    print(f"\n📊 Overall Statistics:")
    print(f"   Total documents: {total_docs}")
    print(f"   Average metadata: {avg_metadata} tokens per doc")
    print(f"   Average content space: {avg_content} tokens per doc")

    print(f"\n🎯 Optimization Potential:")
    print(f"   Movable to DocumentRegistry: ~{avg_movable} tokens/doc")
    print(f"   Content space after optimization: {avg_content_optimized} tokens (+{avg_movable})")
    improvement_pct = (avg_movable / avg_metadata * 100) if avg_metadata > 0 else 0
    print(f"   Improvement: {improvement_pct:.1f}% smaller metadata")

    print(f"\n💡 Recommendation:")
    if avg_content < 100:
        print("   🚨 CRITICAL: Increase CHUNK_SIZE immediately (try 2048 or 4096)")
        print("   🚨 AND use --optimize flag to move heavy metadata to SQLite")
        print("\n   Run:")
        print("   CHUNK_SIZE=2048 python scripts/ingest.py --source ./data/ --reset --optimize")
    elif avg_content < 300:
        print("   ⚡ Recommended: Use --optimize for better RAG quality")
        print("\n   Run:")
        print("   python scripts/ingest.py --source ./data/ --reset --optimize")
    elif improvement_pct > 20:
        print(f"   ✅ Optional: --optimize would give ~{improvement_pct:.0f}% more content space")
        print("\n   Run (optional):")
        print("   python scripts/ingest.py --source ./data/ --reset --optimize")
    else:
        print("   ✅ Current setup is efficient. --optimize is optional.")

    # Fields to move
    print(f"\n📦 Fields to move to DocumentRegistry:")
    for field in sorted(MOVABLE_FIELDS):
        print(f"   - {field}")

    print(f"\n🔒 Essential fields (keep in Qdrant):")
    for field in sorted(ESSENTIAL_FIELDS):
        print(f"   - {field}")


if __name__ == "__main__":
    main()
