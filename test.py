import os
import lab
import pytest

TEST_DIRECTORY = os.path.realpath(os.path.dirname(__file__))


def test_index_conversion():
    with open(os.path.join(TEST_DIRECTORY, "test_data", "columns_in_order.txt")) as f:
        for c, line in enumerate(f):
            line = line.strip()
            for ix, r in enumerate((0, 99, 99999, 27, 10, 1)):
                assert lab.split_column_and_row(line + str(r)) == (line, r)
                assert lab.split_column_and_row(line + "0" * (ix + 1) + str(r)) == (
                    line,
                    r,
                )

    badnames = [
        "",
        "2",
        "A",
        " A2",
        "A99A",
        "9AA9",
        "z28",
        "🫠28",
        "AAA🫠",
        "Á28",
        "22A",
        "AAA",
    ]
    for badname in badnames:
        with pytest.raises(lab.BadCellName):
            lab.split_column_and_row(badname)


def test_cell_basics():
    s = lab.Spreadsheet()
    c = lab.Cell("A1", s)
    assert c.name == "A1"
    assert c.sheet is s
    assert c.formula == "0"
    assert c.value == 0

    c.set_formula("10")
    assert c.name == "A1"
    assert c.sheet is s
    assert c.formula == "10"
    assert c.value == 0

    assert c.update_value() == 10
    assert c.name == "A1"
    assert c.sheet is s
    assert c.formula == "10"
    assert c.value == 10
    assert c.update_and_propagate() == {"A1": 10}

    c.set_formula("range(7)")
    assert c.name == "A1"
    assert c.sheet is s
    assert c.formula == "range(7)"
    assert c.value == 10

    assert c.update_and_propagate() == {"A1": range(7)}
    assert c.name == "A1"
    assert c.sheet is s
    assert c.formula == "range(7)"
    assert c.value == range(7)


def test_spreadsheet_basics():
    s = lab.Spreadsheet()
    assert "A2" not in s
    assert s["A2"] is None
    s["A2"] = "10"
    assert "A2" in s
    assert set(s.cells) == {("A", 2)}
    assert s.cells[("A", 2)] is s["A2"]
    assert s["A2"].formula == "10"
    assert s["A2"].value == 10

    del s["A02"]
    assert "A2" not in s
    assert s["A2"] is None
    assert s.cells == {}


def test_basic_end_to_end():
    s = lab.Spreadsheet()
    assert s["A1"] is None
    s["A1"] = "42"
    assert s["A1"].value == 42
    s["A1"] = '"hello"'
    assert s["A1"].value == "hello"

    s["A2"] = "7"
    assert s["A2"] is s["A00002"]

    with pytest.raises(lab.BadCellName):
        assert s["['1', '2', '3']"].value == ["1", "2", "3"]

    s["A2"] = "['1', '2', '3']"
    assert s["A2"].value == ["1", "2", "3"]

    assert s.cells["A", 1] is s["A1"]
    assert s.cells["A", 2] is s["A2"]

    s = lab.Spreadsheet()
    assert "B2" not in s
    s["B2"] = "1"
    assert "B2" in s
    assert "B1" not in s
    assert "A2" not in s

    with pytest.raises(lab.IllegalOperation):
        del s["C3"]

    with pytest.raises(lab.IllegalOperation):
        del s["B1"]

    del s["B2"]
    assert "B2" not in s
    assert s["B2"] is None
    s["B2"] = "1"
    assert "B2" in s


