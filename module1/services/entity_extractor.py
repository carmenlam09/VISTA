import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)
ENTITY_KEYS = ("vendor_name", "registration_number", "country", "address", "directors", "shareholders", "ubo", "related_parties")
PROMPT_TEMPLATE = """Extract vendor due diligence entities from the text below. Return JSON only with these keys: vendor_name, registration_number, country, address, directors, shareholders, ubo, related_parties.

The source may be a Malaysian SSM company report. Interpret these labels: Nama is the current company name, No. Pendaftaran is the registration number, Tempat Penubuhan is country, Alamat Daftar is the registered address, MAKLUMAT PENGARAH DAN PEGAWAI contains officers, and MAKLUMAT PEMEGANG SYER contains shareholders. Include only people whose Jawatan is DIRECTOR; do not include SECRETARY as a director. Keep multiline addresses together. Use objects with director_name and nationality for directors, shareholder_name and ownership_percentage for shareholders, ubo_name and ownership_percentage for UBOs, and related_party_name and relationship_type for related parties. Do not infer an ownership percentage when the report only gives share counts.

TEXT:
{text}"""


def _empty() -> dict[str, Any]:
    return {"vendor_name": "", "registration_number": "", "country": "", "address": "", "directors": [], "shareholders": [], "ubo": [], "related_parties": []}


def _items(value: str, name_key: str, percentage_key: str | None = None) -> list[dict[str, Any]]:
    result = []
    for raw in re.split(r"[;\n]+", value):
        raw = raw.strip(" .:-")
        if not raw:
            continue
        percentage = None
        if percentage_key:
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", raw)
            if match:
                percentage = float(match.group(1))
                raw = re.sub(r"\s*\(?\d+(?:\.\d+)?\s*%\)?", "", raw).strip(" -")
        result.append({name_key: raw, **({percentage_key: percentage} if percentage_key else {})})
    return result


def _lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean or re.search(r"^(?:User ID:|Tarikh Cetakan:|Maklumat ini dijana|MENARA SSM@|TEL:|FAX:|\d+/6$)", clean, re.I):
            continue
        lines.append(clean)
    return lines


def _section(lines: list[str], start: str, end_markers: tuple[str, ...]) -> list[str]:
    start_index = next((index for index, line in enumerate(lines) if re.search(start, line, re.I)), None)
    if start_index is None:
        return []
    end_index = len(lines)
    for index in range(start_index + 1, len(lines)):
        if any(re.search(marker, lines[index], re.I) for marker in end_markers):
            end_index = index
            break
    return lines[start_index + 1:end_index]


def _label_value(lines: list[str], label: str) -> str:
    match = next((match for line in lines if (match := re.match(rf"^{label}\s*:\s*(.+)$", line, re.I))), None)
    return match.group(1).strip() if match else ""


