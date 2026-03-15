"""
Tests for the internal math helpers in navicube.widget.
These are pure-Python / numpy — no Qt required.
"""
import math
import numpy as np
import pytest

from navcube.widget import (
    _norm, _rod, _vslerp, _smooth,
    _project_to_plane, _camera_basis,
    _qnorm, _quat_from_matrix, _matrix_from_quat, _qslerp,
)


# ── _norm ──────────────────────────────────────────────────────────────────

def test_norm_unit_vector():
    v = np.array([3.0, 0.0, 0.0])
    assert np.allclose(_norm(v), [1.0, 0.0, 0.0])

def test_norm_zero_vector_safe():
    v = np.array([0.0, 0.0, 0.0])
    result = _norm(v)
    # Should not raise and should return something finite
    assert np.all(np.isfinite(result))

def test_norm_preserves_direction():
    v = np.array([1.0, 2.0, 3.0])
    n = _norm(v)
    assert abs(np.linalg.norm(n) - 1.0) < 1e-10
    assert np.allclose(n, v / np.linalg.norm(v))


# ── _rod ───────────────────────────────────────────────────────────────────

def test_rod_90deg_rotation():
    # Rotate +X by 90° around +Z → should give +Y
    v    = np.array([1.0, 0.0, 0.0])
    axis = np.array([0.0, 0.0, 1.0])
    result = _rod(v, axis, math.pi / 2)
    assert np.allclose(result, [0.0, 1.0, 0.0], atol=1e-10)

def test_rod_360deg_returns_original():
    v    = np.array([0.5, 0.5, 0.707])
    axis = np.array([0.0, 1.0, 0.0])
    result = _rod(_norm(v), axis, 2 * math.pi)
    assert np.allclose(result, _norm(v), atol=1e-10)

def test_rod_zero_angle_identity():
    v    = np.array([1.0, 2.0, 3.0])
    axis = np.array([0.0, 0.0, 1.0])
    result = _rod(v, axis, 0.0)
    assert np.allclose(result, v, atol=1e-10)


# ── _vslerp ────────────────────────────────────────────────────────────────

def test_vslerp_t0_returns_v0():
    v0 = _norm(np.array([1.0, 0.0, 0.0]))
    v1 = _norm(np.array([0.0, 1.0, 0.0]))
    assert np.allclose(_vslerp(v0, v1, 0.0), v0, atol=1e-7)

def test_vslerp_t1_returns_v1():
    v0 = _norm(np.array([1.0, 0.0, 0.0]))
    v1 = _norm(np.array([0.0, 1.0, 0.0]))
    assert np.allclose(_vslerp(v0, v1, 1.0), v1, atol=1e-7)

def test_vslerp_midpoint_is_unit():
    v0 = _norm(np.array([1.0, 0.0, 0.0]))
    v1 = _norm(np.array([0.0, 1.0, 0.0]))
    mid = _vslerp(v0, v1, 0.5)
    assert abs(np.linalg.norm(mid) - 1.0) < 1e-7

def test_vslerp_antipodal_no_nan():
    # dot(v0, v1) = -1 — this was the crash case
    v0 = np.array([1.0, 0.0, 0.0])
    v1 = np.array([-1.0, 0.0, 0.0])
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        result = _vslerp(v0, v1, t)
        assert np.all(np.isfinite(result)), f"NaN/Inf at t={t}"
        assert abs(np.linalg.norm(result) - 1.0) < 1e-7


# ── _smooth ────────────────────────────────────────────────────────────────

def test_smooth_boundaries():
    assert _smooth(0.0) == pytest.approx(0.0)
    assert _smooth(1.0) == pytest.approx(1.0)

def test_smooth_clamps_outside_01():
    assert _smooth(-5.0) == pytest.approx(0.0)
    assert _smooth(10.0) == pytest.approx(1.0)

def test_smooth_monotone():
    ts = [i / 100 for i in range(101)]
    vals = [_smooth(t) for t in ts]
    assert all(vals[i] <= vals[i+1] for i in range(len(vals)-1))


