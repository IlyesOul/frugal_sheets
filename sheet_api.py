#!/usr/bin/env python3
"""Spreadsheet HTTP/API handlers shared by server.py and the GitHub Pages UI."""

import importlib
import json
import sys
import traceback

try:
    import lab
except ImportError:
    import llllab as lab

    sys.modules["lab"] = lab


SPREADSHEET = lab.Spreadsheet()


def new(params):
    global SPREADSHEET, lab
    lab = importlib.reload(lab)
    print("[reloading lab.py in case you changed something]")
    SPREADSHEET = lab.Spreadsheet()
    return {"ok": True, "hasTopo": "ordered_dependents" in lab.Cell.__dict__}


def set_cell(params):
    loc = params["location"]
    value = params["formula"].strip()
    lab.get_sources(value)
    SPREADSHEET[loc] = value
    return {
        "ok": True,
        "values": {
            k: repr(v) for k, v in SPREADSHEET[loc].update_and_propagate().items()
        },
    }


def delete_cell(params):
    loc = params["location"]
    old = {k: v.value for k, v in SPREADSHEET.cells.items()}
    del SPREADSHEET[loc]
    return {
        "ok": True,
        "values": {
            f"{k[0]}{k[1]}": repr(v.value)
            for k, v in SPREADSHEET.cells.items()
            if v.value != old.get(k, None)
        },
    }


def generate_json(params):
    out = '["FRUGALSHEET",\n['
    ordered = all_ordered_dependents(SPREADSHEET)
    for ix, cell in enumerate(ordered):
        end = "," if ix != len(ordered) - 1 else ""
        out += f"\n    [{json.dumps(cell.name)}, {json.dumps(cell.formula)}]{end}"
    return {"ok": True, "result": out + "\n]]"}


def all_ordered_dependents(sheet):
    all_downstream = {c for cell in sheet.cells.values() for c in cell.downstream}

    out = []
    visited = set()
    for cell in sheet.cells.values():
        if cell in visited or cell in all_downstream:
            continue
        deps = [i for i in reversed(cell.ordered_dependents()) if i not in visited]
        out.extend(deps)
        visited.update(deps)
    return [
        i
        for i in out[::-1]
        if hasattr(i, "name") and i.name and "_" not in [i.name[-1], i.name[0]]
    ]


funcs = {
    "new": new,
    "set_cell": set_cell,
    "generate_json": generate_json,
    "delete_cell": delete_cell,
}


def dispatch(name, params):
    try:
        return funcs[name](params)
    except Exception:
        tb = traceback.format_exc()
        print(
            "--- Python error (likely in your lab code) during the next operation:\n"
            + tb,
            end="",
        )
        return {"error": tb}
