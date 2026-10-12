from science.harmonization.spatial_normalization import assign_grid_cell

def test_assign_grid_cell():
    lat, lon = assign_grid_cell(5.1234, 100.5678, grid_size=0.01)
    assert round(lat, 2) == 5.12
    assert round(lon, 2) == 100.57


def test_assign_grid_cell_half_open_boundaries():
    # Boundary: [c - res/2, c + res/2)
    # Cell 5.12 has interval [5.115, 5.125)
    lat_left, lon_left = assign_grid_cell(5.115, 100.565, grid_size=0.01)
    assert lat_left == 5.12
    assert lon_left == 100.57

    # Cell 5.13 has interval [5.125, 5.135)
    lat_edge, lon_edge = assign_grid_cell(5.125, 100.575, grid_size=0.01)
    assert lat_edge == 5.13
    assert lon_edge == 100.58

    # Cell 5.14 has interval [5.135, 5.145)
    lat_next, lon_next = assign_grid_cell(5.135, 100.585, grid_size=0.01)
    assert lat_next == 5.14
    assert lon_next == 100.59
