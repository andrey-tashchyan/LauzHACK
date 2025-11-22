import pandas as pd
from datetime import datetime
import numpy as np


def calculate_account_age_months(input_file, output_file):
    """
    Calculate the age of accounts in months and add it as a new column.

    Parameters:
    -----------
    input_file : str
        Path to the input CSV file (e.g., "account.csv")
    output_file : str
        Path to the output CSV file (e.g., "account.csv")

    Returns:
    --------
    pd.DataFrame
        The DataFrame with the new 'account_age_months' column
    """

    # 1. Load the CSV file into a DataFrame
    df = pd.read_csv(input_file)

    # 2. Parse dates correctly with pandas.to_datetime
    # Using errors='coerce' to handle any invalid dates gracefully
    df['account_open_date'] = pd.to_datetime(df['account_open_date'], errors='coerce')
    df['account_close_date'] = pd.to_datetime(df['account_close_date'], errors='coerce')

    # Get today's date for open accounts
    today = pd.Timestamp(datetime.now().date())

    # 3. Calculate account age in months
    def compute_age_in_months(row):
        """
        Compute the age of an account in months.

        - If account_close_date is not null, use the period from open to close.
        - If account_close_date is null, use today's date as the end date.
        - Handle missing open_date by returning NaN
        """
        open_date = row['account_open_date']
        close_date = row['account_close_date']

        # If open_date is missing, return NaN
        if pd.isna(open_date):
            return np.nan

        # Determine the end date
        if pd.notna(close_date):
            end_date = close_date
        else:
            end_date = today

        # Calculate the difference in months
        # Using relativedelta would be more accurate, but using a simple calculation
        # that counts the approximate months (days / 30.44 avg days per month)
        delta = end_date - open_date
        months = delta.days / 30.44  # Average days per month

        return int(round(months))

    # Apply the function to each row
    df['account_age_months'] = df.apply(compute_age_in_months, axis=1)

    # 4. Save the resulting DataFrame to a new CSV file
    df.to_csv(output_file, index=False)

    print(f"✓ Account ages calculated successfully!")
    print(f"✓ Input file: {input_file}")
    print(f"✓ Output file: {output_file}")
    print(f"✓ Total accounts: {len(df)}")
    print(f"✓ Open accounts (no close date): {df['account_close_date'].isna().sum()}")
    print(f"✓ Closed accounts: {df['account_close_date'].notna().sum()}")
    print(f"\nAccount age statistics (in months):")
    print(df['account_age_months'].describe())

    return df


# Example usage
if __name__ == "__main__":
    # Call the function with input and output file paths
    df_result = calculate_account_age_months(
        input_file='LauzHACK/account.csv',
        output_file='LauzHACK/account.csv'
    )

    # Display a few examples
    print("\nSample of results:")
    print(df_result[['account_id', 'account_open_date', 'account_close_date', 'account_age_months']].head(10))
