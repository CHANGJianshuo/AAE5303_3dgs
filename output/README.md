# Output Models

Trained 3D Gaussian Splatting models for the AMtown02 scene.

## Files (not tracked by git)

| File | Size | Iterations | Gaussians | Final Loss |
|------|------|------------|-----------|------------|
| `amtown02_10k.ply` | 807 MB | 10,000 | 3,410,439 | 0.1644 |
| `amtown02_30k.ply` | 1.4 GB | 30,000 | 5,741,661 | 0.1362 |

Both models are PLY files (binary little endian) containing 3D Gaussians
with SH degree 3 (48 coefficients per Gaussian).

## Why not in git

The PLY files exceed GitHub's 100 MB file limit and are excluded via
`.gitignore`. To obtain the models, either:

1. **Re-train**: Run `scripts/03_train_3dgs.sh` on a CUDA GPU
   (A100 or similar, ~15 min for 10k, ~40 min for 30k at `-d 4`).
2. **Contact the author** for a direct download link.

## Viewing the models

PLY files of this size are slow in CloudCompare. Recommended viewers:

- **SuperSplat** (web-based, fastest): https://superspl.at/editor
- **gsplat.js** / **Three.js** with GaussianSplat viewer
- **Inria SIBR viewer** (from original 3DGS repo)

## Training reports

Per-run statistics are in `figures/10k/training_report.json` and
`figures/30k/training_report.json`.
