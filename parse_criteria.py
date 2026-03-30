#!/usr/bin/env python3
"""
Parse Knowledge Bank HTML file to extract lending criteria data into structured JSON.

The HTML contains a single lender's (Accord) residential lending criteria from
knowledgebank.uk. Each criterion is a table row with:
- A criteria name (in a .criteriaRow div)
- A criteria ID and row number (data attributes)
- Search tags
- Optionally, expanded detail including:
  - A question/description
  - A grade/response (Yes, No, Yes with conditions, Please Refer, Yes by exception)
  - Notes/conditions text
- Optionally, a Consumer Duty flag
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path


def parse_html(html_content: str) -> dict:
    """Parse the Knowledge Bank HTML and return structured criteria data."""

    # Extract lender info from the heading
    lender_match = re.search(
        r'<h2>The Bank &gt; (.+?)&nbsp;&gt; <span class="color--primary">(.+?)</span></h2>',
        html_content,
    )
    lending_type = lender_match.group(1).strip() if lender_match else "Unknown"
    lender_name = lender_match.group(2).strip() if lender_match else "Unknown"

    # Extract all criteria rows
    # Each row is inside a <tr> containing a .criteriaRow div
    criteria = []

    # Pattern to find each criteria row block (from <tr> to </tr>)
    # We use the criteriaRow div as our anchor
    row_pattern = re.compile(
        r'<div\s+class="\s*criteriaRow"\s+'
        r'data-crit-id="(\d+)"\s+'
        r'data-row="(\d+)"\s+'
        r'[^>]*>\s*'
        r'(.*?)\s*'  # criteria name
        r'</div>\s*'
        r'<span\s+class="tags">(.*?)</span>\s*'  # tags
        r'<span\s+id="search-criteria-expanded-\d+"\s+class="criteriaExpanded"'
        r'(.*?)'  # either hidden="" or content
        r'(?=<div\s+class="\s*criteriaRow"|</tbody>)',
        re.DOTALL,
    )

    for match in row_pattern.finditer(html_content):
        crit_id = match.group(1)
        row_num = match.group(2)
        criteria_name = clean_text(match.group(3))
        tags = match.group(4).strip()
        expanded_block = match.group(5)

        entry = {
            "criteria_id": int(crit_id),
            "row": int(row_num),
            "name": criteria_name,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "consumer_duty_flag": False,
            "response": None,
            "question": None,
            "notes": None,
        }

        # Check for Consumer Duty flag in the surrounding area
        # We need to look in the parent <tr> which includes the second <td>
        # The flag image appears in the second td
        consumer_duty_check = expanded_block
        if "Consumer Duty Category" in consumer_duty_check or "flag_ConsumerDuty" in consumer_duty_check:
            entry["consumer_duty_flag"] = True

        # Check if expanded content is present (not hidden)
        if 'hidden=""' not in expanded_block[:20] and 'hidden=""' not in expanded_block[:50]:
            # Extract question text
            question_match = re.search(
                r'<div\s+class=""\s+style="[^"]*font-size:\s*1[23]px[^"]*">(.*?)</div>',
                expanded_block,
                re.DOTALL,
            )
            if question_match:
                entry["question"] = clean_text(question_match.group(1))

            # Extract grade/response
            grade_match = re.search(
                r'©_files/(\w+)\.png">&nbsp;&nbsp;(.*?)</div>',
                expanded_block,
            )
            if grade_match:
                grade_icon = grade_match.group(1)
                grade_text = clean_text(grade_match.group(2))
                entry["response"] = {
                    "grade": grade_icon,
                    "label": grade_text,
                }

            # Extract notes/conditions (the type--fine-print div after the grade)
            notes_match = re.search(
                r'<div\s+class="type--fine-print"\s+style="margin-left:\s*39px;">(.*?)</div>',
                expanded_block,
                re.DOTALL,
            )
            if notes_match:
                entry["notes"] = clean_text(notes_match.group(1))

        criteria.append(entry)

    # If the regex approach missed some, also try a simpler fallback
    # to catch the Consumer Duty flags that appear outside the expanded block
    # Let's also scan for Consumer Duty by row
    consumer_duty_rows = set()
    cd_pattern = re.compile(
        r'data-row="(\d+)".*?flag_ConsumerDuty',
        re.DOTALL,
    )
    # This is expensive on the full doc, so let's do it per-TR
    tr_pattern = re.compile(r'<tr>(.*?)</tr>', re.DOTALL)
    for tr_match in tr_pattern.finditer(html_content):
        tr_content = tr_match.group(1)
        row_match = re.search(r'data-row="(\d+)"', tr_content)
        if row_match and 'flag_ConsumerDuty' in tr_content:
            consumer_duty_rows.add(int(row_match.group(1)))

    # Update consumer duty flags
    for entry in criteria:
        if entry["row"] in consumer_duty_rows:
            entry["consumer_duty_flag"] = True

    result = {
        "source": "Knowledge Bank (knowledgebank.uk)",
        "lender": lender_name,
        "lending_type": lending_type,
        "total_criteria": len(criteria),
        "criteria_with_details": sum(1 for c in criteria if c["response"] is not None),
        "criteria_without_details": sum(1 for c in criteria if c["response"] is None),
        "response_summary": {},
        "criteria": criteria,
    }

    # Build response summary
    for c in criteria:
        if c["response"]:
            label = c["response"]["label"]
            result["response_summary"][label] = result["response_summary"].get(label, 0) + 1

    return result


def clean_text(text: str) -> str:
    """Clean HTML text by removing tags and normalizing whitespace."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main():
    html_path = Path("/home/user/mortgage-eligibility/Knowledge Bank ©.html")
    output_path = Path("/home/user/mortgage-eligibility/lending_criteria.json")

    print(f"Reading HTML file: {html_path}")
    html_content = html_path.read_text(encoding="utf-8")
    print(f"File size: {len(html_content):,} characters")

    print("Parsing criteria...")
    result = parse_html(html_content)

    print(f"Extracted {result['total_criteria']} criteria entries")
    print(f"  - With detailed responses: {result['criteria_with_details']}")
    print(f"  - Without details (lazy-loaded): {result['criteria_without_details']}")
    print(f"  - Response summary: {result['response_summary']}")

    print(f"\nWriting JSON to: {output_path}")
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("Done!")


if __name__ == "__main__":
    main()
