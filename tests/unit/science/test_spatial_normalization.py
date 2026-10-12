from science.harmonization.spatial_normalization import assign_grid_cell

def test_assign_grid_cell():
    """Verify grid cell assignment snaps coordinates to the configured grid size."""
    lat, lon = assign_grid_cell(5.1234, 100.5678, grid_size=0.01)
    assert round(lat, 2) == 5.12
    assert round(lon, 2) == 100.57
