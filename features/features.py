"""
Aggregate all feature functions into a single textual report.

The `features` function runs each feature, captures its docstring,
stdout output, and any returned value, and stitches everything into
one large string.
"""

import inspect
import io 
import json
import textwrap
from contextlib import redirect_stdout

# Support usage whether this file is imported as part of the features package
# or executed directly from the features directory.
try:
    from .feature_frequency import feature_frequency
    from .feature_burst_structuring import feature_burst_structuring
    from .feature_atypical_amounts import feature_atypical_amounts
    from .feature_cross_border import feature_cross_border
    from .feature_counterparties import feature_counterparties
    from .feature_irregularity import feature_irregularity
    from .feature_night_activity import feature_night_activity
    from .feature_ephemeral_account import feature_ephemeral_account
    from .feature_abnormal_activity import feature_abnormal_activity
    from .feature_account_age import feature_account_age
    from .feature_account_multiplicity import feature_account_multiplicity
except ImportError:  # pragma: no cover - fallback for direct execution
    from feature_frequency import feature_frequency
    from feature_burst_structuring import feature_burst_structuring
    from feature_atypical_amounts import feature_atypical_amounts
    from feature_cross_border import feature_cross_border
    from feature_counterparties import feature_counterparties
    from feature_irregularity import feature_irregularity
    from feature_night_activity import feature_night_activity
    from feature_ephemeral_account import feature_ephemeral_account
    from feature_abnormal_activity import feature_abnormal_activity
    from feature_account_age import feature_account_age
    from feature_account_multiplicity import feature_account_multiplicity


def _capture_feature_output(func, *args, **kwargs):
    """Run a feature function and capture its docstring, stdout, and return value."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)

    printed_output = buffer.getvalue().strip()
    doc = inspect.getdoc(func) or ""

    sections = []
    if doc:
        sections.append(textwrap.dedent(doc).strip())

    if printed_output:
        sections.append(f"Output:\n{printed_output}")

    if result is not None:
        if isinstance(result, (dict, list)):
            result_text = json.dumps(result, indent=2, default=str)
        else:
            result_text = str(result)
        sections.append(f"Returned value:\n{result_text}")

    if not sections:
        return ""

    header = f"{func.__name__}"
    underline = "-" * len(header)
    return f"{header}\n{underline}\n" + "\n\n".join(sections)


def features(transactions_df, accounts_df, partner_id=None):
    """
    Run every feature function and return a single combined string.

    Parameters:
    -----------
    transactions_df : pd.DataFrame
        Transaction data
    accounts_df : pd.DataFrame
        Account data
    partner_id : str, optional
        Specific partner to analyze. If None, analyzes all data.

    Returns:
    --------
    str
        Combined docstrings, printed output, and return values from all feature functions.
    """
    feature_calls = [
        (feature_frequency, (transactions_df,), {"partner_id": partner_id}),
        (feature_burst_structuring, (transactions_df,), {"partner_id": partner_id}),
        (feature_atypical_amounts, (transactions_df,), {"partner_id": partner_id}),
        (feature_cross_border, (transactions_df,), {"partner_id": partner_id}),
        (feature_counterparties, (transactions_df,), {"partner_id": partner_id}),
        (feature_irregularity, (transactions_df,), {"partner_id": partner_id}),
        (feature_night_activity, (transactions_df,), {"partner_id": partner_id}),
        (feature_ephemeral_account, (transactions_df, accounts_df), {"partner_id": partner_id}),
        (feature_abnormal_activity, (transactions_df, accounts_df), {"partner_id": partner_id}),
        (feature_account_age, (accounts_df,), {"partner_id": partner_id}),
        (feature_account_multiplicity, (accounts_df, transactions_df), {}),
    ]

    sections = []
    for func, args, kwargs in feature_calls:
        section = _capture_feature_output(func, *args, **kwargs)
        if section:
            sections.append(section)

    return "\n\n".join(sections)


if __name__ == "__main__":
    try:
        from aml_utils import load_data
    except ImportError:
        raise SystemExit("aml_utils.load_data is required to load sample data.")

    tx_df, acct_df = load_data()
    print(features(tx_df, acct_df))