def test_dependent_cells():
    # basic dependent updates
    s = lab.Spreadsheet()
    s["A1"] = "10"
    s["A2"] = "A1 * 2"
    assert s["A2"].value == 20
    s["A1"] = "20"
    assert s["A1"].value == 20
    assert s["A2"].value == 40
    s["A2"] = "A1 * 3"
    assert s["A1"].value == 20
    assert s["A2"].value == 60

    # basic dependent updates, types
    s = lab.Spreadsheet()
    s["A2"] = "A1 * 2"
    assert s["A2"].value == 0
    s["A1"] = "10"
    assert s["A2"].value == 20
    s["A1"] = "'cat'"
    assert s["A2"].value == "catcat"
    assert str(s["A2"]) == repr("catcat")

    # complicated types
    s["A1"] = "2"
    s["C8"] = "lambda x: x**2"
    s["D8"] = "C8(A2)"
    assert s["D8"].value == 16
    s["C8"] = "lambda x: x**3"
    assert s["D8"].value == 64
    s["A1"] = "3"
    assert s["D8"].value == 216

    s["F5"] = "[A1, C8, D8, A3]"
    s["F6"] = "F5[A1]"
    assert s["F6"].value == s["A3"].value

    s["A1"] = "0"
    assert s["F6"].value == s["A1"].value

    # chained updates
    s = lab.Spreadsheet()
    s["A3"] = "A2 + 1"
    s["A2"] = "A1 + 1"
    s["A1"] = "2"
    assert s["A3"].value == 4
    s["A1"] = "10"
    assert s["A3"].value == 12

    # multiple cells depending on the same cell should all update when it changes
    s = lab.Spreadsheet()
    s["A1"] = "3"
    s["B1"] = "A1 + 1"
    s["C1"] = "A1 * 2"
    s["A1"].set_formula("5")
    assert s["A1"].update_and_propagate() == {"A1": 5, "B1": 6, "C1": 10}
    assert s["B1"].value == 6
    assert s["C1"].value == 10

    # old dependencies should removed when updating formula
    s = lab.Spreadsheet()
    s["A1"] = "10"
    s["A2"] = "20"
    s["B1"] = "A1 + 1"
    assert s["B1"].value == 11
    assert set(s["A1"].update_and_propagate()) == {"A1", "B1"}
    s["B1"] = "A2 + 1"
    assert s["B1"].value == 21
    assert set(s["A1"].update_and_propagate()) == {"A1"}
    s["A1"] = "999"
    assert s["B1"].value == 21

    s = lab.Spreadsheet()
    s["A1"] = "10"
    s["A2"] = "20"
    s["B1"] = "A1 + 1"
    with pytest.raises(lab.IllegalOperation):
        del s["A1"]  # can't delete a cell someone depends on
    with pytest.raises(lab.IllegalOperation):
        del s["C1"]  # can't delete nonexistent cell
    del s["B1"]
    assert s["A1"].update_and_propagate() == {"A1": 10}
    del s["A1"]
    assert "A1" not in s

    s = lab.Spreadsheet()
    for i in range(1000):
        s[f"B{i}"] = f"A1 + {i}"
    assert s["A1"].value == 0
    s["D1"] = "[]"
    s["A1"] = "D1.append(1) or 4"  # this should only get evaluated once
    assert s["A1"].value == 4
    for i in range(1000):
        assert s[f"B00{i}"].value == 4 + i
    assert s["D1"].value == [1]


def test_dependent_rowcol():
    s = lab.Spreadsheet()
    s["ZZ27"] = "sum(Z_)"
    s["ZZ28"] = "len(Z_)"
    s["ZZ29"] = "Z_+ (-1,)"
    assert s["ZZ27"].value == 0
    assert s["ZZ28"].value == 0
    assert s["ZZ29"].value == (-1,)
    s["Z3"] = "42"
    assert s["ZZ27"].value == 42
    assert s["ZZ28"].value == 1
    assert s["ZZ29"].value == (42, -1)
    del s["Z3"]
    assert s["ZZ27"].value == 0
    assert s["ZZ28"].value == 0
    assert s["ZZ29"].value == (-1,)
    s["Z3"] = "42"
    s["Z99999"] = "1"
    assert s["ZZ27"].value == 43
    assert s["ZZ28"].value == 2
    assert s["ZZ29"].value == (42, 1, -1)

    s["A4"] = "67"
    s["A3"] = "42"
    s["A99999"] = "1"
    s["AA28"] = "sum(A_)"
    s["AA27"] = "len(A_)"
    s["AA29"] = "A_ + (-1,)"
    assert s["AA27"].value == 3
    assert s["AA28"].value == 110
    assert s["AA29"].value == (42, 67, 1, -1)

    s["A0"] = "sum(_4)"
    assert s["A0"].value == 67
    assert s["AA27"].value == 4
    assert s["AA28"].value == 177
    assert s["AA29"].value == (67, 42, 67, 1, -1)

    s["B4"] = "7"
    assert s["A0"].value == 74
    assert s["AA27"].value == 4
    assert s["AA28"].value == 184
    assert s["AA29"].value == (74, 42, 67, 1, -1)

    s["B0"] = "sum(_27)"
    assert s["B0"].value == 47

    s["Z20"] = "99"
    assert s["ZZ27"].value == 142
    assert s["B0"].value == 146

    del s["Z3"]
    assert s["ZZ27"].value == 100
    assert s["B0"].value == 104

    s["D32"] = "F_"
    s["F234"] = "99"
    s["E5"] = "F_ + _234 + _3"
    assert s["E5"].value == (99, 99, 42)
    s["F27"] = "20"
    assert s["E5"].value == (20, 99, 99, 42)

    s = lab.Spreadsheet()
    s["A1"] = "20"
    s["C1"] = "A_"
    assert s["C1"].value == (20,)
    del s["A1"]  # okay to delete if the only dependent is a _region_
    assert "A1" not in s
    assert s["C1"].value == ()


