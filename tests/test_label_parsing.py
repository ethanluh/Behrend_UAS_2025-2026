import pytest

import od_lib


def test_valid_line():
    cls, cx, cy, w, h = od_lib.parse_label_line("0 0.5 0.5 0.1 0.2")
    assert cls == 0
    assert (cx, cy, w, h) == pytest.approx((0.5, 0.5, 0.1, 0.2))


def test_tent_class():
    cls, *_ = od_lib.parse_label_line("1 0.25 0.25 0.5 0.5")
    assert cls == 1


@pytest.mark.parametrize("line", [
    "0 0.5 0.5 0.1",          # too few fields
    "0 0.5 0.5 0.1 0.2 0.3",  # too many fields
    "x 0.5 0.5 0.1 0.2",      # non-integer class
    "0 1.5 0.5 0.1 0.2",      # cx out of range
    "0 0.5 -0.1 0.1 0.2",     # cy out of range
])
def test_malformed_line_raises(line):
    with pytest.raises(ValueError):
        od_lib.parse_label_line(line)


def test_parse_file_multiline(tmp_path):
    p = tmp_path / "labels.txt"
    p.write_text("0 0.5 0.5 0.1 0.2\n\n1 0.3 0.3 0.2 0.2\n")
    boxes = od_lib.parse_label_file(str(p))
    assert len(boxes) == 2
    assert boxes[0][0] == 0
    assert boxes[1][0] == 1


def test_label_path_for_image():
    assert od_lib.label_path_for_image("mannequin_00001.png", "/lbls") \
        == "/lbls/mannequin_00001.txt"
