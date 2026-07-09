from __future__ import annotations
import html
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from aurora_compiler.models.aurora import AuroraElement


def _inner_xml(node: ET.Element | None) -> str:
    if node is None:
        return ""
    chunks: list[str] = []
    if node.text and node.text.strip():
        chunks.append(html.escape(node.text))
    for child in list(node):
        if child.tag.lower() == "html":
            # Aurora sometimes stores escaped HTML inside <html> nodes.
            chunks.append(html.unescape(child.text or ""))
        else:
            chunks.append(ET.tostring(child, encoding="unicode"))
        if child.tail and child.tail.strip():
            chunks.append(html.escape(child.tail))
    return "".join(chunks).strip()


def _node_dict(node: ET.Element) -> dict:
    d = {
        "tag": node.tag,
        "attrs": dict(node.attrib),
        "text": (node.text or "").strip(),
        "children": [_node_dict(c) for c in list(node)],
    }
    if node.tag == "set":
        d["name"] = node.attrib.get("name", "")
        d["value"] = (node.text or node.attrib.get("value", "")).strip()
    return d


def parse_xml_bytes(data: bytes, file_name: str = "") -> list[AuroraElement]:
    text = data.decode("utf-8-sig", errors="replace")
    root = ET.fromstring(text)
    out: list[AuroraElement] = []
    for elem in root.findall(".//element"):
        desc = elem.find("description")
        rules_node = elem.find("rules")
        setters_node = elem.find("setters")
        supports: list[str] = []
        for s in elem.findall("supports"):
            if s.text and s.text.strip():
                # Aurora uses comma-separated supports in some files.
                supports.extend([p.strip() for p in s.text.split(",") if p.strip()])
        out.append(AuroraElement(
            id=elem.attrib.get("id", ""),
            name=elem.attrib.get("name", ""),
            type=elem.attrib.get("type", ""),
            source=elem.attrib.get("source", ""),
            description_html=_inner_xml(desc),
            rules=[_node_dict(c) for c in list(rules_node)] if rules_node is not None else [],
            setters=[_node_dict(c) for c in list(setters_node)] if setters_node is not None else [],
            supports=supports,
            file=file_name,
            attrs=dict(elem.attrib),
        ))
    return out


def parse_aurora_zip(zip_path: str | Path) -> list[AuroraElement]:
    result: list[AuroraElement] = []
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if not name.lower().endswith(".xml"):
                continue
            try:
                result.extend(parse_xml_bytes(z.read(name), name))
            except Exception as exc:
                print(f"[WARN] Failed parsing {name}: {exc}")
    return result
