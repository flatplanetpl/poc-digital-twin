#!/usr/bin/env python3
"""GPU detection and profile recommendation script.

Run this before installation to auto-configure GPU_PROFILE based on your hardware.

Usage:
    python scripts/detect_gpu.py           # Show recommendation
    python scripts/detect_gpu.py --apply   # Apply to .env file
    python scripts/detect_gpu.py --json    # Output as JSON
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GpuInfo:
    """Detected GPU information."""

    name: str
    vram_mb: int
    vendor: str  # nvidia, amd, intel, unknown
    driver_version: str | None = None


@dataclass
class ProfileRecommendation:
    """GPU profile recommendation result."""

    profile: str
    confidence: str  # high, medium, low
    reason: str
    detected_gpus: list[GpuInfo]
    vram_total_mb: int


# =============================================================================
# GPU Detection Functions
# =============================================================================


def detect_nvidia_gpus() -> list[GpuInfo]:
    """Detect NVIDIA GPUs using nvidia-smi."""
    gpus = []

    try:
        # Query GPU info in CSV format
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 2:
                        name = parts[0]
                        vram_mb = int(float(parts[1]))
                        driver = parts[2] if len(parts) > 2 else None

                        gpus.append(
                            GpuInfo(
                                name=name,
                                vram_mb=vram_mb,
                                vendor="nvidia",
                                driver_version=driver,
                            )
                        )
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    return gpus


def detect_amd_gpus() -> list[GpuInfo]:
    """Detect AMD GPUs using rocm-smi or system info."""
    gpus = []

    # Try rocm-smi first (Linux with ROCm)
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            for card_id, card_info in data.items():
                if card_id.startswith("card"):
                    vram_total = card_info.get("VRAM Total Memory (B)", 0)
                    vram_mb = int(vram_total) // (1024 * 1024) if vram_total else 0

                    gpus.append(
                        GpuInfo(
                            name=f"AMD GPU ({card_id})",
                            vram_mb=vram_mb,
                            vendor="amd",
                        )
                    )
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
    ):
        pass

    # Fallback: try to detect via lspci (Linux)
    if not gpus:
        try:
            result = subprocess.run(
                ["lspci"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "VGA" in line or "3D" in line:
                        if "AMD" in line or "Radeon" in line or "ATI" in line:
                            # Extract GPU name
                            match = re.search(r"\[(.+?)\]", line)
                            name = match.group(1) if match else "AMD GPU"

                            # Estimate VRAM based on model name
                            vram_mb = _estimate_amd_vram(name)

                            gpus.append(
                                GpuInfo(
                                    name=name,
                                    vram_mb=vram_mb,
                                    vendor="amd",
                                )
                            )
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass

    return gpus


def detect_intel_gpus() -> list[GpuInfo]:
    """Detect Intel integrated/discrete GPUs."""
    gpus = []

    # Try via lspci (Linux)
    try:
        result = subprocess.run(
            ["lspci"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "VGA" in line or "3D" in line:
                    if "Intel" in line:
                        match = re.search(r"\[(.+?)\]", line)
                        name = match.group(1) if match else "Intel GPU"

                        # Estimate shared memory (usually 2-4GB usable)
                        vram_mb = _estimate_intel_vram(name)

                        gpus.append(
                            GpuInfo(
                                name=name,
                                vram_mb=vram_mb,
                                vendor="intel",
                            )
                        )
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    # Try via Windows WMI
    if not gpus and sys.platform == "win32":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-WmiObject Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if not isinstance(data, list):
                    data = [data]

                for gpu in data:
                    name = gpu.get("Name", "")
                    if "Intel" in name:
                        adapter_ram = gpu.get("AdapterRAM", 0)
                        vram_mb = int(adapter_ram) // (1024 * 1024) if adapter_ram else 2048

                        gpus.append(
                            GpuInfo(
                                name=name,
                                vram_mb=vram_mb,
                                vendor="intel",
                            )
                        )
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.SubprocessError,
            json.JSONDecodeError,
        ):
            pass

    return gpus


def _estimate_amd_vram(name: str) -> int:
    """Estimate AMD GPU VRAM based on model name."""
    name_lower = name.lower()

    # RX 7000 series
    if "7900" in name:
        return 24576 if "xtx" in name_lower else 20480
    if "7800" in name:
        return 16384
    if "7700" in name or "7600" in name:
        return 8192

    # RX 6000 series
    if "6900" in name or "6950" in name:
        return 16384
    if "6800" in name:
        return 16384
    if "6700" in name:
        return 12288
    if "6600" in name:
        return 8192

    # Older or unknown
    return 4096


def _estimate_intel_vram(name: str) -> int:
    """Estimate Intel GPU VRAM based on model name."""
    name_lower = name.lower()

    # Arc discrete GPUs
    if "arc" in name_lower:
        if "a770" in name_lower:
            return 16384
        if "a750" in name_lower:
            return 8192
        if "a380" in name_lower:
            return 6144
        return 8192

    # Integrated - usually shares system RAM (estimate 2-4GB usable)
    if "iris" in name_lower:
        return 4096
    if "uhd" in name_lower:
        return 2048

    return 2048


def detect_all_gpus() -> list[GpuInfo]:
    """Detect all available GPUs."""
    gpus = []

    # Try each detection method
    gpus.extend(detect_nvidia_gpus())
    gpus.extend(detect_amd_gpus())
    gpus.extend(detect_intel_gpus())

    # Deduplicate by name
    seen = set()
    unique_gpus = []
    for gpu in gpus:
        if gpu.name not in seen:
            seen.add(gpu.name)
            unique_gpus.append(gpu)

    return unique_gpus


# =============================================================================
# Profile Recommendation
# =============================================================================


def recommend_profile(gpus: list[GpuInfo]) -> ProfileRecommendation:
    """Recommend GPU profile based on detected hardware."""

    if not gpus:
        return ProfileRecommendation(
            profile="low",
            confidence="low",
            reason="No dedicated GPU detected. Using CPU-only profile.",
            detected_gpus=[],
            vram_total_mb=0,
        )

    # Find GPU with most VRAM (for multi-GPU systems)
    best_gpu = max(gpus, key=lambda g: g.vram_mb)
    total_vram = sum(g.vram_mb for g in gpus)

    # Determine profile based on VRAM
    vram_gb = best_gpu.vram_mb / 1024

    if vram_gb >= 24:
        profile = "ultra"
        confidence = "high"
        reason = f"{best_gpu.name} with {vram_gb:.0f}GB VRAM - excellent for large models"
    elif vram_gb >= 12:
        profile = "high"
        confidence = "high"
        reason = f"{best_gpu.name} with {vram_gb:.0f}GB VRAM - great for 13B models"
    elif vram_gb >= 6:
        profile = "medium"
        confidence = "high"
        reason = f"{best_gpu.name} with {vram_gb:.0f}GB VRAM - good for 7B models"
    elif vram_gb >= 4:
        profile = "low"
        confidence = "medium"
        reason = f"{best_gpu.name} with {vram_gb:.0f}GB VRAM - limited, using small models"
    else:
        profile = "low"
        confidence = "low"
        reason = f"{best_gpu.name} with {vram_gb:.1f}GB VRAM - very limited, CPU may be better"

    # Adjust confidence for Intel integrated
    if best_gpu.vendor == "intel" and "arc" not in best_gpu.name.lower():
        confidence = "medium"
        reason += " (integrated GPU - shared memory)"

    return ProfileRecommendation(
        profile=profile,
        confidence=confidence,
        reason=reason,
        detected_gpus=gpus,
        vram_total_mb=total_vram,
    )


# =============================================================================
# .env File Management
# =============================================================================


def update_env_file(profile: str, env_path: Path | None = None) -> bool:
    """Update or create .env file with GPU_PROFILE setting.

    Args:
        profile: The profile to set
        env_path: Path to .env file (default: project root/.env)

    Returns:
        True if successful
    """
    if env_path is None:
        env_path = Path(__file__).parent.parent / ".env"

    # Read existing content or start from example
    if env_path.exists():
        content = env_path.read_text()
    else:
        example_path = env_path.parent / ".env.example"
        if example_path.exists():
            content = example_path.read_text()
        else:
            content = ""

    # Update or add GPU_PROFILE
    if "GPU_PROFILE=" in content:
        # Replace existing (commented or not)
        content = re.sub(
            r"^#?\s*GPU_PROFILE=.*$",
            f"GPU_PROFILE={profile}",
            content,
            flags=re.MULTILINE,
        )
    else:
        # Add after Qdrant section or at end
        insertion_point = content.find("# =====")
        if insertion_point > 0:
            # Find the GPU Profile section marker
            gpu_section = content.find("GPU Profile")
            if gpu_section > 0:
                # Find the commented GPU_PROFILE line and replace
                content = re.sub(
                    r"^#\s*GPU_PROFILE=.*$",
                    f"GPU_PROFILE={profile}",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content += f"\n# Auto-detected GPU Profile\nGPU_PROFILE={profile}\n"
        else:
            content += f"\nGPU_PROFILE={profile}\n"

    env_path.write_text(content)
    return True


# =============================================================================
# CLI Interface
# =============================================================================


def print_report(recommendation: ProfileRecommendation) -> None:
    """Print a human-readable report."""
    print("=" * 60)
    print("  Digital Twin - GPU Detection Report")
    print("=" * 60)
    print()

    if recommendation.detected_gpus:
        print("Detected GPUs:")
        for gpu in recommendation.detected_gpus:
            vram_gb = gpu.vram_mb / 1024
            driver_info = f" (driver: {gpu.driver_version})" if gpu.driver_version else ""
            print(f"  - {gpu.name}")
            print(f"    Vendor: {gpu.vendor.upper()}")
            print(f"    VRAM: {vram_gb:.1f} GB{driver_info}")
        print()
    else:
        print("No dedicated GPU detected.")
        print()

    print("-" * 60)
    print(f"Recommended Profile: {recommendation.profile.upper()}")
    print(f"Confidence: {recommendation.confidence}")
    print(f"Reason: {recommendation.reason}")
    print("-" * 60)
    print()

    # Show what this profile means
    profiles_info = {
        "low": ("orca-mini-3b", 3, "Basic, CPU-friendly"),
        "medium": ("mistral-7b", 5, "Balanced performance"),
        "high": ("llama-2-13b", 8, "High quality responses"),
        "ultra": ("nous-hermes-13b-Q5", 12, "Maximum quality"),
    }

    model, top_k, desc = profiles_info[recommendation.profile]
    print(f"Profile '{recommendation.profile}' settings:")
    print(f"  Model: {model}")
    print(f"  TOP_K: {top_k}")
    print(f"  Description: {desc}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Detect GPU and recommend Digital Twin profile"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply recommended profile to .env file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--profile",
        choices=["low", "medium", "high", "ultra"],
        help="Override auto-detection with specific profile (use with --apply)",
    )

    args = parser.parse_args()

    # Detect GPUs
    gpus = detect_all_gpus()

    # Get recommendation
    recommendation = recommend_profile(gpus)

    # Override if specified
    if args.profile:
        recommendation.profile = args.profile
        recommendation.reason = f"Manually set to '{args.profile}'"
        recommendation.confidence = "manual"

    # Output
    if args.json:
        output = {
            "profile": recommendation.profile,
            "confidence": recommendation.confidence,
            "reason": recommendation.reason,
            "vram_total_mb": recommendation.vram_total_mb,
            "gpus": [
                {
                    "name": g.name,
                    "vram_mb": g.vram_mb,
                    "vendor": g.vendor,
                    "driver_version": g.driver_version,
                }
                for g in recommendation.detected_gpus
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(recommendation)

    # Apply if requested
    if args.apply:
        env_path = Path(__file__).parent.parent / ".env"
        if update_env_file(recommendation.profile, env_path):
            print(f"Updated {env_path} with GPU_PROFILE={recommendation.profile}")
        else:
            print("Failed to update .env file", file=sys.stderr)
            sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
