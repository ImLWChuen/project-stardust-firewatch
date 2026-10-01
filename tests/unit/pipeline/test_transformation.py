from science.harmonization.activity_index import calculate_activity_index

def test_activity_index_calculation():
    val = calculate_activity_index(10, 50.0, weight_frp=0.5)
    assert val == 30.0
