"""Controlled yaw experiment; ground-truth membership never uses perturbed calibration.

Metric counts point/object pairs (overlapping boxes can count a point twice).
Denominator: finite points in original 3D boxes visible in the original camera.
Points leaving the image under perturbation are misses, not removed denominators.
Written for this lab with Codex assistance; uses repository starter geometry/IO.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from starter.datasets import load_frame
from starter.projection import velo_to_cam, cam_to_image, project_velo_to_image, perturb_extrinsic

CLASSES = ('Car', 'Van', 'Pedestrian', 'Cyclist')


def points_in_box(points_cam, obj):
    """Inverse KITTI yaw; location is bottom center, y lies in [-h, 0]."""
    c, s = np.cos(obj.rotation_y), np.sin(obj.rotation_y)
    rotation = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    local = (points_cam - obj.location) @ rotation
    h, w, length = obj.dimensions
    return ((np.abs(local[:, 0]) <= length / 2)
            & (local[:, 1] >= -h) & (local[:, 1] <= 0)
            & (np.abs(local[:, 2]) <= w / 2))


def prepare_frame(data_root, frame):
    fr = load_frame(data_root, frame)
    points = fr['points'][np.isfinite(fr['points']).all(axis=1)]
    original_cam = velo_to_cam(points[:, :3], fr['calib'])
    # Baseline FOV fixes the evaluation cohort, including for truncated boxes.
    _, _, valid = cam_to_image(original_cam, fr['calib'].P2, fr['image'].shape)
    members = [(obj, points_in_box(original_cam, obj) & valid)
               for obj in fr['labels'] if obj.type in CLASSES]
    return fr, points, members


def evaluate(fr, points, members, yaw):
    uv, _, mask = project_velo_to_image(
        points, perturb_extrinsic(fr['calib'], yaw_deg=yaw), fr['image'].shape)
    full_uv = np.full((len(points), 2), np.nan)
    full_uv[mask] = uv
    stats = {name: dict(object_count=0, object_points=0, hits=0) for name in CLASSES}
    for obj, membership in members:
        xy = full_uv[membership]
        x1, y1, x2, y2 = obj.bbox
        hits = ((xy[:, 0] >= x1) & (xy[:, 0] <= x2)
                & (xy[:, 1] >= y1) & (xy[:, 1] <= y2))
        row = stats[obj.type]
        row['object_count'] += 1
        row['object_points'] += int(membership.sum())
        row['hits'] += int(hits.sum())
    total = dict(n_points=len(points), inside_image=int(mask.sum()),
                 object_points=sum(r['object_points'] for r in stats.values()),
                 hits=sum(r['hits'] for r in stats.values()))
    for row in [total, *stats.values()]:
        row['hit_ratio'] = row['hits'] / row['object_points'] if row['object_points'] else np.nan
    return total, stats


def write_csv(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, float_format='%.10f',
                              na_rep='NaN', lineterminator='\n')
    print(f'{len(rows)} rows -> {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                    formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data-root', default='data/kitti_mini', help='KITTI-format dataset root')
    parser.add_argument('--frames', nargs='+', default=['000008', '000011', '000049'], help='Frame IDs')
    parser.add_argument('--yaw-levels', nargs='+', type=float, default=[0, .5, 1, 2, 3], help='LiDAR z-axis yaw in degrees')
    parser.add_argument('--out', default='results/yaw_perturb_sweep.csv', help='Frame metric CSV')
    parser.add_argument('--class-out', default='results/yaw_perturb_by_class.csv', help='Per-frame/class metric CSV; absent classes have NaN ratio')
    args = parser.parse_args()
    if not np.isfinite(args.yaw_levels).all():
        parser.error('yaw levels must be finite')
    rows, class_rows = [], []
    for frame in sorted(set(args.frames)):
        fr, points, members = prepare_frame(args.data_root, frame)
        for yaw in sorted(set(args.yaw_levels)):
            total, stats = evaluate(fr, points, members, yaw)
            key = dict(dataset=Path(args.data_root).name, frame=frame, yaw_deg=yaw)
            rows.append({**key, **total})
            for name in CLASSES:
                class_rows.append({**key, 'class_name': name, **stats[name]})
            print(f'{frame} yaw={yaw:g}: {total}')
    write_csv(rows, args.out)
    write_csv(class_rows, args.class_out)


if __name__ == '__main__':
    main()
