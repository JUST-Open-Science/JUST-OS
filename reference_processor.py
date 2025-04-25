import html
import json
import re

import markdown
from bs4 import BeautifulSoup

CREATOR_KEY = "Provider/Creators"
TIMESTAMP_KEY = "Timestamp"
TITLE_KEY = "Title"
URL_DOI_KEY = (
    "URL/DOI (please check DOI by collating DOI at the end of https://doi.org/ )"
)


def context_from_nodes(nodes):
    return "\n".join(
        f"[{idx}] Title: {node.metadata[TITLE_KEY]} Text: {' '.join(node.text.split())}"
        for idx, node in enumerate(nodes)
    )


def process_markdown_with_references(markdown_text, references_nodes):
    """Convert markdown to HTML and add clickable references with tooltips"""
    html_text = markdown.markdown(markdown_text)
    soup = BeautifulSoup(html_text, "html.parser")
    reference_pattern = r"\[(\d+)\]"

    text_nodes = soup.find_all(text=True)
    used_refs_ordered = []
    ref_mapping = {}

    # First pass - collect references in order of appearance
    for text in text_nodes:
        for match in re.finditer(reference_pattern, text):
            ref_idx = int(match.group(1))
            if ref_idx < len(references_nodes) and ref_idx not in ref_mapping:
                used_refs_ordered.append(ref_idx)
                ref_mapping[ref_idx] = len(used_refs_ordered)

    # Second pass - replace references with new numbers
    for text in text_nodes:
        if re.search(reference_pattern, text):
            matches = list(re.finditer(reference_pattern, text))
            new_text = text

            for match in reversed(matches):
                old_ref_num = int(match.group(1))
                start, end = match.span()

                if old_ref_num in ref_mapping:
                    new_ref_num = ref_mapping[old_ref_num]
                    ref_node = references_nodes[old_ref_num]

                    reference_data = {
                        "title": ref_node.metadata[TITLE_KEY],
                        "authors": ref_node.metadata[CREATOR_KEY],
                        "year": ref_node.metadata[TIMESTAMP_KEY],
                        "url": ref_node.metadata[URL_DOI_KEY],
                        "text": html.escape(ref_node.text),
                    }

                    data_string = json.dumps(
                        reference_data, ensure_ascii=True, separators=(",", ":")
                    )
                    escaped_data_string = html.escape(data_string, quote=True)

                    reference_html = (
                        f'<a href="#" class="reference-link" '
                        f'data-reference="{escaped_data_string}">'
                        f"[{new_ref_num}]"
                        f"</a>"
                    )

                    new_text = new_text[:start] + reference_html + new_text[end:]

            text.replace_with(BeautifulSoup(new_text, "html.parser"))

    return str(soup), used_refs_ordered


def references_from_nodes(nodes, used_refs_ordered=None):
    """Generate reference list from nodes.

    Args:
        nodes: List of reference nodes
        used_refs_ordered: Optional list of reference indices in order of appearance.
                         If None, all references will be included in original order.
    """
    if not used_refs_ordered:
        return "\n".join(
            f"[{idx + 1}] {node.metadata[CREATOR_KEY]} ({node.metadata[TIMESTAMP_KEY]}). "
            f"{node.metadata[TITLE_KEY]}. {node.metadata[URL_DOI_KEY]}"
            for idx, node in enumerate(nodes)
        )

    return "\n".join(
        f"[{idx + 1}] {nodes[ref_idx].metadata[CREATOR_KEY]} ({nodes[ref_idx].metadata[TIMESTAMP_KEY]}). "
        f"{nodes[ref_idx].metadata[TITLE_KEY]}. {nodes[ref_idx].metadata[URL_DOI_KEY]}"
        for idx, ref_idx in enumerate(used_refs_ordered)
    )
