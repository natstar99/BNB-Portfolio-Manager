import yfinance as yf
import openpyxl
import pandas as pd
import matplotlib.pyplot as plt
import pickle
import tkinter as tk
from tkinter import simpledialog, ttk
import os

stock_splits = [('IVV', '2022-12-09', 15),  # IVV 15 for 1 split on December 9, 2022 
                ]
                
def calculate_transaction_value(df):
    df['Transaction Value'] = df['Quantity'] * df['Price']
    return df

def adjust_for_stock_splits(df, stock_splits):
    # Convert Trade Date to datetime
    df['Trade Date'] = pd.to_datetime(df['Trade Date'])
    
    # Iterate through each stock split and adjust the DataFrame
    for code, split_date, ratio in stock_splits:
        split_date = pd.to_datetime(split_date)
        
        # Adjust Quantity and Price for the specified Instrument Code and Trade Date
        mask = (df['Instrument Code'] == code) & (df['Trade Date'] <= split_date)
        df.loc[mask, 'Quantity'] *= ratio
        df.loc[mask, 'Price'] /= ratio
    
    # Recalculate Transaction Value after adjustments
    df['Transaction Value'] = df['Quantity'] * df['Price']
    return df

def separate_transactions(df):
    buy_df = df[df['Transaction Type'] == 'BUY']
    sell_df = df[df['Transaction Type'] == 'SELL']
    return buy_df, sell_df

def calculate_totals(buy_df, sell_df):
    total_shares_bought = buy_df.groupby('Instrument Code')['Quantity'].sum()
    total_shares_sold = sell_df.groupby('Instrument Code')['Quantity'].sum()
    return total_shares_bought, total_shares_sold

def calculate_weighted_average_price(df, transaction_type):
    return (df.groupby('Instrument Code')
              .apply(lambda group: (group['Price'] * group['Quantity']).sum() / group['Quantity'].sum())
              .reset_index(name=f'Weighted Average {transaction_type} Price'))

def set_index(df, column):
    df.set_index(column, inplace=True)
    return df

def calculate_adjusted_values(df):
    df['Adjusted Transaction Value'] = df['Transaction Value'].where(df['Transaction Type'] == 'BUY', -df['Transaction Value'])
    df['Adjusted Quantity'] = df['Quantity'].where(df['Transaction Type'] == 'BUY', -df['Quantity'])
    return df

def calculate_cumulative_values(df):
    df['Cumulative Transaction Value'] = df.groupby('Instrument Code')['Adjusted Transaction Value'].cumsum() * -1
    df['Cumulative Quantity'] = df.groupby('Instrument Code')['Adjusted Quantity'].cumsum()
    return df

def get_most_recent_values(df):
    max_trade_dates = df.groupby('Instrument Code')['Trade Date'].max()
    most_recent_values_df = df[df.apply(lambda row: row['Trade Date'] == max_trade_dates[row['Instrument Code']], axis=1)]
    return most_recent_values_df[['Instrument Code', 'Cumulative Transaction Value', 'Cumulative Quantity']]

def replace_small_values_with_zero(df, column, threshold):
    df[column] = df[column].apply(lambda x: 0 if x < threshold else x)
    return df

def add_last_sale_price(df):
    for ticker in df.index:
        if ticker not in ['BTC', 'RPF']:
            try:
                df.loc[ticker, 'Last Sale Price'] = yf.Ticker(ticker + ".AX").history(period='1d')['Close'].iloc[0]
            except IndexError:
                df.loc[ticker, 'Last Sale Price'] = "Not Found"
        else:
            df.loc[ticker, 'Last Sale Price'] = yf.Ticker('BTC-AUD').history(period='1d')['Close'].iloc[0]
    return df

def calculate_market_value(row):
    if row.name == 'RPF':
        return row['Cumulative Transaction Value'] * -1.07
    else:
        try:
            return row['Cumulative Quantity'] * row['Last Sale Price']
        except:
            return 0

def add_profit_loss(df):
    for idx, row in df.iterrows():
        if row['Last Sale Price'] != "Not Found":
            df.loc[idx, 'Profit/Loss'] = row['Cumulative Transaction Value'] + row['Current Market Value']
        else:
            df.loc[idx, 'Profit/Loss'] = "Not Found"
    return df

def interpolate_trading_days(data):
    date_range = pd.date_range(start=data['Trade Date'].min(), end=pd.to_datetime('today'), freq='D')
    interpolated_values_quantity = {}
    interpolated_values_transaction_value = {}

    for date in date_range:
        last_known_quantity = data.loc[data['Trade Date'] <= date, 'Cumulative Quantity'].iloc[-1]
        last_known_transaction_value = data.loc[data['Trade Date'] <= date, 'Cumulative Transaction Value'].iloc[-1]
        interpolated_values_quantity[date] = last_known_quantity
        interpolated_values_transaction_value[date] = last_known_transaction_value

    interpolated_df = pd.DataFrame({
        'Trade Date': list(interpolated_values_quantity.keys()),
        'Cumulative Quantity': list(interpolated_values_quantity.values()),
        'Cumulative Transaction Value': list(interpolated_values_transaction_value.values())
    })
    return interpolated_df

def get_dividends(ticker, interpolated_df):
    dividends = yf.Ticker(ticker).dividends
    div_df = pd.DataFrame(dividends)
    div_df['Trade Date'] = div_df.index.tz_localize(None)
    combined_df = interpolated_df.merge(div_df, left_on='Trade Date', right_on='Trade Date', how='left')
    return combined_df