# ── _project_to_plane ──────────────────────────────────────────────────────

def test_project_removes_normal_component():
    v      = np.array([1.0, 1.0, 1.0])
    normal = np.array([0.0, 0.0, 1.0])
    result = _project_to_plane(v, normal)
    assert abs(np.dot(result, _norm(normal))) < 1e-10

def test_project_to_plane_already_planar():
    v      = np.array([1.0, 1.0, 0.0])
    normal = np.array([0.0, 0.0, 1.0])
    result = _project_to_plane(v, normal)
    assert np.allclose(result, v, atol=1e-10)


# ── _camera_basis ──────────────────────────────────────────────────────────

def test_camera_basis_orthonormal():
    d = _norm(np.array([1.0, 1.0, -1.0]))
    u = np.array([0.0, 0.0, 1.0])
    B = _camera_basis(d, u)
    # Columns should be orthogonal unit vectors
    for i in range(3):
        assert abs(np.linalg.norm(B[:, i]) - 1.0) < 1e-9
    assert abs(np.dot(B[:, 0], B[:, 1])) < 1e-9
    assert abs(np.dot(B[:, 0], B[:, 2])) < 1e-9
    assert abs(np.dot(B[:, 1], B[:, 2])) < 1e-9

def test_camera_basis_direction_column():
    d = _norm(np.array([0.0, 0.0, 1.0]))
    u = np.array([0.0, 1.0, 0.0])
    B = _camera_basis(d, u)
    # Third column = -d
    assert np.allclose(B[:, 2], -d, atol=1e-9)


# ── quaternion round-trip ──────────────────────────────────────────────────

def test_quat_matrix_roundtrip():
    d = _norm(np.array([-1.0, 1.0, -1.0]))
    u = np.array([0.0, 0.0, 1.0])
    M = _camera_basis(d, u)
    q = _quat_from_matrix(M)
    M2 = _matrix_from_quat(q)
    assert np.allclose(M, M2, atol=1e-9)

def test_quat_unit():
    d = _norm(np.array([1.0, 2.0, 3.0]))
    u = _norm(np.array([0.0, 1.0, 0.0]))
    M = _camera_basis(d, u)
    q = _quat_from_matrix(M)
    assert abs(np.linalg.norm(q) - 1.0) < 1e-9


# ── _qslerp ────────────────────────────────────────────────────────────────

def test_qslerp_t0():
    d0 = _norm(np.array([1.0, 0.0, 0.0]))
    d1 = _norm(np.array([0.0, 1.0, 0.0]))
    q0 = _quat_from_matrix(_camera_basis(d0, np.array([0., 0., 1.])))
    q1 = _quat_from_matrix(_camera_basis(d1, np.array([0., 0., 1.])))
    assert np.allclose(_qslerp(q0, q1, 0.0), q0, atol=1e-7)

def test_qslerp_t1():
    d0 = _norm(np.array([1.0, 0.0, 0.0]))
    d1 = _norm(np.array([0.0, 1.0, 0.0]))
    q0 = _quat_from_matrix(_camera_basis(d0, np.array([0., 0., 1.])))
    q1 = _quat_from_matrix(_camera_basis(d1, np.array([0., 0., 1.])))
    result = _qslerp(q0, q1, 1.0)
    # Allow for quaternion double-cover (q and -q represent same rotation)
    assert np.allclose(result, q1, atol=1e-7) or np.allclose(result, -q1, atol=1e-7)

def test_qslerp_stays_unit():
    d0 = _norm(np.array([1.0, 0.0, 0.0]))
    d1 = _norm(np.array([0.0, 0.0, -1.0]))
    q0 = _quat_from_matrix(_camera_basis(d0, np.array([0., 0., 1.])))
    q1 = _quat_from_matrix(_camera_basis(d1, np.array([0., 1., 0.])))
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        q = _qslerp(q0, q1, t)
        assert abs(np.linalg.norm(q) - 1.0) < 1e-7
