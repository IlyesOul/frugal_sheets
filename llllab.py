#!/usr/bin/env python3
"""
6.101 Lab:
Frugal Sheets
"""

# import enum  # optional import
# import pprint  # optional import
# import typing  # optional import

import re
# import doctest

# NO ADDITIONAL IMPORTS ALLOWED!


######################################
# CUSTOM EXCEPTIONS FOR SPREADSHEETS #
######################################


class BadFormula(Exception):
    """
    Exception for bad cell formula
    """
    pass


class BadCellName(Exception):
    """
    Exception for bad cell name
    """
    pass

class IllegalOperation(Exception):
    """
    Exception for illegal operation
    """
    pass


class CyclicalDefinition(Exception):
    """
    Exception for cyclical defintion
    """
    pass


###################################
# STAFF-PROVIDED HELPER FUNCTIONS #
###################################

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _letters_to_index(letter):
    letter = letter.upper()
    return (
        sum(
            (LETTERS.index(char) + 1) * len(LETTERS) ** power
            for power, char in enumerate(reversed(letter))
        )
        - 1
    )


def cell_name_sorter(name):
    """
    Usable as a key function to `sort`, `min`, `max`, etc.  Takes as input
    a cell name (or a tuple of (column_name, row_num)) and returns a value
    that can be used as a key to sort elements within a region.
    """
    if isinstance(name, str):
        colname, rownum = split_column_and_row(name)
    else:
        colname, rownum = name
    return _letters_to_index(colname), rownum


def get_sources(formula_str):
    """
    Given a string containing a Python expression, return a set of all
    cell or region names contained therein.
    """
    try:
        formula_code = compile(formula_str, "<spreadsheet>", "eval")
    except Exception as e:
        raise BadFormula(f"invalid formula: {formula_str!r}") from e
    return {
        name
        for name in formula_code.co_names
        if re.match("[A-Z]+[0-9]+", name)
        or re.match("[A-Z]+_|_[0-9]+|[A-Z]+[0-9]+_[A-z]+[0-9]+", name)
    }


###################################
# CORE SPREADSHEET IMPLEMENTATION #
###################################


def split_column_and_row(name):
    """
    Given a cell name (a string containing one or more upper-case letters
    followed by one or more digits), return a `tuple` (column_name, row_num)
    where column_name contains the letters and row_num is an `int` representing
    the given number.

    If the given name is not valid, raise a `BadCellName` exception instead.
    """

    if not isinstance(name, str) or not name.isascii() \
    or len(name) == 0 or " " in name: # string isn't passed/invalid chars
        raise BadCellName

    # Don't modify passed name
    new_name = ""
    for char in name:
        new_name += char

    # Find first digit
    digits, num_index = "", -1
    for i, item in enumerate(new_name):
        if str(item).isdigit():
            num_index = i
            break

    # Find first letter
    let_index = -1
    for i, item in enumerate(new_name):
        if not str(item).isdigit():
            let_index = i
            break

    if num_index == -1 or let_index == -1 or \
    num_index <= let_index : # no digits found or before letter
        raise BadCellName

    digits = new_name[num_index:]
    digits = digits if digits.isdigit() else None

    words = new_name[:num_index]

    if not words.isalpha() or not digits or not words.isupper():
        raise BadCellName

    return (words, int(digits))



