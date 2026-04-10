#!/usr/bin/env python3
"""Analyze 3DGS training log and generate visualization figures."""

import re
import json
import sys
import os
import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib not installed. Install with: pip install matplotlib")
    sys.exit(1)

def parse_log(log_path):
    """Parse training log to extract step and loss data."""
    steps, losses = [], []
    with open(log_path, 'r') as f:
        content = f.read()

    # Match patterns like "Loss=0.2756439"
    # The log format: Training progress: XX%|...|XXXX/YYYY [..., Loss=X.XXXXXXX, ...]
    pattern = r'(\d+)/\d+\s+\[.*?Loss=([\d.]+)'
    for match in re.finditer(pattern, content):
        step = int(match.group(1))
        loss = float(match.group(2))
        if loss > 0:  # Skip depth loss = 0
            steps.append(step)
            losses.append(loss)

    # Remove duplicates, keep last occurrence
    seen = {}
    for s, l in zip(steps, losses):
        seen[s] = l

    steps = sorted(seen.keys())
    losses = [seen[s] for s in steps]
    return np.array(steps), np.array(losses)


def generate_figures(steps, losses, output_dir, prefix=""):
    """Generate all training analysis figures."""
    os.makedirs(output_dir, exist_ok=True)

    # Color scheme
    primary = '#2196F3'
    secondary = '#FF5722'
    accent = '#4CAF50'

    # 1. Training Loss Curve
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    ax.plot(steps, losses, color=primary, alpha=0.3, linewidth=0.5, label='Raw Loss')
    # Moving average
    window = min(50, len(losses) // 5) if len(losses) > 10 else 1
    if window > 1:
        ma = np.convolve(losses, np.ones(window)/window, mode='valid')
        ma_steps = steps[window-1:]
        ax.plot(ma_steps, ma, color=secondary, linewidth=2, label=f'Moving Avg (w={window})')
    ax.set_xlabel('Training Step', fontsize=12)
    ax.set_ylabel('Loss', fontsize=12)
    ax.set_title(f'{prefix}3DGS Training Loss Curve - AMtown02', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'training_loss_curve.png'), dpi=150)
    plt.close(fig)
    print(f"  Saved training_loss_curve.png")

    # 2. Loss Distribution
    fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    ax.hist(losses, bins=50, color=primary, alpha=0.7, edgecolor='white')
    ax.axvline(np.mean(losses), color=secondary, linestyle='--', label=f'Mean: {np.mean(losses):.4f}')
    ax.axvline(np.min(losses), color=accent, linestyle=':', label=f'Min: {np.min(losses):.4f}')
    ax.set_xlabel('Loss Value', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'{prefix}Loss Distribution', fontsize=14)
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'loss_distribution.png'), dpi=150)
    plt.close(fig)
    print(f"  Saved loss_distribution.png")

    # 3. Convergence Analysis
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Log scale loss
    axes[0,0].semilogy(steps, losses, color=primary, alpha=0.5, linewidth=0.5)
    if window > 1:
        axes[0,0].semilogy(ma_steps, ma, color=secondary, linewidth=2)
    axes[0,0].set_title('Log-Scale Loss', fontsize=11)
    axes[0,0].set_xlabel('Step')
    axes[0,0].set_ylabel('Loss (log)')
    axes[0,0].grid(True, alpha=0.3)

    # Loss gradient
    if len(losses) > 10:
        grad = np.gradient(losses)
        grad_smooth = np.convolve(grad, np.ones(window)/window, mode='valid') if window > 1 else grad
        axes[0,1].plot(steps[:len(grad_smooth)], grad_smooth, color=accent, linewidth=1)
        axes[0,1].axhline(0, color='gray', linestyle='-', alpha=0.5)
    axes[0,1].set_title('Loss Gradient', fontsize=11)
    axes[0,1].set_xlabel('Step')
    axes[0,1].set_ylabel('dLoss/dStep')
    axes[0,1].grid(True, alpha=0.3)

    # Rolling statistics
    if len(losses) > window:
        roll_mean = np.convolve(losses, np.ones(window)/window, mode='valid')
        roll_std = np.array([np.std(losses[max(0,i-window):i+1]) for i in range(window-1, len(losses))])
        x = steps[window-1:]
        axes[1,0].fill_between(x, roll_mean - roll_std, roll_mean + roll_std, alpha=0.2, color=primary)
        axes[1,0].plot(x, roll_mean, color=primary, linewidth=2)
    axes[1,0].set_title('Rolling Mean ± Std', fontsize=11)
    axes[1,0].set_xlabel('Step')
    axes[1,0].set_ylabel('Loss')
    axes[1,0].grid(True, alpha=0.3)

    # Phase comparison
    n = len(losses)
    phases = [('Early (0-25%)', losses[:n//4]),
              ('Mid (25-50%)', losses[n//4:n//2]),
              ('Late (50-75%)', losses[n//2:3*n//4]),
              ('Final (75-100%)', losses[3*n//4:])]
    phase_names = [p[0] for p in phases]
    phase_means = [np.mean(p[1]) for p in phases]
    colors = [primary, '#FFC107', secondary, accent]
    axes[1,1].bar(phase_names, phase_means, color=colors, alpha=0.8)
    axes[1,1].set_title('Phase-wise Mean Loss', fontsize=11)
    axes[1,1].set_ylabel('Mean Loss')
    for i, v in enumerate(phase_means):
        axes[1,1].text(i, v + 0.002, f'{v:.4f}', ha='center', fontsize=9)

    fig.suptitle(f'{prefix}Convergence Analysis - AMtown02', fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'convergence_analysis.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved convergence_analysis.png")

    # 4. Summary Dashboard
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Loss curve (compact)
    axes[0,0].plot(steps, losses, color=primary, alpha=0.3, linewidth=0.5)
    if window > 1:
        axes[0,0].plot(ma_steps, ma, color=secondary, linewidth=2)
    axes[0,0].set_title('Training Progress', fontsize=11)
    axes[0,0].set_xlabel('Step')
    axes[0,0].set_ylabel('Loss')
    axes[0,0].grid(True, alpha=0.3)

    # Stats table
    stats = {
        'Total Steps': f'{steps[-1]:,}',
        'Initial Loss': f'{losses[0]:.6f}',
        'Final Loss': f'{losses[-1]:.6f}',
        'Min Loss': f'{np.min(losses):.6f}',
        'Max Loss': f'{np.max(losses):.6f}',
        'Mean Loss': f'{np.mean(losses):.6f}',
        'Std Dev': f'{np.std(losses):.6f}',
        'Loss Reduction': f'{(1 - losses[-1]/losses[0])*100:.1f}%',
    }
    axes[0,1].axis('off')
    table_data = [[k, v] for k, v in stats.items()]
    table = axes[0,1].table(cellText=table_data, colLabels=['Metric', 'Value'],
                            loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    axes[0,1].set_title('Training Statistics', fontsize=11)

    # Loss over epochs
    axes[1,0].hist(losses, bins=40, color=primary, alpha=0.7, edgecolor='white')
    axes[1,0].set_title('Loss Distribution', fontsize=11)
    axes[1,0].set_xlabel('Loss')
    axes[1,0].set_ylabel('Count')

    # Learning trajectory
    if len(losses) >= 100:
        chunk_size = len(losses) // 20
        chunk_means = [np.mean(losses[i:i+chunk_size]) for i in range(0, len(losses)-chunk_size+1, chunk_size)]
        chunk_x = list(range(len(chunk_means)))
        axes[1,1].plot(chunk_x, chunk_means, 'o-', color=secondary, markersize=6)
    axes[1,1].set_title('Loss Trajectory (chunked)', fontsize=11)
    axes[1,1].set_xlabel('Chunk')
    axes[1,1].set_ylabel('Mean Loss')
    axes[1,1].grid(True, alpha=0.3)

    fig.suptitle(f'{prefix}Training Summary Dashboard - AMtown02 3DGS', fontsize=14)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'summary_dashboard.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved summary_dashboard.png")

    return stats


def generate_report(stats, log_path, output_path):
    """Generate training report JSON."""
    report = {
        "dataset": "AMtown02",
        "method": "3D Gaussian Splatting",
        "implementation": "gaussian-splatting (original, Python/CUDA)",
        "gpu": "NVIDIA A100-PCIE-40GB",
        "training_log": os.path.basename(log_path),
        "statistics": stats,
    }
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"  Saved {os.path.basename(output_path)}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_training.py <log_file> [output_dir] [prefix]")
        sys.exit(1)

    log_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'figures'
    prefix = sys.argv[3] + ' ' if len(sys.argv) > 3 else ''

    print(f"Parsing {log_path}...")
    steps, losses = parse_log(log_path)
    print(f"  Found {len(steps)} data points, steps {steps[0]}-{steps[-1]}")

    print("Generating figures...")
    stats = generate_figures(steps, losses, output_dir, prefix)

    report_path = os.path.join(output_dir, 'training_report.json')
    generate_report(stats, log_path, report_path)

    print("\nDone!")
