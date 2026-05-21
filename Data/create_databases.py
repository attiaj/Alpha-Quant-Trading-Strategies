from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5

# MT5 rate times are Unix seconds (UTC). Convert to US Eastern (EST/EDT).
EST = "America/New_York"


def mt5_time_to_est(series):
    """Unix seconds from MT5 → timezone-aware Eastern datetime."""
    return pd.to_datetime(series, unit="s", utc=True).dt.tz_convert(EST)


# Initialize the bounds between MetaTrader 5 and Python
mt5.initialize()


def get_rates(symbol, number_of_data=10_000, timeframe=mt5.TIMEFRAME_D1):
    # Compute now date
    from_date = datetime.now()

    # Extract n rates before now
    rates = mt5.copy_rates_from(symbol, timeframe, from_date, number_of_data)

    # Transform array into a DataFrame
    df_rates = pd.DataFrame(rates)

    # Convert Unix seconds → Eastern datetime
    df_rates["time"] = mt5_time_to_est(df_rates["time"])
    df_rates = df_rates.set_index("time")

    return df_rates

# !! You can't import more than 99.999 rows in one request
df = get_rates("GBPUSD", number_of_data=99_999, timeframe=mt5.TIMEFRAME_M30)

# Display the data
print("First 100 rows:\n")
print(df.head(100))
print("\nLast 100 rows:\n")
print(df.tail(100))

# Put where you want to save the database
save_path = input("Write the path to save csv file to (or click enter if not saving): ")

# Save the database if you had put a path
if len(save_path)>0:
    df.to_csv(save_path)



###### Exercise
#- Do the same thing, for one of the 3 other function (copy_rates_range, copy_ticks_from or copy_ticks_range)