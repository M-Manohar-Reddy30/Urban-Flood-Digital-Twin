import numpy as np
import pytest
from scripts.audit_d8_routing import audit_arrays, CONVENTIONS


def test_chain_conserves_contributing_cells():
    pointer = np.array([[2, 2, 0]])
    accumulation = np.array([[1., 2., 3.]])
    valid = np.ones(pointer.shape, dtype=bool)
    report = audit_arrays(pointer, accumulation, valid, CONVENTIONS['whitebox'])
    assert report['internally_consistent']
    assert report['terminal_cells'] == 1
    assert report['terminal_accumulation_sum_cells'] == 3
    accumulation[0, 1] = 5
    assert not audit_arrays(pointer, accumulation, valid, CONVENTIONS['whitebox'])['internally_consistent']


def test_nodata_is_a_domain_exit():
    pointer = np.array([[2, 0]])
    accumulation = np.array([[1., -9999.]])
    valid = np.array([[True, False]])
    report = audit_arrays(pointer, accumulation, valid, CONVENTIONS['whitebox'])
    assert report['internally_consistent']
    assert report['nonzero_pointers_leaving_valid_domain'] == 1


def test_invalid_codes_rejected():
    with pytest.raises(ValueError, match='Unknown pointer'):
        audit_arrays(np.array([[3]]), np.array([[1.]]), np.array([[True]]), CONVENTIONS['whitebox'])
