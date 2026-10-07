"""Plot measured frame ratios and class ratios pooled by point/object pairs."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def style(ax):
    ax.set_xlabel('LiDAR yaw perturbation (deg)')
    ax.set_ylabel('Hit ratio (%)')
    ax.set_ylim(0, 100)
    ax.grid(alpha=.25)
    ax.legend()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', default='results/yaw_perturb_sweep.csv', help='Frame metrics')
    parser.add_argument('--class-csv', default='results/yaw_perturb_by_class.csv', help='Class metrics')
    parser.add_argument('--out-dir', default='results/figures', help='PNG destination')
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(args.csv, dtype={'frame': str})
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for frame, group in table.groupby('frame', sort=True):
        ax.plot(group.yaw_deg, group.hit_ratio * 100, marker='o', label=f'Frame {frame}')
    ax.set_title('KITTI: measured projection hits by frame')
    style(ax)
    fig.tight_layout()
    fig.savefig(out / 'yaw_sweep.png', dpi=180)
    plt.close(fig)
    table = pd.read_csv(args.class_csv)
    pooled = table.groupby(['class_name', 'yaw_deg'], sort=True)[['hits', 'object_points']].sum().reset_index()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for name, group in pooled.groupby('class_name', sort=True):
        group = group[group.object_points > 0]
        if not group.empty:
            ax.plot(group.yaw_deg, 100 * group.hits / group.object_points,
                    marker='o', label=f'{name} (n={int(group.object_points.iloc[0])})')
    ax.set_title('KITTI: class ratios pooled over three frames')
    style(ax)
    fig.tight_layout()
    fig.savefig(out / 'yaw_sweep_by_class.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
