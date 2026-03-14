"""Utilities for converting pasted HTML tables into Jinja2-like templates."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


NUMBER_PATTERN = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^-?\d+(?:\.\d+)?$")
PERCENT_PATTERN = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?%$|^-?\d+(?:\.\d+)?%$")
PERIOD_PATTERN = re.compile(r"^(?:\d{1,2}(?:\.\d+)?Q|\d{2}\.W\d{1,2}|\d{4}\.\dQ)$", re.IGNORECASE)
HEADER_KEYWORDS = {"DRAM", "FLASH", "TOTAL", "합계", "요약", "SUMMARY", "제목"}


@dataclass
class CellMeta:
    table_index: int
    tag: str
    row_index: int
    col_index: int
    a1_addr: str
    rowspan: int
    colspan: int
    original_text: str
    inner_html: str
    styles: str
    attrs: dict[str, Any]


def col_idx_to_letters(index: int) -> str:
    result = ""
    current = index + 1
    while current:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def parse_html_tables(html_text: str) -> tuple[ET.Element, list[ET.Element]]:
    """Parse HTML as XML and return root + all tables."""
    root = ET.fromstring(html_text)
    tables = [elem for elem in root.iter() if elem.tag.lower() == "table"]
    return root, tables


def _child_elements_by_tag(parent: ET.Element, tags: set[str]) -> list[ET.Element]:
    return [c for c in list(parent) if isinstance(c.tag, str) and c.tag.lower() in tags]


def _element_text(elem: ET.Element) -> str:
    return " ".join("".join(elem.itertext()).split())


def build_virtual_grid(table: ET.Element, table_index: int) -> list[CellMeta]:
    occupied: dict[int, set[int]] = {}
    row_index = 0
    metas: list[CellMeta] = []

    for tr in [e for e in table.iter() if isinstance(e.tag, str) and e.tag.lower() == "tr"]:
        occupied.setdefault(row_index, set())
        col_index = 0

        for cell in _child_elements_by_tag(tr, {"td", "th"}):
            while col_index in occupied[row_index]:
                col_index += 1

            rowspan = int(cell.attrib.get("rowspan", "1") or "1")
            colspan = int(cell.attrib.get("colspan", "1") or "1")
            a1_addr = f"{col_idx_to_letters(col_index)}{row_index + 1}"

            for r in range(rowspan):
                occupied.setdefault(row_index + r, set())
                for c in range(colspan):
                    occupied[row_index + r].add(col_index + c)

            attrs = dict(cell.attrib)
            inner_html = "".join(ET.tostring(c, encoding="unicode") for c in list(cell))
            if cell.text:
                inner_html = cell.text + inner_html

            metas.append(
                CellMeta(
                    table_index=table_index,
                    tag=cell.tag.lower(),
                    row_index=row_index,
                    col_index=col_index,
                    a1_addr=a1_addr,
                    rowspan=rowspan,
                    colspan=colspan,
                    original_text=_element_text(cell),
                    inner_html=inner_html,
                    styles=attrs.get("style", ""),
                    attrs=attrs,
                )
            )
            col_index += colspan

        row_index += 1

    return metas


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_value_type(text: str) -> str:
    normalized = normalize_text(text)
    if PERCENT_PATTERN.match(normalized):
        return "percent"
    if NUMBER_PATTERN.match(normalized):
        return "number"
    if PERIOD_PATTERN.match(normalized):
        return "period"
    return "text"


def is_candidate_cell(cell_meta: CellMeta) -> bool:
    value = normalize_text(cell_meta.original_text)
    if not value or cell_meta.tag == "th" or value.upper() in HEADER_KEYWORDS:
        return False
    if detect_value_type(value) in {"number", "percent", "period"}:
        return True
    if cell_meta.row_index >= 2 and cell_meta.col_index >= 2 and len(value) <= 30:
        return True
    return False


def detect_candidate_cells(cell_metas: list[CellMeta]) -> list[dict[str, Any]]:
    rows = []
    for cell in cell_metas:
        normalized = normalize_text(cell.original_text)
        is_candidate = is_candidate_cell(cell)
        rows.append(
            {
                **asdict(cell),
                "normalized_text": normalized,
                "detected_type": detect_value_type(normalized),
                "is_candidate": is_candidate,
                "placeholder": f"cell_{cell.a1_addr}" if is_candidate else None,
            }
        )
    return rows


def _replace_cell_text(cell: ET.Element, placeholder: str) -> None:
    replacement = f"{{{{ {placeholder} }}}}"
    # Prefer p/span descendants, otherwise replace first text-bearing location in cell.
    target_candidates = [d for d in cell.iter() if isinstance(d.tag, str) and d.tag.lower() in {"p", "span"}]
    target_candidates.append(cell)

    for target in target_candidates:
        if target.text and target.text.strip():
            target.text = replacement
            for child in list(target):
                child.tail = ""
            return

    # Fallback when only tail texts exist.
    cell.text = replacement


def _find_cell_by_position(table: ET.Element, target_row: int, target_col: int) -> ET.Element | None:
    occupied: dict[int, set[int]] = {}
    row_idx = 0
    for tr in [e for e in table.iter() if isinstance(e.tag, str) and e.tag.lower() == "tr"]:
        occupied.setdefault(row_idx, set())
        col_idx = 0
        for cell in _child_elements_by_tag(tr, {"td", "th"}):
            while col_idx in occupied[row_idx]:
                col_idx += 1

            rowspan = int(cell.attrib.get("rowspan", "1") or "1")
            colspan = int(cell.attrib.get("colspan", "1") or "1")

            if row_idx == target_row and col_idx == target_col:
                return cell

            for r in range(rowspan):
                occupied.setdefault(row_idx + r, set())
                for c in range(colspan):
                    occupied[row_idx + r].add(col_idx + c)
            col_idx += colspan
        row_idx += 1
    return None


def generate_template(root: ET.Element, contract_rows: list[dict[str, Any]]) -> str:
    tables = [e for e in root.iter() if isinstance(e.tag, str) and e.tag.lower() == "table"]
    for row in contract_rows:
        if not row["is_candidate"]:
            continue
        if row["table_index"] >= len(tables):
            continue
        cell = _find_cell_by_position(tables[row["table_index"]], row["row_index"], row["col_index"])
        if cell is not None:
            _replace_cell_text(cell, row["placeholder"])

    return ET.tostring(root, encoding="unicode", method="html")


def generate_data_contract(contract_rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates, all_cells = [], []
    for row in contract_rows:
        item = {
            "table_index": row["table_index"],
            "placeholder": row["placeholder"],
            "a1_addr": row["a1_addr"],
            "original_text": row["original_text"],
            "normalized_text": row["normalized_text"],
            "detected_type": row["detected_type"],
            "is_candidate": row["is_candidate"],
            "rowspan": row["rowspan"],
            "colspan": row["colspan"],
            "tag": row["tag"],
        }
        all_cells.append(item)
        if row["is_candidate"]:
            candidates.append(item)
    return {
        "version": "stage1",
        "description": "HTML table cells mapped to Jinja placeholders",
        "candidate_cells": candidates,
        "all_cells": all_cells,
    }


def generate_mock_data(data_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        cell["placeholder"]: cell["normalized_text"]
        for cell in data_contract["candidate_cells"]
        if cell["placeholder"]
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