def test_cell_attributes():
    s = lab.Spreadsheet()

    s["A1"] = "7"
    a1 = s["A1"]
    assert a1.name == "A1"
    assert a1.sheet is s
    assert a1.value == 7
    assert a1.formula == "7"

    s["B1"] = "A1 + 1"
    b1 = s["B1"]
    assert b1.name == "B1"
    assert b1.sheet is s
    assert b1.value == 8
    assert b1.formula == "A1 + 1"
    assert b1 in a1.downstream

    s["C1"] = "A1 * 2"
    c1 = s["C1"]
    assert c1 in a1.downstream
    assert b1 in a1.downstream
    assert c1.value == 14
    assert c1.formula == "A1 * 2"

    c1.set_formula("99")
    assert c1.value == 14
    assert c1.formula == "99"
    assert c1 not in a1.downstream
    assert b1 in a1.downstream

    c1.set_formula("B1 - 1")
    assert c1.value == 14
    assert c1.formula == "B1 - 1"
    assert c1 in b1.downstream
    assert c1 not in a1.downstream
    assert b1 in a1.downstream

    s["A1"] = "10"
    assert a1.value == 10
    assert b1.value == 11
    assert c1.value == 10
    assert a1.formula == "10"
    assert b1.formula == "A1 + 1"
    assert c1.formula == "B1 - 1"

    s["A1"].set_formula("5")
    assert a1.formula == "5"
    assert a1.value == 10
    s["A1"].update_value()
    b1.update_value()
    assert a1.value == 5
    assert b1.value == 6
    assert c1.value == 10
    assert a1.formula == "5"
    assert b1.formula == "A1 + 1"
    assert c1.formula == "B1 - 1"

    c1.update_value()
    assert c1.value == 5

    a1.set_formula("100")
    result = a1.update_and_propagate()
    assert result["A1"] == 100
    assert result["B1"] == 101
    assert result["C1"] == 100
    assert a1.value == 100
    assert b1.value == 101
    assert c1.value == 100
    assert a1.formula == "100"
    assert b1.formula == "A1 + 1"
    assert c1.formula == "B1 - 1"

    region_types = {type(x).__name__ for x in a1.downstream}
    assert "Region" in region_types

    s["D1"] = "sum(A_)"
    s["A2"] = "50"
    assert s["D1"].value == 100 + 50


def test_spreadsheet_independence():
    s1 = lab.Spreadsheet()
    s2 = lab.Spreadsheet()

    s1["A1"] = "10"
    s1["A2"] = "A1 * 2"
    s1["A3"] = "A2 + A1"

    assert s2["A1"] is None
    assert s2["A2"] is None

    s2["A1"] = "99"
    s2["A2"] = "A1 + 1"

    assert s1["A1"].value == 10
    assert s1["A2"].value == 20
    assert s1["A3"].value == 30

    assert s2["A1"].value == 99
    assert s2["A2"].value == 100
    assert s2["A3"] is None

    s1["A1"] = "5"
    assert s1["A2"].value == 10
    assert s2["A1"].value == 99

    s2["A1"] = "0"
    assert s2["A2"].value == 1
    assert s1["A1"].value == 5

    assert s1["A1"].downstream.isdisjoint(s2["A1"].downstream)

    s1["B1"] = "7"
    s2["B1"] = "7"
    del s1["B1"]
    assert "B1" not in s1
    assert "B1" in s2

    s1["C1"] = "3"
    s2["C1"] = "300"
    assert s1["C1"].value != s2["C1"].value
    s1["D2"] = "sum(C_)"
    s2["D2"] = "sum(C_)"
    assert s1["D2"].value == 3
    assert s2["D2"].value == 300