def _ssm_extract(text: str) -> dict[str, Any]:
    result = _empty()
    lines = _lines(text)
    company = _section(lines, r"^MAKLUMAT SYARIKAT$", (r"^MAKLUMAT MODAL$", r"^MAKLUMAT PENGARAH"))
    result["vendor_name"] = _label_value(company, r"Nama")
    result["registration_number"] = _label_value(company, r"No\. Pendaftaran")
    result["country"] = _label_value(company, r"Tempat Penubuhan")

    address_start = next((index for index, line in enumerate(company) if re.match(r"^Alamat Daftar\s*:", line, re.I)), None)
    if address_start is not None:
        address_lines = [re.sub(r"^Alamat Daftar\s*:\s*", "", company[address_start], flags=re.I).strip()]
        for line in company[address_start + 1:]:
            if re.match(r"^Poskod\s*:", line, re.I):
                address_lines.append(line)
                break
            if re.match(r"^(?:Nama|No\. Pendaftaran|Tarikh|Jenis|Status|Tempat Penubuhan|Alamat Perniagaan)\s*:", line, re.I):
                break
            address_lines.append(line)
        result["address"] = "\n".join(line for line in address_lines if line)

    officer_lines = _section(lines, r"^MAKLUMAT PENGARAH DAN PEGAWAI$", (r"^MAKLUMAT PEMEGANG SYER$", r"^MAKLUMAT GADAIAN$"))
    for index, line in enumerate(officer_lines):
        if not re.search(r"\bDIRECTOR\b", line, re.I):
            continue
        inline_name = re.search(r"(?P<name>[A-Z][A-Z .'-]+?)\s+\d{6}-\d{2}-\d{4}\s+DIRECTOR\b", line, re.I)
        if inline_name:
            result["directors"].append({"director_name": inline_name.group("name").strip(), "nationality": ""})
            continue
        preceding = officer_lines[:index]
        name = next((candidate for candidate in reversed(preceding) if re.match(r"^[A-Z][A-Z .'-]+$", candidate) and not re.search(r"^(?:SAMPLE|SSM|SURUHANJAYA|COMPANIES|MAKLUMAT)\b", candidate, re.I)), "")
        if name:
            result["directors"].append({"director_name": name, "nationality": ""})

    shareholder_lines = _section(lines, r"^MAKLUMAT PEMEGANG SYER$", (r"^MAKLUMAT GADAIAN$", r"^RINGKASAN PENYATA KEWANGAN$"))
    for index, line in enumerate(shareholder_lines):
        row_match = re.match(r"^(?P<name>.+?)\s+(?P<shares>[\d,]+(?:\.\d+)?)$", line)
        if not row_match or not re.search(r"\.\d{2}$", row_match.group("shares")):
            continue
        name = re.sub(r"^\d{6,}\s*\([^)]*\)\s*", "", row_match.group("name").strip())
        if not re.search(r"\b(?:SDN\.?\s*BHD\.?|BERHAD)\b", name, re.I):
            name_candidates = shareholder_lines[:index]
            name = next((candidate for candidate in reversed(name_candidates) if re.search(r"\b(?:SDN\.?\s*BHD\.?|BERHAD)\b", candidate, re.I)), "")
        if name:
            shares = row_match.group("shares").replace(",", "")
            result["shareholders"].append({"shareholder_name": name, "ownership_percentage": None, "shares": float(shares)})
    return result


def mock_extract(text: str) -> dict[str, Any]:
    if re.search(r"MAKLUMAT SYARIKAT|NO\. PENDAFTARAN|MAKLUMAT PENGARAH", text, re.I):
        return _ssm_extract(text)
    result = _empty()
    patterns = {
        "vendor_name": r"(?:vendor\s*name|company\s*name)\s*:\s*(.+)",
        "registration_number": r"registration\s*(?:number|no\.)\s*:\s*(.+)",
        "country": r"country\s*:\s*(.+)",
        "address": r"address\s*:\s*(.+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            result[key] = match.group(1).strip()
    for label, key, name_key, pct_key in [
        ("directors", "directors", "director_name", None),
        ("shareholders", "shareholders", "shareholder_name", "ownership_percentage"),
        ("ubo", "ubo", "ubo_name", "ownership_percentage"),
        ("related parties", "related_parties", "related_party_name", None),
    ]:
        match = re.search(rf"{label}\s*:\s*(.+)", text, re.I)
        if match:
            result[key] = _items(match.group(1), name_key, pct_key)
            if key == "directors":
                for item in result[key]:
                    item["nationality"] = ""
            if key == "related_parties":
                for item in result[key]:
                    item["relationship_type"] = ""
    return result


def extract_entities(text: str) -> dict[str, Any]:
    """Use Gemini when configured; otherwise use deterministic local extraction."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return mock_extract(text)
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(PROMPT_TEMPLATE.format(text=text))
        raw = response.text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return {key: parsed.get(key, _empty()[key]) for key in ENTITY_KEYS}
    except Exception:
        logger.exception("Gemini extraction failed; using mock extractor")
        return mock_extract(text)