class Cell:
    """
    Cell class
    """
    def __init__(self, name, sheet):
        """
        Initializes cell
        """
        self.name = name
        self.sheet = sheet
        self.value = 0
        self.formula = "0"
        self.downstream = set()
        self.sources=[]

    def set_formula(self, formula):
        """
        Update the cell's formula to the given string formula
        """

        # Removing from cells/regions we depend on's downstreams
        dependent_cell_region_names = get_sources(self.formula)
        for dependent_cell_region_name in dependent_cell_region_names:
            self.sheet[dependent_cell_region_name].downstream.discard(self)

        self.formula = formula

        # Adding to dependent cells downstreams and updating them
        dependent_cell_region_names = get_sources(self.formula)
        for dependent_cell_region_name in dependent_cell_region_names:
            if dependent_cell_region_name not in self.sheet: # add new to sheet
                if "_" not in dependent_cell_region_name: # cell
                    self.sheet[dependent_cell_region_name] = '0'
                else: # region
                    self.sheet.regions[dependent_cell_region_name] = \
                    Region(dependent_cell_region_name, (), self.sheet)

            self.sheet[dependent_cell_region_name].downstream.add(self)

        self.sources = dependent_cell_region_names


    def update_value(self):
        """
        Update this cell's `value` attribute by evaluating its `formula`.
        Return the updated value.
        """

        # Self value
        var_values = {self.name:self.value}

         # Obtain values for variables in function
        variable_names = self.sources
        for var_name in variable_names:
            var_values[var_name] = self.sheet[var_name].value

        self.value = eval(self.formula, var_values)

        return self.value

    def update_and_propagate(self):
        """
        Update this cell's , as well as those whose values depend on it,
        `value` attributes.  Return a dictionary mapping this
        cell's, as well as those in its downstreams/topological ordering,
        names to their updated values
        """

        topo_order = self.ordered_dependents()

        new_vals = {} # updated values dict

        # Update downstream values in topological order
        for depending_var in topo_order:
            new_change = depending_var.update_value()
            if "_" not in depending_var.name:
                new_vals[depending_var.name] = new_change

        return new_vals

    def ordered_dependents(self):
        """
        Helper fuction that returns topological ordering of dependency graph
        """

        # Build topolist, visited set, and current path
        return_list = []
        visited = set()
        cp = set()

        def toposort_helper(cell: Cell):

            if cell in cp: # cycle
                raise CyclicalDefinition

            if cell in visited: # validity of cell
                return

            cp.add(cell)

            # iterate through non-finished nodes
            for child in cell.downstream:
                toposort_helper(child)

            # Update sets and lists
            visited.add(cell)
            return_list.append(cell)
            cp.remove(cell)

        toposort_helper(self) # recursive helper call

        return return_list[::-1]

    def __str__(self):
        return repr(self.value)


class Spreadsheet:
    """
    Spreadsheet class
    """
    def __init__(self):
        """
        Initializes spreadsheet instance
        """
        self.cells = {}
        self.regions = {}

    def __getitem__(self, name):
        """
        Return the `Cell` (or Region) instance associated with the given name if the given
        name maps to a cell in the spreadhseet, or "0" if it doesn't.

        If the given name is not valid, raise a `BadCellName` exception instead.
        """

        if "_" not in name: # cell
            if name not in self: # cell not in cells -> create new one
                return None
            return self.cells[split_column_and_row(name)]
        # region
        if name not in self: # region
            self.regions[name] = Region(name, (), self) # create new region
        return self.regions[name]

    def __setitem__(self, name, formula):
        """
        Update the formula of the cell at the given location to be the string
        represented by the formula.  Then update its value, as well as those
        of the cells that depend on it, appropriately.

        If the cell doesn't exist in the sheet, add it before adjusting its
        formula.

        If the given name is not valid, raise a `BadCellName` exception instead.
        """

        if "_" not in self:
            # Update this cell's value
            if name not in self: # cell doesn't exist yet -> add it
                new_cell = Cell(name, self)
                self.cells[split_column_and_row(name)] = new_cell

                # Add cell to appropriate regions
                col, row = split_column_and_row(name)
                col_name, row_name = col+ "_", "_" + str(row)

                for r_name in [col_name, row_name]:
                    if r_name not in self.regions:
                        self.regions[r_name] = Region(r_name, (), self) # create new

                # Now add the cell to the regions
                col_region = self.regions[col_name]
                row_region = self.regions[row_name]

                # Adding to regions
                col_region.add_cell(new_cell)
                row_region.add_cell(new_cell)

                # Add to downstreams
                new_cell.downstream.add(col_region)
                new_cell.downstream.add(row_region)

        # Set formula and propogate
        if "_" not in name:
            target_cell = self.cells[split_column_and_row(name)]
            target_cell.set_formula(formula)
            return target_cell.update_and_propagate()

    def __contains__(self, name):
        """
        Return a Boolean indicating whether `name` maps to a cell in the
        spreadsheet

        If the given name is not valid, raise a `BadCellName` exception instead.
        """
        return split_column_and_row(name) in self.cells.keys() \
    if "_" not in name else name in self.regions.keys()

    def __delitem__(self, name):
        """
        Delete the given cell from the spreadsheet completely.

        If the given name is not valid, raise a `BadCellName` exception
        instead. If a cell with the given name doesn't exist, or other
        cells depend on this one, raise an 'IllegalOperation' exception
        """
        if name not in self: # cell doesn't exist
            raise IllegalOperation("Cell not in sheet")
        if any(isinstance(downstream_member, Cell) for downstream_member in self[name\
                                ].downstream): # other cells dependent on this one
            raise IllegalOperation("Other cells dependent on this one")
        # remove from upstream cells/regions
        for upstream_cell_name in get_sources(self[name].formula):
            upstream_cell = self[upstream_cell_name]
            upstream_cell.downstream.discard(self[name])

        # Remove from region
        col, row = split_column_and_row(name)
        col, row = col+ "_", "_" + str(row)
        col_region = self[col]
        row_region = self[row]

        # Update regions
        col_region.remove_cell(self.cells[split_column_and_row(name)])
        row_region.remove_cell(self.cells[split_column_and_row(name)])

        self.cells.pop(split_column_and_row(name)) # delete cell

        # Update regions
        col_region.update_and_propagate()
        row_region.update_and_propagate()


