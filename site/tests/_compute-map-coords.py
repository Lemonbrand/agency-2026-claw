#!/usr/bin/env python3
"""
Fit an affine projection from (lat, lng) to SVG (x, y) using known
state/province centroids and the SVG centroid coords measured by Playwright.

Then apply the fit to each data-center city's GPS coords to produce SVG
coordinates ready to paste into the overlay.

Usage:
  python3 tests/_compute-map-coords.py
"""

# Calibration: state/province centroid in the SVG, in viewBox space, taken
# from Playwright getCTM-aware bbox extraction (tests/calibrate-map.spec.js).
# (lng, lat, svg_x, svg_y)
CALIBRATION = [
    ('US-CA',  -119.5, 37.0,  268.76, 829.15),
    ('US-OR',  -120.5, 43.9,  285.71, 729.09),
    ('US-WA',  -121.5, 47.4,  304.52, 685.10),
    ('US-NV',  -116.6, 39.3,  306.58, 818.54),
    ('US-AZ',  -111.7, 34.2,  337.17, 902.51),
    ('US-TX',  -99.2,  31.5,  472.71, 972.02),
    ('US-NY',  -75.6,  42.9,  747.54, 788.26),
    ('US-VA',  -78.7,  37.7,  720.31, 870.17),
    ('US-FL',  -82.5,  28.7,  680.53, 1025.15),
    ('CA-ON',  -85.0,  50.0,  649.58, 705.02),
]

CITIES = [
    # Data-center / HQ locations to plot.
    # (label, lng, lat, country)
    ('San Francisco (Anthropic + OpenAI HQ)', -122.42, 37.77, 'US'),
    ('Boardman OR (AWS us-west-2)',           -119.70, 45.66, 'US'),
    ('Ashburn VA (AWS us-east-1)',             -77.49, 39.02, 'US'),
    ('Dallas TX (Azure us-south-central)',     -96.80, 32.78, 'US'),
    ('New York / NJ',                           -74.00, 40.71, 'US'),
    ('Toronto · Cohere',                        -79.38, 43.65, 'CA'),
    ('Montreal · OVH / OpenAI Vertex',          -73.55, 45.50, 'CA'),  # for completeness
]


def solve_3x3(A, b):
    """Solve a 3x3 linear system A * x = b using Cramer's rule."""
    def det(m):
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    D = det(A)
    if abs(D) < 1e-12:
        raise ValueError('singular system')
    out = []
    for col in range(3):
        Mc = [row[:] for row in A]
        for r in range(3):
            Mc[r][col] = b[r]
        out.append(det(Mc) / D)
    return out


def fit_affine(points, axis):
    """
    Fit svg_axis = A * lng + B * lat + C using ordinary least squares.
    points: list of (id, lng, lat, svg_x, svg_y).
    axis: 'x' or 'y'.
    Returns (A, B, C).
    """
    target_idx = 3 if axis == 'x' else 4
    # Normal equations: (X^T X) p = X^T y, where each row of X is [lng, lat, 1]
    sxx = syy = sxy = sx = sy = sn = 0.0
    sxz = syz = sz = 0.0
    for p in points:
        lng, lat = p[1], p[2]
        z = p[target_idx]
        sxx += lng * lng
        syy += lat * lat
        sxy += lng * lat
        sx += lng
        sy += lat
        sn += 1.0
        sxz += lng * z
        syz += lat * z
        sz += z
    M = [
        [sxx, sxy, sx],
        [sxy, syy, sy],
        [sx,  sy,  sn],
    ]
    rhs = [sxz, syz, sz]
    return solve_3x3(M, rhs)


def project(lng, lat, fx, fy):
    return (
        fx[0] * lng + fx[1] * lat + fx[2],
        fy[0] * lng + fy[1] * lat + fy[2],
    )


def main():
    fx = fit_affine(CALIBRATION, 'x')
    fy = fit_affine(CALIBRATION, 'y')
    print('Affine fit (svg = A * lng + B * lat + C):')
    print(f'  svg_x = {fx[0]:.4f} * lng + {fx[1]:.4f} * lat + {fx[2]:.4f}')
    print(f'  svg_y = {fy[0]:.4f} * lng + {fy[1]:.4f} * lat + {fy[2]:.4f}')

    print('\nResidual on calibration anchors:')
    err_x = []
    err_y = []
    for c in CALIBRATION:
        lng, lat, sx, sy = c[1], c[2], c[3], c[4]
        px, py = project(lng, lat, fx, fy)
        ex = px - sx
        ey = py - sy
        err_x.append(ex)
        err_y.append(ey)
        print(f'  {c[0]:6}  ({lng:6.1f}, {lat:5.1f}) -> svg ({px:7.1f}, {py:7.1f})  err ({ex:+5.1f}, {ey:+5.1f})')
    rms_x = (sum(e * e for e in err_x) / len(err_x)) ** 0.5
    rms_y = (sum(e * e for e in err_y) / len(err_y)) ** 0.5
    print(f'  RMS error: ({rms_x:.1f}, {rms_y:.1f})  (smaller is better; viewBox is 1711×1992)')

    print('\nCity SVG coordinates:')
    for label, lng, lat, country in CITIES:
        px, py = project(lng, lat, fx, fy)
        print(f'  {country}  cx={int(round(px)):4d}  cy={int(round(py)):4d}   {label}')


if __name__ == '__main__':
    main()
