#!/usr/bin/env python3
"""
Parse Knowledge Bank HTML file to extract lending criteria data into structured JSON.
"""

import json
import re
from pathlib import Path


def clean_html(text: str) -> str:
    """Remove HTML tags, decode entities, and clean whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&rsquo;', '\u2019')
    text = text.replace('&lsquo;', '\u2018')
    text = text.replace('&rdquo;', '\u201d')
    text = text.replace('&ldquo;', '\u201c')
    text = text.replace('&ndash;', '\u2013')
    text = text.replace('&mdash;', '\u2014')
    text = text.replace('&pound;', '\u00a3')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_criteria(html_content: str) -> dict:
    """Parse the Knowledge Bank HTML and return structured criteria data."""

    # Extract lender and lending type from heading
    lender_match = re.search(
        r'<h2>The Bank\s*(?:&gt;|>)\s*([\w\s]+?)(?:&nbsp;)?\s*(?:&gt;|>)\s*<span[^>]*>([^<]+)</span></h2>',
        html_content
    )
    lender_name = lender_match.group(2).strip() if lender_match and lender_match.group(2) else ""
    lending_type = lender_match.group(1).strip() if lender_match else ""

    # Find all criteriaRow divs with their positions
    crit_pattern = re.compile(
        r'<div[^>]*class="[^"]*criteriaRow[^"]*"[^>]*data-crit-id="(\d+)"[^>]*data-row="(\d+)"[^>]*>\s*(.*?)\s*</div>',
        re.DOTALL
    )
    crit_matches = list(crit_pattern.finditer(html_content))
    print(f"Found {len(crit_matches)} criteriaRow divs")

    criteria_list = []

    for i, m in enumerate(crit_matches):
        crit_id = m.group(1)
        row_num = m.group(2)
        criteria_name = clean_html(m.group(3))

        # Define the text block for this criteria: from current match to next match (or +5000 chars)
        start = m.end()
        if i + 1 < len(crit_matches):
            end = crit_matches[i + 1].start()
        else:
            end = min(start + 5000, len(html_content))
        block = html_content[start:end]

        # Extract tags
        tags = []
        tags_match = re.search(r'<span class="tags">(.*?)</span>', block, re.DOTALL)
        if tags_match:
            raw_tags = tags_match.group(1).strip()
            tags = [t.strip() for t in raw_tags.split(',') if t.strip()]

        # Consumer Duty flag
        consumer_duty = 'flag_ConsumerDuty' in block.split('</tr>')[0] if '</tr>' in block else 'flag_ConsumerDuty' in block[:2000]

        # Find expanded content span
        expanded_pattern = re.compile(
            r'<span[^>]*id="search-criteria-expanded-' + re.escape(row_num) + r'"[^>]*class="criteriaExpanded"([^>]*)>',
            re.DOTALL
        )
        exp_match = expanded_pattern.search(block)

        question = None
        grade = None
        grade_icon = None
        notes = None
        has_detail = False

        if exp_match:
            attrs = exp_match.group(1)
            if 'hidden' not in attrs:
                # Get content after the opening span tag
                exp_start = exp_match.end()
                # Find the closing </span> - but need to handle nested spans
                # The expanded content ends with </span> followed by whitespace
                # Use the content between the span open and the next </td> or criteriaRow
                remaining = block[exp_start:]

                # Find the content up to the closing </span> that's at indent level
                # The pattern: content ends before the first </span> that's followed by criteria structure
                span_end = remaining.find('\n</span>')
                if span_end == -1:
                    # Try alternate pattern
                    span_end_match = re.search(r'</span>\s*\n?\s*(?:<!--.*?-->)?\s*\n?\s*(?:</td>|\s*<)', remaining)
                    if span_end_match:
                        span_end = span_end_match.start()

                if span_end > 0:
                    content = remaining[:span_end]
                    if content.strip():
                        has_detail = True

                        # Extract question
                        q_match = re.search(
                            r'<div[^>]*style="[^"]*font-size:\s*1[23]px[^"]*"[^>]*>(.*?)</div>',
                            content, re.DOTALL
                        )
                        if q_match:
                            question = clean_html(q_match.group(1))

                        # Extract grade icon and text
                        grade_match = re.search(
                            r'<img[^>]*src="[^"]*/(yes(?:condition|byexception)?|no|refer|caution|value)\.png"[^>]*>\s*(?:&nbsp;)*\s*(.*?)</div>',
                            content, re.DOTALL
                        )
                        if grade_match:
                            grade_icon = grade_match.group(1)
                            grade = clean_html(grade_match.group(2))

                        # Extract notes
                        notes_match = re.search(
                            r'<div class="type--fine-print" style="margin-left: 39px;">(.*?)</div>',
                            content, re.DOTALL
                        )
                        if notes_match:
                            n = clean_html(notes_match.group(1))
                            if n:
                                notes = n

        entry = {
            "criteria_id": int(crit_id),
            "row": int(row_num),
            "criteria_name": criteria_name,
            "tags": tags,
            "consumer_duty_flagged": consumer_duty,
            "detail_available": has_detail,
        }

        if has_detail:
            entry["question"] = question
            entry["grade"] = grade
            entry["grade_icon"] = grade_icon
            if notes:
                entry["notes"] = notes

        criteria_list.append(entry)

    result = {
        "source": "Knowledge Bank",
        "source_url": "https://www.knowledgebank.uk/broker/the-bank?l=7&lt=1",
        "lender": lender_name,
        "lending_type": lending_type,
        "total_criteria": len(criteria_list),
        "criteria_with_details": sum(1 for c in criteria_list if c.get("detail_available")),
        "criteria_without_details": sum(1 for c in criteria_list if not c.get("detail_available")),
        "criteria": criteria_list,
    }

    return result


def main():
    html_path = Path("/home/user/mortgage-eligibility/Knowledge Bank ©.html")
    output_path = Path("/home/user/mortgage-eligibility/lending_criteria.json")

    print(f"Reading HTML file: {html_path}")
    html_content = html_path.read_text(encoding='utf-8')
    print(f"File size: {len(html_content):,} characters")

    print("Parsing criteria...")
    result = parse_criteria(html_content)

    print(f"\nLender: {result.get('lender', 'N/A')}")
    print(f"Lending Type: {result.get('lending_type', 'N/A')}")
    print(f"Total criteria found: {result.get('total_criteria', 0)}")
    print(f"  With inline details: {result.get('criteria_with_details', 0)}")
    print(f"  Without details (AJAX-loaded): {result.get('criteria_without_details', 0)}")

    grades = {}
    for c in result.get("criteria", []):
        if c.get("detail_available"):
            g = c.get("grade_icon") or "unknown"
            grades[g] = grades.get(g, 0) + 1
    if grades:
        print(f"  Grade distribution: {grades}")

    # Show a few examples
    print("\nSample entries:")
    for c in result["criteria"][:3]:
        print(f"  [{c['row']}] {c['criteria_name']} - detail: {c['detail_available']}")
        if c.get("grade"):
            print(f"       grade: {c['grade']} ({c.get('grade_icon')})")
        if c.get("notes"):
            print(f"       notes: {c['notes'][:80]}...")

    print(f"\nWriting JSON to: {output_path}")
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print("Done!")


if __name__ == "__main__":
    main()
