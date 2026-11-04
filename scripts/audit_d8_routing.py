"""Check D8 topology against accumulation; does not validate real flood behaviour."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'data/processed/hydrology/flow/d8_trial_5gw0hhqc'
# Each candidate is checked against the accumulation, rather than inferred from TIFF software tags.
CONVENTIONS = {
    'whitebox': {1: (-1, 1), 2: (0, 1), 4: (1, 1), 8: (1, 0),
                 16: (1, -1), 32: (0, -1), 64: (-1, -1), 128: (-1, 0)},
    'esri': {1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1),
             16: (0, -1), 32: (-1, -1), 64: (-1, 0), 128: (-1, 1)},
}


def audit_arrays(pointer, accumulation, valid, convention):
    if pointer.shape != accumulation.shape or valid.shape != pointer.shape:
        raise ValueError('Grid shapes differ.')
    if not valid.any():
        raise ValueError('No valid cells.')
    if not np.isfinite(accumulation[valid]).all() or (accumulation[valid] < 1).any():
        raise ValueError('Accumulation must be finite and at least one cell.')
    if not np.isin(pointer[valid], [0, *convention]).all():
        raise ValueError('Unknown pointer codes.')
    expected = np.ones(pointer.shape, dtype=np.float64)
    terminals = valid & (pointer == 0)
    outward = 0
    for code, (dr, dc) in convention.items():
        r, c = np.where(valid & (pointer == code))
        nr, nc = r + dr, c + dc
        inside = (nr >= 0) & (nc >= 0) & (nr < valid.shape[0]) & (nc < valid.shape[1])
        linked = inside.copy()
        linked[inside] &= valid[nr[inside], nc[inside]]
        outward += int((~linked).sum())
        terminals[r[~linked], c[~linked]] = True
        np.add.at(expected, (nr[linked], nc[linked]), accumulation[r[linked], c[linked]])
    residual = accumulation[valid] - expected[valid]
    mismatches = int((~np.isclose(residual, 0, atol=1e-5, rtol=0)).sum())
    terminal_total = float(accumulation[terminals].sum())
    count = int(valid.sum())
    return {
        'valid_cells': count,
        'local_balance_mismatch_cells': mismatches,
        'maximum_absolute_balance_residual_cells': float(np.abs(residual).max()),
        'terminal_cells': int(terminals.sum()),
        'nonzero_pointers_leaving_valid_domain': outward,
        'terminal_accumulation_sum_cells': terminal_total,
        'terminal_mass_balance_matches': bool(np.isclose(terminal_total, count, atol=1e-5, rtol=0)),
        'internally_consistent': mismatches == 0 and bool(np.isclose(terminal_total, count, atol=1e-5, rtol=0)),
    }


def build_report(folder):
    paths = [folder / 'ballari_d8_pointer.tif', folder / 'ballari_d8_accumulation_cells.tif']
    with rasterio.open(paths[0]) as p, rasterio.open(paths[1]) as a:
        if (p.crs, p.shape, p.transform) != (a.crs, a.shape, a.transform):
            raise ValueError('Raster grids differ.')
        pv, av = p.read(1), a.read(1)
        valid = p.read_masks(1) > 0
        if not np.array_equal(valid, a.read_masks(1) > 0):
            raise ValueError('Valid-cell masks differ.')
        candidates = {name: audit_arrays(pv, av, valid, directions) for name, directions in CONVENTIONS.items()}
        matches = [name for name, result in candidates.items() if result['internally_consistent']]
        return {
            'status': 'internal_routing_audit_only',
            'sources': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
            'crs': str(p.crs), 'shape': list(p.shape), 'transform': list(p.transform),
            'cell_area_m2': abs(p.transform.a * p.transform.e - p.transform.b * p.transform.d),
            'consistent_direction_conventions': matches,
            'convention_results': candidates,
            'limitations': [
                'Internal consistency does not establish drainage positional accuracy or flood-prediction skill.',
                'Direction convention is inferred from consistency with the paired accumulation, not generation logs.',
                'DEM conditioning, upstream domain completeness and physical drainage capacity require independent review.',
            ],
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=DEFAULT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.folder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2))
    if len(report['consistent_direction_conventions']) != 1:
        raise SystemExit('A unique internally consistent convention was not established.')
