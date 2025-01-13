from datetime import datetime
from typing import List, Tuple, Dict, Optional, Set, Any

def parse_date(date_str: str) -> datetime:
    """Parses a date string into a datetime object."""
    return datetime.strptime(date_str, '%Y-%m-%d')

def create_key(row: List) -> Tuple:
    """Creates a key tuple from non-date columns."""
    return tuple(row[1:])  # Assume date is always the first column

def build_candidate_dict(rows: List[List]) -> Dict[Tuple, List[Tuple[int, List]]]:
    """Builds a dictionary of rows grouped by non-date keys."""
    candidate_dict = {}

    # Each key is a tuple containing the non-date values
    # It is used for efficient searching of matching rows, reducing the number
    # of rows that need to be searched for every determined combination of values
    for idx, row in enumerate(rows):
        key = create_key(row)
        if key not in candidate_dict:
            candidate_dict[key] = []
        candidate_dict[key].append({"idx": idx, "row": row})

    # The rows within each key are sorted by date to increase search efficiency as well
    for key in candidate_dict:
        candidate_dict[key].sort(key=lambda x: x["row"][0])

    return candidate_dict

def find_closest_date(row: List, candidate_dict: Dict[Tuple, List[Dict[str, Any]]], used_indices: Set[int]) -> Optional[int]:
    """Finds the closest date match within a 1-day range for a given row."""
    row_date = row[0]  # Date is pre-parsed, assume it's the first column
    key = create_key(row)

    if key not in candidate_dict:
        return None

    for candidate_info in candidate_dict[key]:
        # Avoids already matched rows
        if candidate_info["idx"] in used_indices:
            continue

        candidate_date = candidate_info["row"][0]
        date_diff = (candidate_date - row_date).days

        if -1 <= date_diff <= 1:
            return candidate_info["idx"]  # Since dates are sorted, the first still non-used match is the best

    return None

def match_rows(source: List[List], target: List[List]) -> List[str]:
    """Matches rows from source to target, marking used indices."""
    used_indices = set()
    candidate_dict = build_candidate_dict(target)

    match_flags = []
    for row in source:
        match_idx = find_closest_date(row, candidate_dict, used_indices)
        if match_idx is not None:
            used_indices.add(match_idx)
            match_flags.append('FOUND')
        else:
            match_flags.append('MISSING')

    return match_flags

def reconcile_accounts(list1: List[List], list2: List[List]) -> Tuple[List[List], List[List]]:
    """
    Reconciles rows from two lists adding a matched flag as a new entry in every row.

    Args:
        list1 (List[List]): List of rows parsed as nested lists
        list2 (List[List]): List of rows parsed as nested lists
    
    Returns:
        flagged_list1 (List[List]): List of rows parsed as nested lists with a flag column informing of matches
        flagged_list2 (List[List]): List of rows parsed as nested lists with a flag column informing of matches
    """
    # Parse dates and sort lists
    parsed_list1 = [[parse_date(row[0])] + row[1:] for row in list1]
    parsed_list2 = [[parse_date(row[0])] + row[1:] for row in list2]

    # Match list1 against list2
    flags1 = match_rows(parsed_list1, parsed_list2)

    # Match list2 against list1
    flags2 = match_rows(parsed_list2, parsed_list1)

    # Reformat lists with flags
    flagged_list1 = [row + [flags1[i]] for i, row in enumerate(list1)]
    flagged_list2 = [row + [flags2[i]] for i, row in enumerate(list2)]

    return flagged_list1, flagged_list2

def test_reconcile_accounts():
    test_cases = [
        # Simple match
        {
            "list1": [["2025-01-01", "A", "B", "C"]],
            "list2": [["2025-01-02", "A", "B", "C"]],
            "expected1": [["2025-01-01", "A", "B", "C", "FOUND"]],
            "expected2": [["2025-01-02", "A", "B", "C", "FOUND"]],
        },
        # No match
        {
            "list1": [["2025-01-01", "A", "B", "C"]],
            "list2": [["2025-01-03", "A", "B", "C"]],
            "expected1": [["2025-01-01", "A", "B", "C", "MISSING"]],
            "expected2": [["2025-01-03", "A", "B", "C", "MISSING"]],
        },
        # Duplicate rows in both lists
        {
            "list1": [
                ["2025-01-01", "A", "B", "C"],
                ["2025-01-01", "A", "B", "C"],
            ],
            "list2": [
                ["2025-01-02", "A", "B", "C"],
                ["2025-01-02", "A", "B", "C"],
            ],
            "expected1": [
                ["2025-01-01", "A", "B", "C", "FOUND"],
                ["2025-01-01", "A", "B", "C", "FOUND"],
            ],
            "expected2": [
                ["2025-01-02", "A", "B", "C", "FOUND"],
                ["2025-01-02", "A", "B", "C", "FOUND"],
            ],
        },
        # Multiple possible matches
        {
            "list1": [["2025-01-01", "A", "B", "C"]],
            "list2": [
                ["2024-12-31", "A", "B", "C"],
                ["2025-01-02", "A", "B", "C"],
            ],
            "expected1": [["2025-01-01", "A", "B", "C", "FOUND"]],
            "expected2": [
                ["2024-12-31", "A", "B", "C", "FOUND"],
                ["2025-01-02", "A", "B", "C", "MISSING"],
            ],
        },
        {
            "list1": [["2025-01-01", "A", "B", "C"]],
            "list2": [
                ["2024-12-31", "A", "B", "C"],
                ["2025-01-01", "A", "B", "C"],
            ],
            "expected1": [["2025-01-01", "A", "B", "C", "FOUND"]],
            "expected2": [
                ["2024-12-31", "A", "B", "C", "FOUND"],
                ["2025-01-01", "A", "B", "C", "MISSING"],
            ],
        },
        {
            "list1": [
                ['2020-12-04', 'Tecnologia', '16.00', 'Bitbucket'],
                ['2020-12-04', 'Jurídico', '60.00', 'LinkSquares'],
                ['2020-12-05', 'Tecnologia', '50.00', 'AWS']
            ],
            "list2": [
                ['2020-12-04', 'Tecnologia', '16.00', 'Bitbucket'],
                ['2020-12-05', 'Tecnologia', '49.99', 'AWS'],
                ['2020-12-04', 'Jurídico', '60.00', 'LinkSquares']
            ],
            "expected1": [
                ['2020-12-04', 'Tecnologia', '16.00', 'Bitbucket', 'FOUND'],
                ['2020-12-04', 'Jurídico', '60.00', 'LinkSquares', 'FOUND'],
                ['2020-12-05', 'Tecnologia', '50.00', 'AWS', 'MISSING']
            ],
            "expected2": [
                ['2020-12-04', 'Tecnologia', '16.00', 'Bitbucket', 'FOUND'],
                ['2020-12-05', 'Tecnologia', '49.99', 'AWS', 'MISSING'],
                ['2020-12-04', 'Jurídico', '60.00', 'LinkSquares', 'FOUND']
            ]
        }
    ]

    for i, case in enumerate(test_cases):
        result1, result2 = reconcile_accounts(case["list1"], case["list2"])
        assert result1 == case["expected1"], f"Test case {i + 1} failed for list1"
        assert result2 == case["expected2"], f"Test case {i + 1} failed for list2"

    print("All test cases passed!")

# Example usage/test
if __name__ == "__main__":
    test_reconcile_accounts()