def test_ordered_dependents_and_cycles():
    s = lab.Spreadsheet()
    s["A1"] = "1"
    s["A2"] = "A1 + 1"
    s["A3"] = "A2 + 1"

    order = s["A1"].ordered_dependents()
    names = [c.name for c in order if isinstance(c, lab.Cell)]
    assert names.index("A1") < names.index("A2") < names.index("A3")
    assert len(names) == len(set(names))

    s = lab.Spreadsheet()
    s["A1"] = "2"
    s["B1"] = "A1 + 0"
    s["C1"] = "A1 * 10"
    s["D1"] = "B1 + C1"

    order = s["A1"].ordered_dependents()
    names = [c.name for c in order if isinstance(c, lab.Cell)]
    assert names.index("A1") < names.index("B1")
    assert names.index("A1") < names.index("C1")
    assert names.index("B1") < names.index("D1")
    assert names.index("C1") < names.index("D1")
    assert len(names) == len(set(names))

    s = lab.Spreadsheet()
    s["Z9"] = "42"
    cell = s["Z9"]
    assert [i for i in cell.ordered_dependents() if isinstance(i, lab.Cell)] == [cell]

    s = lab.Spreadsheet()
    with pytest.raises(lab.CyclicalDefinition):
        s["A1"] = "A1"

    s = lab.Spreadsheet()
    s["X1"] = "1"
    s["X2"] = "X1 + 1"
    with pytest.raises(lab.CyclicalDefinition):
        s["X1"] = "X2"

    s = lab.Spreadsheet()
    for i in range(1, 101):
        s[f"A{i}"] = f"A{i-1} - 1"
    assert s["A100"].value == -100
    with pytest.raises(lab.CyclicalDefinition):
        s["A0"] = "A100 - 1"

    s = lab.Spreadsheet()
    s["C1"] = "3"
    s["C3"] = "9"
    with pytest.raises(lab.CyclicalDefinition):
        s["C2"] = "sum(C_)"
    s["C2"] = "C1 + C3"
    assert s["C2"].value == 12

    s = lab.Spreadsheet()
    for i in range(1, 11):
        s[f"B{i}"] = "A1 + 1"
    s["A1"] = "0"
    order = s["A1"].ordered_dependents()
    names = [c.name for c in order if isinstance(c, lab.Cell)]
    assert names[0] == "A1"
    assert sorted(names[1:]) == sorted(f"B{i}" for i in range(1, 11))

    s = lab.Spreadsheet()
    s["A1"] = "7"
    s["Z1"] = "sum(B_)"
    s["B2"] = "A1"
    s["B4"] = "B3"
    s["B3"] = "C1"
    assert s["Z1"].value == 7
    order = s["A1"].ordered_dependents()
    names = [c.name for c in order if isinstance(c, lab.Cell)]
    assert names.index("A1") < names.index("B2")
    assert names.index("Z1") == len(names) - 1
    order = s["C1"].ordered_dependents()
    names = [c.name for c in order if isinstance(c, lab.Cell)]
    assert names.index("C1") < names.index("B3")
    assert names.index("B3") < names.index("B4")
    assert names.index("Z1") == len(names) - 1


def test_big_dependencies_0():
    s = lab.Spreadsheet()
    s["ZAZZ1"] = "0"
    s["FUNC99"] = (
        "lambda n: __import__('functools').reduce(lambda x, _: x+[x[-1]+x[-2]], range(n-2), [0, 1])[-1]"
    )
    for i in range(50):
        s[f"QWERTY{i}"] = f"ZAZZ1 + {i}"
    s["CAT1"] = f"FUNC99(sum([{', '.join(f'QWERTY{i}' for i in range(2000))}]))"
    assert (
        s["CAT1"].value
        == 2827396159842418257182804699555048011544339558456848272703033314918994592020372102637633855208914570753115697690541891141357336605732655542610875041205458422049070983350202734034483405073248675325309262472317172257496401998781129096025801427515217762620768
    )
    s["ZAZZ1"] = "1"
    assert (
        s["CAT1"].value
        == 79573539503523266013360314290021310955098457667867493651195356428866087092371388766472475054184181597649943790945922708202411234829389507530685713475193974079898960050751443548470855732068635616067561689174061451521890621303834843963751260242328256247933621422454257
    )


def test_big_dependencies_1():
    s = lab.Spreadsheet()
    s["A1"] = "0"
    for i in range(2000):
        s[f"B{i}"] = f"A1 + {i}"
    s["C1"] = (
        f"__import__('time').sleep(1) or sum([{', '.join(f'B{i}' for i in range(2000))}])"
    )
    assert s["C1"].value == sum(range(2000))
    s["A1"] = "1"
    assert s["C1"].value == sum(range(2000)) + 2000


def test_big_dependencies_2():
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def index_to_letters(index):
        if index < 26:
            return letters[index]
        return index_to_letters(index // 26 - 1) + letters[index % 26]

    s = lab.Spreadsheet()
    s["A0"] = "0"
    current = [(0, 0)]
    for i in range(5):
        next_ = []
        curix = 0
        for c, r in current:
            col_label = index_to_letters(c)
            next_label = index_to_letters(c + 1)
            for i in range(3):
                s[f"{next_label}{curix}"] = f"{col_label}{r} + 1"
                next_.append((c + 1, curix))
                curix += 1
        current = next_
    assert s["F10"].value == 5
    s["A0"] = "10"
    assert s["F10"].value == 15
