class BadCellName(Exception):
    pass


def split_column_and_row(name):
    """
    Given a cell name (a string containing one or more upper-case letters
    followed by one or more digits), return a `tuple` (column_name, row_num)
    where column_name contains the letters and row_num is an `int` representing
    the given number.

    If the given name is not valid, raise a `BadCellName` exception instead.
    """

    #print(f"passed name: {name}")

    if type(name) != str or not name.isascii() or len(name) == 0 or " " in name: # string isn't passed/invalid chars
        raise BadCellName

    # Don't modify passed name
    new_name = ""
    for char in name:
        new_name += char
    
    # Find first digit
    digits, num_index = "", -1
    for i in range(len(new_name)):
        if str(new_name[i]).isdigit():
            num_index = i
            break
    
    # Find first letter
    let_index = -1
    for i in range(len(new_name)):
        if not str(new_name[i]).isdigit():
            let_index = i
            break

    if num_index == -1 or let_index == -1 or num_index <= let_index : # no digits found or before letter
        raise BadCellName
    
    digits = new_name[num_index:] 
    digits = digits if digits.isdigit() else None

    words = new_name[:num_index]

    if not words.isalpha() or not digits or not words.isupper(): # not alphabetical characters in first part or not uppercase
        raise BadCellName

    return (words, int(digits))

cells = (1, 2, float)

print(any(isinstance(downstream_member, int) for downstream_member in cells))