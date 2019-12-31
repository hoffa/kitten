import kitten


def test_chunks():
    assert list(kitten.chunks([1, 2, 3, 4, 5, 6, 7, 8], 3)) == [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8],
    ]