class Region():
    """
    Region class
    """
    def __init__(self, name, cells, sheet):
        """
        Initializes region instance
        """
        self.name = name
        self.cells = cells
        self.value = ()
        self.sheet = sheet
        self.downstream = set()

    def update_value(self):
        """
        Function that updates the region's value based on its member cells
        """

        # Sort value
        ordered_cells = sorted(self.cells, key=lambda c: cell_name_sorter(c.name))

        # Extract the values in that order
        self.value = tuple(c.value for c in ordered_cells)
        return self.value

    def add_cell(self, cell: Cell):
        """
        Function that adds a given cell to the region
        """

        if cell not in self.cells:
            # Update cells
            self.cells += (cell, )
        cell.downstream.add(self)

    def remove_cell(self, cell: Cell):
        """
        Function that removes a given cell to the region
        """

        if cell in self.cells:
            # Update tuple
            self.cells = tuple(tup_cell for tup_cell in self.cells if tup_cell != cell)
            # Update stream/value
        cell.downstream.discard(self)


    def update_and_propagate(self):
        """
        Update this region's , as well as those whose values depend on it,
        `value` attributes.  Return a dictionary mapping this
        region's, as well as those in its downstreams,
        names to their updated values
        """

        # Toposort list
        ts_order = self.ordered_dependents()

        new_vals = {} # updated values dict

        if ts_order:
            # Update downstream values
            for depending_var in ts_order:
                value = depending_var.update_value()
                if isinstance(depending_var, Cell):
                    new_vals[depending_var.name] = value

        return new_vals

    def ordered_dependents(self):
        """
        Helper fuction that returns topological ordering of dependency graph
        """

        # Build topolist, visited set, and current path
        return_list = []
        visited = set()
        cp = set()

        def toposort_helper(region_cell):
            if region_cell in cp: # cycle
                raise CyclicalDefinition

            if region_cell in visited: # validity of cell
                return

            cp.add(region_cell)

            # iterate through non-finished nodes
            for child in region_cell.downstream:
                toposort_helper(child)

            # Update sets and lists
            visited.add(region_cell)
            return_list.append(region_cell)
            cp.remove(region_cell)

        toposort_helper(self) # recursive helper call

        return return_list[::-1]