def process_tickers(df, tickers):
    ticker_dfs = {}
    for ticker in tickers:
        if ticker != 'RPF':
            ticker_df = df[df['Instrument Code'] == ticker]

            if ticker != 'BTC':
                stock_data = yf.download(f"{ticker}.AX", start=ticker_df['Trade Date'].min(), end=pd.to_datetime('today'))['Close']
            else:
                stock_data = yf.download(f"{ticker}-AUD", start=ticker_df['Trade Date'].min(), end=pd.to_datetime('today'))['Close']

            stock_data = pd.DataFrame(stock_data)
            interpolated_df = interpolate_trading_days(ticker_df)

            if ticker != 'BTC':
                combined_df = get_dividends(f"{ticker}.AX", interpolated_df)
            else:
                combined_df = get_dividends(f"{ticker}-AUD", interpolated_df)

            combined_df['Price'] = combined_df['Trade Date'].map(stock_data['Close'])
            combined_df['Price'] = combined_df['Price'].fillna(method='ffill')
            combined_df['Dividends'] = combined_df['Dividends'].fillna(0)

            fractional_shares = combined_df['Cumulative Quantity'].max() % 1 > 0
            combined_df['Market Value (Without Dividends)'] = combined_df['Cumulative Quantity'] * combined_df['Price']
            combined_df['Cumulative Quantity With Dividends'] = combined_df['Cumulative Quantity']
            combined_df['Dividend Units Remainder'] = 0.0

            for index in range(len(combined_df)):
                row = combined_df.iloc[index]
                if row['Dividends'] > 0:
                    shares = row['Cumulative Quantity With Dividends']
                    dividend = row['Dividends']
                    price = row['Price']
                    dividend_units = (dividend * shares) / price

                    for row_idx in range(index + 1, len(combined_df)):
                        if fractional_shares:
                            combined_df.at[row_idx, 'Cumulative Quantity With Dividends'] += dividend_units
                        else:
                            combined_df.at[row_idx, 'Dividend Units Remainder'] += dividend_units % 1
                            combined_df.at[row_idx, 'Cumulative Quantity With Dividends'] += dividend_units // 1
                            if combined_df.at[row_idx, 'Dividend Units Remainder'] >= 1:
                                combined_df.at[row_idx, 'Dividend Units Remainder'] -= 1

            combined_df['Market Value (With Dividends)'] = combined_df['Cumulative Quantity With Dividends'] * combined_df['Price']

            # Define the threshold
            threshold = 1e-6

            # Initialize variables to keep track of the fixed value and if we are in the fixed mode
            fixed_value = None
            in_fixed_mode = False

            # Iterate through the DataFrame
            for index, row in combined_df.iterrows():
                if row['Cumulative Quantity'] < threshold:
                    if not in_fixed_mode:
                        fixed_value = row['Market Value (With Dividends)']
                        in_fixed_mode = True
                    combined_df.at[index, 'Market Value (With Dividends)'] = fixed_value
                else:
                    in_fixed_mode = False

            ticker_dfs[ticker] = combined_df
            
    return ticker_dfs

def set_negative_market_values_to_zero(ticker_dfs):
    for ticker, df in ticker_dfs.items():
        df['Market Value (With Dividends)'] = df['Market Value (With Dividends)'].clip(lower=0)
        df['Market Value (Without Dividends)'] = df['Market Value (Without Dividends)'].clip(lower=0)
    return ticker_dfs

def main(file_path):
    df = pd.read_excel(file_path, sheet_name='Transaction Data')
    df = calculate_transaction_value(df)
    df = adjust_for_stock_splits(df, stock_splits)
    buy_df, sell_df = separate_transactions(df)
    total_shares_bought, total_shares_sold = calculate_totals(buy_df, sell_df)
    
    weighted_average_purchase_price = calculate_weighted_average_price(buy_df, 'Purchase')
    weighted_average_sale_price = calculate_weighted_average_price(sell_df, 'Sale')
    
    weighted_average_purchase_price = set_index(weighted_average_purchase_price, 'Instrument Code')
    weighted_average_sale_price = set_index(weighted_average_sale_price, 'Instrument Code')
    
    df = calculate_adjusted_values(df)
    df = calculate_cumulative_values(df)
    df.sort_values(by=['Instrument Code', 'Trade Date'], inplace=True)
    
    most_recent_values_df = get_most_recent_values(df)
    most_recent_values_df = set_index(most_recent_values_df, 'Instrument Code')
    most_recent_values_df = replace_small_values_with_zero(most_recent_values_df, 'Cumulative Quantity', 1e-6)
    
    most_recent_values_df['Weighted Average Purchase Price'] = weighted_average_purchase_price["Weighted Average Purchase Price"]
    most_recent_values_df['Weighted Average Sale Price'] = weighted_average_sale_price['Weighted Average Sale Price']
    most_recent_values_df['Total Shares Bought'] = total_shares_bought
    most_recent_values_df['Total Shares Sold'] = total_shares_sold
    
    most_recent_values_df = add_last_sale_price(most_recent_values_df)
    most_recent_values_df['Current Market Value'] = most_recent_values_df.apply(calculate_market_value, axis=1)
    most_recent_values_df = add_profit_loss(most_recent_values_df)
    
    tickers = most_recent_values_df[most_recent_values_df['Last Sale Price'] != 'Not Found'].index

    ticker_dfs = process_tickers(df, tickers)
    ticker_dfs = set_negative_market_values_to_zero(ticker_dfs)
    
    return ticker_dfs