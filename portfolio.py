import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import sv_ttk
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Slider
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
from matplotlib.widgets import RangeSlider
import seaborn as sns
import pickle
import pandas as pd
import os
import shutil
import threading
import stock_info_collector
from tkcalendar import DateEntry
from datetime import datetime
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
import squarify

# Function to find the earliest trade date with non-zero portfolio performance
def find_earliest_non_zero_date(selected_tickers):
    min_date = None
    for ticker in selected_tickers:
        non_zero_indices = (portfolio_df[f'{ticker}_Market_Value_WithDiv'] + portfolio_df[f'{ticker}_Cumulative_Transaction_Value']) != 0
        ticker_min_date = portfolio_df.loc[non_zero_indices, 'Trade Date'].min()
        if min_date is None or (ticker_min_date is not None and ticker_min_date < min_date):
            min_date = ticker_min_date
    return min_date - pd.DateOffset(days=1) if min_date is not None else None

# Function to format y-axis labels as dollars with commas
def dollar_format(x, pos):
    return f"${x:,.0f}"

# Function to plot based on the selected plot type and mode (individual/aggregate)
def plot_selected(mode):
    if selected_plot_type.get() == "Portfolio Distribution":
        plot_portfolio_distribution()
    elif selected_plot_type.get() == "Stacked Area Chart":
        plot_stacked_area()
    elif selected_plot_type.get() == "Portfolio Treemap":
        plot_portfolio_treemap()
    else:
        # Clear the plot frame
        for widget in plot_frame.winfo_children():
            widget.destroy()
        
        # Create a new figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        selected_tickers = [ticker for ticker, var in ticker_vars.items() if var.get() == 1]
        
        if not selected_tickers:
            messagebox.showwarning("Warning", "Please select at least one ticker.")
            return
        
        min_date = find_earliest_non_zero_date(selected_tickers)
        
        if min_date is None:
            messagebox.showwarning("Warning", "No data available for selected tickers.")
            return
        
        if mode == 'individual':
            # Plot selected tickers individually
            for ticker in selected_tickers:
                if selected_plot_type.get() == "Value of Portfolio":
                    ax.plot(portfolio_df['Trade Date'], portfolio_df[f'{ticker}_Market_Value_WithDiv'], label=f'{ticker} Market Value (With Dividends)')
                    ax.plot(portfolio_df['Trade Date'], portfolio_df[f'{ticker}_Market_Value_WithoutDiv'], label=f'{ticker} Market Value (Without Dividends)')
                elif selected_plot_type.get() == "Dividend Performance":
                    ax.plot(portfolio_df['Trade Date'], portfolio_df[f'{ticker}_Dividends_Earned']*portfolio_df[f'{ticker}_Price'], label=f'{ticker}')
                elif selected_plot_type.get() == "Profit/Loss":
                    ax.plot(portfolio_df['Trade Date'], portfolio_df[f'{ticker}_Market_Value_WithDiv'] + portfolio_df[f'{ticker}_Cumulative_Transaction_Value'], label=ticker)
            
            title = 'Individual Stock Performance'
            
        elif mode == 'aggregate':
            # Initialize aggregate columns
            portfolio_df['Portfolio_Market_Value'] = sum(portfolio_df[f'{ticker}_Market_Value_WithDiv'] for ticker in selected_tickers)
            portfolio_df['Dividend_Performance'] = sum(portfolio_df[f'{ticker}_Market_Value_WithDiv'] - portfolio_df[f'{ticker}_Market_Value_WithoutDiv'] for ticker in selected_tickers)
            portfolio_df['Portfolio_Cumulative_Transaction_Value'] = sum(portfolio_df[f'{ticker}_Cumulative_Transaction_Value'] for ticker in selected_tickers)
            
            # Plot the aggregated portfolio performance
            if selected_plot_type.get() == "Value of Portfolio":
                ax.plot(portfolio_df['Trade Date'], portfolio_df['Portfolio_Market_Value'], label='Aggregate Market Value')
            elif selected_plot_type.get() == "Dividend Performance":
                ax.plot(portfolio_df['Trade Date'], portfolio_df['Dividend_Performance'], label='Aggregate Dividend Performance')
            elif selected_plot_type.get() == "Profit/Loss":
                ax.plot(portfolio_df['Trade Date'], portfolio_df['Portfolio_Market_Value'] + portfolio_df['Portfolio_Cumulative_Transaction_Value'], label='Aggregate', linewidth=1, color='darkgreen')
            
            title = 'Overall Portfolio Performance'
        
        # Set plot labels and title
        ax.set_xlabel('Trade Date')
        ax.set_ylabel('Portfolio Performance')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollar_format))
        
        # Set x-axis limits based on the earliest trade date with non-zero portfolio performance
        ax.set_xlim(min_date, None)
        
        # Add legend
        ax.legend(loc="upper left", bbox_to_anchor=(1, 1))
        
        # Adjust layout to prevent cutting off labels
        plt.tight_layout()
        
        # Embed the plot into tkinter
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)

# Function to select all tickers
def select_all():
    for var in ticker_vars.values():
        var.set(1)

# Function to deselect all tickers
def select_none():
    for var in ticker_vars.values():
        var.set(0)

# Function to get template
def get_template():
    save_path = filedialog.askdirectory(title="Where would you like to save the template?")
    if save_path:
        template_path = os.path.join(save_path, "Transaction_Data_Template.xlsx")
        # Assuming 'Transaction_Data_Template.xlsx' is in the root folder
        shutil.copy("Transaction_Data_Template.xlsx", template_path)
        messagebox.showinfo("Success", f"Template saved to {template_path}")

def load_new_portfolio_data(initial_window=None):
    file_path = filedialog.askopenfilename(title="Which transaction data do you wish to load?", filetypes=[("Excel files", "*.xlsx")])
    if file_path:
        # Load the transaction data
        new_df = pd.read_excel(file_path, sheet_name='Transaction Data')

        # Check if the columns match the template
        template_df = pd.read_excel("Transaction_Data_Template.xlsx")
        if not all(col in new_df.columns for col in template_df.columns):
            messagebox.showerror("Error", "The columns of the selected file do not match the template.")
            return

        # Create loading screen
        loading_window = tk.Toplevel(root)
        loading_window.title("Loading")
        loading_window.geometry("300x150")
        loading_window.transient()
        loading_window.grab_set()

        # Close the initial window if it exists
        if initial_window and initial_window.winfo_exists():
            initial_window.destroy()

        loading_label = ttk.Label(loading_window, text="Processing data... Please wait.")
        loading_label.pack(pady=10)

        progress_bar = ttk.Progressbar(loading_window, mode="indeterminate")
        progress_bar.pack(pady=10)
        progress_bar.start()

        # Event to synchronize threads
        event = threading.Event()
        ticker_dfs = []

        def process_data():
            ticker_dfs.append(stock_info_collector.main(file_path))
            event.set()

        # Run the data processing in a separate thread
        threading.Thread(target=process_data, daemon=True).start()

        def check_event():
            if event.is_set():
                loading_window.after(0, lambda: on_data_processed(ticker_dfs, loading_window))
            else:
                loading_window.after(100, check_event)

        loading_window.after(100, check_event)

def on_data_processed(ticker_dfs, loading_window):
    # Stop the progress bar
    for widget in loading_window.winfo_children():
        widget.destroy()

    save_ticker_dfs(ticker_dfs[0], loading_window)

def save_ticker_dfs(ticker_dfs, loading_window):
    loading_window.title("Save Portfolio")
    
    ttk.Label(loading_window, text="Enter the portfolio name:").pack(pady=10)
    
    portfolio_name_var = tk.StringVar()
    portfolio_name_entry = ttk.Entry(loading_window, textvariable=portfolio_name_var)
    portfolio_name_entry.pack(pady=10)
    
    def save_portfolio():
        portfolio_name = portfolio_name_var.get()
        if portfolio_name:
            # Save the new portfolio data as a pickle file
            new_portfolio_path = os.path.join("portfolios", f"{portfolio_name}.pkl")
            with open(new_portfolio_path, 'wb') as f:
                pickle.dump(ticker_dfs, f)
            loading_window.destroy()
    
    ttk.Button(loading_window, text="Save", command=save_portfolio).pack(pady=10)

def refresh_ui():
    global ticker_vars, portfolio_df, ticker_dfs

    # Refresh the ticker selection frame
    for widget in selection_frame.winfo_children():
        widget.destroy()

    ticker_vars = {}
    for i, ticker in enumerate(ticker_dfs.keys()):
        ticker_vars[ticker] = tk.IntVar()
        ttk.Checkbutton(selection_frame, text=ticker, variable=ticker_vars[ticker]).grid(row=i, column=0, sticky='w')

    select_all_button = ttk.Button(selection_frame, text="Select All", command=select_all)
    select_all_button.grid(row=len(ticker_dfs), column=0, pady=5, sticky='w')

    select_none_button = ttk.Button(selection_frame, text="Select None", command=select_none)
    select_none_button.grid(row=len(ticker_dfs) + 1, column=0, pady=5, sticky='w')


def select_portfolio():

    portfolio_window = tk.Toplevel(root)
    portfolio_window.title("Select Portfolio")
    portfolio_window.geometry("300x300")
    sv_ttk.set_theme("dark")

    listbox = tk.Listbox(portfolio_window, selectmode=tk.SINGLE)
    listbox.pack(fill=tk.BOTH, expand=True)

    portfolios = [f for f in os.listdir("portfolios") if f.endswith(".pkl")]
    for portfolio in portfolios:
        listbox.insert(tk.END, portfolio)

    selected_portfolio = tk.StringVar()

    def on_select():
        if listbox.curselection():
            selected = listbox.get(listbox.curselection())
            selected_portfolio.set(selected)
            portfolio_window.destroy()
        else:
            messagebox.showwarning("Warning", "Please select a portfolio.")

    select_button = ttk.Button(portfolio_window, text="Load Portfolio", command=on_select)
    select_button.pack(pady=10)

    portfolio_window.wait_window()
    try:
        if selection_frame:
            global portfolio_df, ticker_dfs
            portfolio_df, ticker_dfs = load_selected_portfolio(selected_portfolio.get())
            refresh_ui()
    except:
        # Handle the exception here (e.g., log an error message or display a user-friendly message)
        print(f"selection_frame does not yet exist. Skipping refresh_ui")

    return selected_portfolio.get()


def new_user():

    # Initialize tkinter window
    initial_window = tk.Toplevel(root)
    initial_window.title("Welcome to Portfolio Manager")
    initial_window.geometry("400x300")
    sv_ttk.set_theme("dark")
    
    # Display welcome message and instructions
    message = (
        "Welcome to Portfolio Manager!\n\n"
        "No portfolios added yet.\n\n"
        "Please load in transaction data using the Excel template.\n\n"
        "If you don't have the template, you can get it below.\n\n"
    )
    label = ttk.Label(initial_window, text=message, padding=(10, 10))
    label.pack()

    get_template_button = ttk.Button(initial_window, text="Get Template", command=get_template)
    get_template_button.pack(pady=5)

    load_data_button = ttk.Button(initial_window, text="Load Data", command=lambda: load_new_portfolio_data(initial_window))
    load_data_button.pack(pady=5)

    return initial_window

def load_selected_portfolio(selected_portfolio):
    
    with open(os.path.join("portfolios", selected_portfolio), 'rb') as f:
        global ticker_dfs
        ticker_dfs = pickle.load(f)

    global portfolio_df
    portfolio_df = pd.DataFrame()

    for ticker, df in ticker_dfs.items():
        if 'Trade Date' in df.columns:
            ticker_data = df[['Trade Date', 'Price', 'Market Value (With Dividends)', 'Market Value (Without Dividends)', 
                              'Cumulative Transaction Value', 'Cumulative Quantity', 'Dividends Earned']]
            
            ticker_data.columns = ['Trade Date', f'{ticker}_Price', f'{ticker}_Market_Value_WithDiv', f'{ticker}_Market_Value_WithoutDiv', 
                                   f'{ticker}_Cumulative_Transaction_Value', f'{ticker}_Cumulative_Quantity', f'{ticker}_Dividends_Earned']

            if portfolio_df.empty:
                portfolio_df = ticker_data
            else:
                portfolio_df = pd.merge(portfolio_df, ticker_data, on='Trade Date', how='outer')

    # Fill missing values with 0
    portfolio_df = portfolio_df.fillna(0)

    #portfolio_window.destroy()
    return portfolio_df, ticker_dfs

def show_statistics_panel():
    # Clear the plot frame
    for widget in plot_frame.winfo_children():
        widget.destroy()

    # Create statistics panel
    stats_frame = ttk.Frame(plot_frame)
    stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # Start Date
    ttk.Label(stats_frame, text="Start Date:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
    start_date = DateEntry(stats_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
    start_date.grid(row=0, column=1, padx=5, pady=5)

    # End Date
    ttk.Label(stats_frame, text="End Date:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
    end_date = DateEntry(stats_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
    end_date.grid(row=1, column=1, padx=5, pady=5)

    # Results display
    results_frame = ttk.LabelFrame(stats_frame, text="Results")
    results_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky='nsew')

    # Create Treeview
    tree = ttk.Treeview(results_frame, columns=('Metric', 'Start Date', 'End Date', 'Period'), show='headings')
    tree.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

    # Configure grid to expand with window
    results_frame.columnconfigure(0, weight=1)
    results_frame.rowconfigure(0, weight=1)

    # Define headings
    tree.heading('Metric', text='Metric')
    tree.heading('Start Date', text='Start Date')
    tree.heading('End Date', text='End Date')
    tree.heading('Period', text='Period')

    # Configure column widths and alignment
    tree.column('Metric', width=150, anchor='w')
    tree.column('Start Date', width=150, anchor='center')
    tree.column('End Date', width=150, anchor='center')
    tree.column('Period', width=150, anchor='center')

    # Define rows
    tree.insert('', 'end', values=('Valuation', '', '', ''))
    tree.insert('', 'end', values=('Total Invested', '', '', ''))
    tree.insert('', 'end', values=('$ Profit/Loss', '', '', ''))
    tree.insert('', 'end', values=('% Profit/Loss', '', '', ''))
    tree.insert('', 'end', values=('$ Dividend Yield', '', '', ''))
    tree.insert('', 'end', values=('% Dividend Yield', '', '', ''))

    def calculate_statistics():
        selected_tickers = [ticker for ticker, var in ticker_vars.items() if var.get() == 1]
        
        if not selected_tickers:
            messagebox.showwarning("Warning", "Please select at least one ticker.")
            return

        start = pd.to_datetime(start_date.get_date())
        end = pd.to_datetime(end_date.get_date())

        df = portfolio_df[(portfolio_df['Trade Date'] >= start) & (portfolio_df['Trade Date'] <= end)]

        if df.empty:
            messagebox.showwarning("Warning", "No data available for the selected date range.")
            return

        # Initialise values
        total_spent_at_start_date = 0
        total_spent_at_end_date = 0
        start_value = 0
        end_value = 0
        total_dividends_at_start = 0
        total_dividends_at_end = 0

        # Calculate statistics for each selected ticker and aggregate
        for ticker in selected_tickers:
            ticker_start_value = df.iloc[0][f'{ticker}_Market_Value_WithDiv']
            ticker_end_value = df.iloc[-1][f'{ticker}_Market_Value_WithDiv']
            ticker_spend_at_start = df.iloc[0][f'{ticker}_Cumulative_Transaction_Value']
            ticker_spend_at_end = df.iloc[-1][f'{ticker}_Cumulative_Transaction_Value']
            ticker_dividends_at_start = df.iloc[0][f'{ticker}_Market_Value_WithDiv'] - df.iloc[0][f'{ticker}_Market_Value_WithoutDiv']
            ticker_dividends_at_end = df.iloc[-1][f'{ticker}_Market_Value_WithDiv'] - df.iloc[-1][f'{ticker}_Market_Value_WithoutDiv']

            total_spent_at_start_date += ticker_spend_at_start
            total_spent_at_end_date += ticker_spend_at_end
            start_value += ticker_start_value
            end_value += ticker_end_value
            total_dividends_at_start += ticker_dividends_at_start
            total_dividends_at_end += ticker_dividends_at_end

        dividends_received_over_period = total_dividends_at_end - total_dividends_at_start
        dividend_yield = (dividends_received_over_period / end_value) * 100 if end_value != 0 else 0
        percent_profit_loss_at_start = ((start_value/-total_spent_at_start_date)-1)*100
        percent_profit_loss_at_end = ((end_value/-total_spent_at_end_date)-1)*100
        percent_profit_loss_over_period = percent_profit_loss_at_end - percent_profit_loss_at_start

        # Update Treeview with calculated values
        tree.item(tree.get_children()[0], values=('Market Valuation', f'${start_value:.2f}', f'${end_value:.2f}', 'N/A'))
        tree.item(tree.get_children()[1], values=('Total Invested', f'${total_spent_at_start_date:.2f}', f'${total_spent_at_end_date:.2f}', 'N/A'))
        tree.item(tree.get_children()[2], values=('$ Profit/Loss', f'${(start_value+total_spent_at_start_date):.2f}', f'${(end_value+total_spent_at_end_date):.2f}', f'${-((start_value+total_spent_at_start_date) - (end_value+total_spent_at_end_date)):.2f}'))
        tree.item(tree.get_children()[3], values=('% Profit/Loss', f'{percent_profit_loss_at_start:.2f}%', f'{percent_profit_loss_at_end:.2f}%', f'{percent_profit_loss_over_period:.2f}%'))
        tree.item(tree.get_children()[4], values=('$ Dividend Returns', f'${total_dividends_at_start:.2f}', f'${total_dividends_at_end:.2f}', f'${dividends_received_over_period:.2f}'))
        tree.item(tree.get_children()[5], values=('% Dividend Returns', f'N/A', f'N/A', f'{dividend_yield:.2f}%'))
    calculate_button = ttk.Button(stats_frame, text="Calculate", command=calculate_statistics)
    calculate_button.grid(row=3, column=0, columnspan=2, pady=10)

    def update_start_date():
        selected_tickers = [ticker for ticker, var in ticker_vars.items() if var.get() == 1]
        
        if not selected_tickers:
            messagebox.showwarning("Warning", "Please select at least one ticker.")
            return
        
        earliest_date = portfolio_df[portfolio_df[[f'{ticker}_Market_Value_WithDiv' for ticker in selected_tickers]].gt(0).any(axis=1)]['Trade Date'].min()
        
        if use_earliest_date.get():
            start_date.set_date(earliest_date)
        
        start_date.config(state='disabled' if use_earliest_date.get() else 'normal', mindate=earliest_date)

    # Checkbox for earliest date
    use_earliest_date = tk.BooleanVar()
    earliest_date_cb = ttk.Checkbutton(stats_frame, text="Use earliest available date", 
                                    variable=use_earliest_date, command=update_start_date)
    earliest_date_cb.grid(row=0, column=2, columnspan=2, padx=5, pady=5, sticky='w')

    # Initially call update_start_date to set the minimum date
    update_start_date()

def plot_stacked_area():
    selected_tickers = [ticker for ticker, var in ticker_vars.items() if var.get() == 1]
    
    if not selected_tickers:
        messagebox.showwarning("Warning", "Please select at least one ticker.")
        return
    
    # Clear the plot frame
    for widget in plot_frame.winfo_children():
        widget.destroy()
    
    # Create a new figure
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Prepare data for stacked area chart
    data = portfolio_df[['Trade Date'] + [f'{ticker}_Market_Value_WithDiv' for ticker in selected_tickers]]
    data = data.set_index('Trade Date')
    
    # Create stacked area chart
    data.plot.area(stacked=True, ax=ax)
    
    # Find the minimum date with non-zero values
    min_date = find_earliest_non_zero_date(selected_tickers)
    
    if min_date is None:
        messagebox.showwarning("Warning", "No data available for selected tickers.")
        return
    
    # Customize the plot
    ax.set_title('Portfolio Composition Over Time', fontsize=14, fontweight='bold')
    ax.set_xlabel('Trade Date')
    ax.set_ylabel('Market Value (With Dividends)')
    ax.legend(title='Tickers', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Format y-axis labels as dollars
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollar_format))
    
    # Set x-axis limits based on the earliest trade date with non-zero portfolio performance
    ax.set_xlim(min_date, None)
    
    # Retrieve legend handles and labels
    handles, labels = ax.get_legend_handles_labels()
    
    # Modify labels by removing '_Market_Value_WithDiv'
    modified_labels = [label.split('_')[0] for label in labels]
    
    # Set modified handles and labels back to the legend
    ax.legend(handles, modified_labels, title='Tickers', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Adjust layout to prevent cutting off labels
    plt.tight_layout()
    
    # Embed the plot into tkinter
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)

def plot_portfolio_distribution():
    global ticker_vars  # We'll need to modify this global variable

    selected_tickers = [ticker for ticker, var in ticker_vars.items() if var.get() == 1]
    
    if not selected_tickers:
        messagebox.showwarning("Warning", "Please select at least one ticker.")
        return
    
    # Clear the plot frame
    for widget in plot_frame.winfo_children():
        widget.destroy()
    
    # Create a new figure with subplots for the pie chart and slider
    fig, (ax_pie, ax_slider) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [20, 1]})
    
    # Prepare data
    data = portfolio_df[['Trade Date'] + [f'{ticker}_Market_Value_WithDiv' for ticker in selected_tickers]]
    data = data.set_index('Trade Date')
    
    # Ensure all dates are timezone-naive
    data.index = data.index.tz_localize(None)
    
    # Get the date range
    date_range = data.index
    min_date = date_range.min()
    max_date = date_range.max()
    
    # Function to update the pie chart
    def update_pie(val):
        ax_pie.clear()
        date = pd.Timestamp(mdates.num2date(val)).tz_localize(None)
        closest_date = date_range[np.abs(date_range - date).argmin()]
        values = data.loc[closest_date]
        
        # Remove tickers with NaN or values less than $1
        valid_tickers = [ticker for ticker in selected_tickers if values[f'{ticker}_Market_Value_WithDiv'] >= 1]
        valid_values = [values[f'{ticker}_Market_Value_WithDiv'] for ticker in valid_tickers]
        
        # Update the selection frame
        for ticker in selected_tickers:
            if ticker not in valid_tickers and ticker_vars[ticker].get() == 1:
                ticker_vars[ticker].set(0)  # Uncheck the ticker in the selection frame
        
        if not valid_tickers:
            ax_pie.text(0.5, 0.5, "No valid data for this date", ha='center', va='center')
        else:
            wedges, texts, autotexts = ax_pie.pie(valid_values, labels=valid_tickers, autopct='%1.1f%%', startangle=90)
            
            # Add value labels
            for i, autotext in enumerate(autotexts):
                autotext.set_text(f'${valid_values[i]:,.0f}')
        
        ax_pie.set_title(f'Portfolio Distribution on {closest_date.strftime("%Y-%m-%d")}', fontsize=14, fontweight='bold')
        fig.canvas.draw_idle()
    
    # Create the slider
    slider_ax = fig.add_axes([0.2, 0.05, 0.6, 0.03])
    slider = Slider(
        ax=slider_ax,
        label='Date',
        valmin=mdates.date2num(min_date),
        valmax=mdates.date2num(max_date),
        valinit=mdates.date2num(max_date),
        valstep=mdates.date2num(date_range[1]) - mdates.date2num(date_range[0])
    )
    
    # Set the slider's format to display dates
    slider.valtext.set_text(max_date.strftime('%Y-%m-%d'))
    
    # Update function for the slider text
    def update_slider_text(val):
        slider.valtext.set_text(pd.Timestamp(mdates.num2date(val)).tz_localize(None).strftime('%Y-%m-%d'))
    
    slider.on_changed(update_slider_text)
    
    # Connect the update function to the slider
    slider.on_changed(update_pie)
    
    # Initial plot
    update_pie(mdates.date2num(max_date))
    
    # Adjust layout
    plt.tight_layout()
    
    # Embed the plot into tkinter
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)
    
    # Keep a reference to the slider to prevent it from being garbage collected
    canvas.slider = slider

    # Function to refresh the selection frame
    def refresh_selection_frame():
        for widget in selection_frame.winfo_children():
            widget.destroy()
        
        for i, ticker in enumerate(ticker_vars.keys()):
            ttk.Checkbutton(selection_frame, text=ticker, variable=ticker_vars[ticker]).grid(row=i, column=0, sticky='w')
        
        select_all_button = ttk.Button(selection_frame, text="Select All", command=select_all)
        select_all_button.grid(row=len(ticker_vars), column=0, pady=5, sticky='w')
        
        select_none_button = ttk.Button(selection_frame, text="Select None", command=select_none)
        select_none_button.grid(row=len(ticker_vars) + 1, column=0, pady=5, sticky='w')
    
    # Refresh the selection frame
    refresh_selection_frame()

# Global variable to store the color bar axis
colorbar_ax = None

def plot_portfolio_treemap():
    global ticker_vars  # We need to modify this global variable
    global colorbar_ax  # Reference to the color bar axis

    selected_tickers = [ticker for ticker, var in ticker_vars.items() if var.get() == 1]
    
    if not selected_tickers:
        messagebox.showwarning("Warning", "Please select at least one ticker.")
        return
    
    # Clear the plot frame
    for widget in plot_frame.winfo_children():
        widget.destroy()
    
    # Create a new figure with subplots for the treemap and slider
    fig, (ax_treemap, ax_slider) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [20, 1]})
    
    # Create a dedicated axis for the color bar
    colorbar_ax = fig.add_axes([0.92, 0.3, 0.02, 0.4])  # Adjust the position as needed
    
    # Prepare data
    data = portfolio_df[['Trade Date'] + 
                        [f'{ticker}_Market_Value_WithDiv' for ticker in selected_tickers] +
                        [f'{ticker}_Cumulative_Transaction_Value' for ticker in selected_tickers] +
                        [f'{ticker}_Cumulative_Quantity' for ticker in selected_tickers]
                        ]

    data = data.set_index('Trade Date')
    
    # Ensure all dates are timezone-naive
    data.index = data.index.tz_localize(None)
    
    # Find the earliest date with non-zero data for any selected ticker
    valid_data = data[[f'{ticker}_Market_Value_WithDiv' for ticker in selected_tickers]].gt(0).any(axis=1)
    min_date = data.index[valid_data].min()
    max_date = data.index.max()
    
    # Function to create color map
    def create_colormap():
        colors = ['darkred', 'red', 'orange', 'lightgrey', 'lightgreen', 'green', 'darkgreen']
        return mcolors.LinearSegmentedColormap.from_list("custom", colors, N=256)
    
    custom_cmap = create_colormap()
    
    # Function to update the treemap
    def update_treemap(start_val, end_val):
        global colorbar_ax
        
        ax_treemap.clear()
        colorbar_ax.clear()  # Clear the color bar axis
        
        start_date = pd.Timestamp(mdates.num2date(start_val)).tz_localize(None)
        end_date = pd.Timestamp(mdates.num2date(end_val)).tz_localize(None)
        
        start_values = data.loc[start_date]
        end_values = data.loc[end_date]
        
        sizes = []
        labels = []
        profits = []
        valid_tickers = []
        
        for ticker in selected_tickers:
            start_market_value = start_values[f'{ticker}_Market_Value_WithDiv']
            end_market_value = end_values[f'{ticker}_Market_Value_WithDiv']
            number_of_shares = end_values[f'{ticker}_Cumulative_Quantity']
            start_transaction_value = start_values[f'{ticker}_Cumulative_Transaction_Value']
            end_transaction_value = end_values[f'{ticker}_Cumulative_Transaction_Value']
            
            if number_of_shares > 0:
                profit_loss = (end_market_value + end_transaction_value) - (start_market_value + start_transaction_value)
                percent_profit_loss = (profit_loss / abs(start_transaction_value)) * 100 if start_transaction_value != 0 else 0
                
                sizes.append(end_market_value)
                labels.append(f"{ticker}\n${end_market_value:.0f}\n{percent_profit_loss:.1f}%\n${profit_loss:.0f}")
                profits.append(profit_loss)
                valid_tickers.append(ticker)
            else:
                ticker_vars[ticker].set(0)  # Uncheck the ticker in the selection frame
        
        if sizes:
            # Center the color scale at 0
            max_abs_profit = max(abs(min(profits)), abs(max(profits)))
            norm = mcolors.TwoSlopeNorm(vmin=-max_abs_profit, vcenter=0, vmax=max_abs_profit)
            
            # Plot treemap with custom colors and borders
            squarify.plot(sizes=sizes, label=labels, color=[custom_cmap(norm(p)) for p in profits],
                          alpha=0.8, ax=ax_treemap, pad=True, text_kwargs={'color':'black', 'size':8})
            
            ax_treemap.axis('off')
            ax_treemap.set_title(f'Portfolio Treemap\n{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
                                 fontsize=14, fontweight='bold')
            
            # Add new colorbar
            sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
            sm.set_array([])
            plt.colorbar(sm, cax=colorbar_ax, orientation='vertical', label='Profit/Loss ($)')
        else:
            ax_treemap.text(0.5, 0.5, "No valid data for this date range", ha='center', va='center')
        
        fig.canvas.draw_idle()
    
    # Create the range slider
    slider_ax = fig.add_axes([0.2, 0.05, 0.6, 0.03])
    slider = RangeSlider(
        ax=slider_ax,
        label='Date Range',
        valmin=mdates.date2num(min_date),
        valmax=mdates.date2num(max_date),
        valinit=(mdates.date2num(min_date), mdates.date2num(max_date)),
        valstep=mdates.date2num(data.index[1]) - mdates.date2num(data.index[0])
    )
    
    # Set the slider's format to display dates
    slider.valtext.set_text(f'{min_date.strftime("%Y-%m-%d")} - {max_date.strftime("%Y-%m-%d")}')
    
    # Update function for the slider text
    def update_slider_text(val):
        start_date = pd.Timestamp(mdates.num2date(val[0])).tz_localize(None)
        end_date = pd.Timestamp(mdates.num2date(val[1])).tz_localize(None)
        slider.valtext.set_text(f'{start_date.strftime("%Y-%m-%d")} - {end_date.strftime("%Y-%m-%d")}')
    
    slider.on_changed(update_slider_text)
    
    # Connect the update function to the slider
    slider.on_changed(lambda val: update_treemap(val[0], val[1]))
    
    # Initial plot
    update_treemap(mdates.date2num(min_date), mdates.date2num(max_date))
    
    # Adjust layout
    plt.tight_layout()
    
    # Embed the plot into tkinter
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)
    
    # Keep a reference to the slider to prevent it from being garbage collected
    canvas.slider = slider


def show_daily_details_table():

    # Clear the plot frame
    for widget in plot_frame.winfo_children():
        widget.destroy()

    # Create a frame for the date selection
    date_frame = ttk.Frame(plot_frame)
    date_frame.pack(pady=10)

    # Add a date entry widget
    date_label = ttk.Label(date_frame, text="Select Date:")
    date_label.pack(side=tk.LEFT, padx=5)
    date_entry = DateEntry(date_frame, bootstyle="primary")
    date_entry.pack(side=tk.LEFT)

    # Add a button to update the table
    update_button = ttk.Button(date_frame, text="Update Table", command=lambda: update_table(date_entry.get()))
    update_button.pack(side=tk.LEFT, padx=5)

    # Create a frame for the table
    table_frame = ttk.Frame(plot_frame)
    table_frame.pack(expand=tk.YES, fill=tk.BOTH, padx=10, pady=10)

    # Create a label for total portfolio value
    total_value_label = ttk.Label(plot_frame, text="Total Portfolio Value: $0", font=("TkDefaultFont", 12, "bold"))
    total_value_label.pack(pady=10)

    # Function to update the table based on the selected date
    def update_table(selected_date):
        selected_date = pd.to_datetime(selected_date).date()

        # Clear existing table
        for widget in table_frame.winfo_children():
            widget.destroy()

        # Prepare data for the table
        table_data = []
        total_value = 0

        for ticker, df in ticker_dfs.items():
            if selected_date in df.index:
                row_data = df.loc[selected_date].to_dict()
                row_data['Ticker'] = ticker
                table_data.append(row_data)
                total_value += row_data.get('Market Value (With Dividends)', 0)

        if not table_data:
            ttk.Label(table_frame, text="No data available for the selected date.").pack()
            return

        # Create column names (use the keys from the first row of data)
        columns = ['Ticker'] + [col for col in table_data[0].keys() if col != 'Ticker']

        # Create the table using Treeview
        tree = ttk.Treeview(table_frame, columns=columns, show='headings')

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center')

        for row in table_data:
            tree.insert('', tk.END, values=[row[col] for col in columns])

        tree.pack(expand=tk.YES, fill=tk.BOTH)

        # Update total portfolio value label
        total_value_label.config(text=f"Total Portfolio Value: ${total_value:,.2f}")

    # Initial table update
    update_table(date_entry.get())

def show_daily_details_table():

    # Clear the plot frame
    for widget in plot_frame.winfo_children():
        widget.destroy()

    date_frame = ttk.Frame(plot_frame)
    date_frame.pack(pady=10)

    date_label = ttk.Label(date_frame, text="Select Date:")
    date_label.pack(side=tk.LEFT, padx=5)
    date_entry = DateEntry(date_frame)
    date_entry.pack(side=tk.LEFT)

    update_button = ttk.Button(date_frame, text="Update Table", command=lambda: update_table(date_entry.get()))
    update_button.pack(side=tk.LEFT, padx=5)

    decimal_places_frame = ttk.Frame(plot_frame)
    decimal_places_frame.pack(pady=10)

    decimal_places_label = ttk.Label(decimal_places_frame, text="Decimal Places:")
    decimal_places_label.pack(side=tk.LEFT, padx=5)
    decimal_places_entry = ttk.Entry(decimal_places_frame, width=5)
    decimal_places_entry.insert(0, "2")
    decimal_places_entry.pack(side=tk.LEFT)

    table_frame = ttk.Frame(plot_frame)
    table_frame.pack(expand=tk.YES, fill=tk.BOTH, padx=10, pady=10)

    total_value_label = ttk.Label(plot_frame, text="Total Portfolio Value: $0", font=("TkDefaultFont", 12, "bold"))
    total_value_label.pack(pady=10)

    def update_table(selected_date):
        selected_date = pd.to_datetime(selected_date).strftime('%Y-%m-%d')
        decimal_places = int(decimal_places_entry.get())

        for widget in table_frame.winfo_children():
            widget.destroy()

        table_data = []
        total_value = 0

        for ticker, df in ticker_dfs.items():
            filtered_df = df[df['Trade Date'] == selected_date]
            if not filtered_df.empty:
                for _, row in filtered_df.iterrows():
                    row_data = row.to_dict()
                    row_data['Ticker'] = ticker
                    table_data.append(row_data)
                    total_value += row_data.get('Market Value (With Dividends)', 0)

        if not table_data:
            ttk.Label(table_frame, text="No data available for the selected date.").pack()
            return

        # Exclude dividends and dividend units remainder columns
        actual_columns = [col for col in table_data[0].keys() if col not in ['Ticker', 'Trade Date', 'Dividends', 'Dividend Units Remainder']]
        columns = ['Ticker'] + actual_columns

        # Define a mapping of actual column names to display names
        column_names = {
            'Ticker': 'Stock Ticker',
            'Price' : 'Last Close Price',
            'Cumulative Transaction Value': 'Total Investment Spend',
            'Cumulative Quantity': 'Units Owned (Purchased)',
            'Cumulative Quantity (With Dividends)': 'Units Owned (Dividends Reinvested)',
            'Market Value (Without Dividends)': 'Market Value of Units Purchased',
            'Market Value (With Dividends)': 'Market Value of Position (Dividends Reinvested)'
        }

        tree = ttk.Treeview(table_frame, columns=columns, show='headings')

        # Create a dictionary to hold max length for each column
        max_lengths = {col: len(column_names.get(col, col)) for col in columns}

        for col in columns:
            tree.heading(col, text=column_names.get(col, col))  # Use the display name from the mapping
            tree.column(col, anchor='center')

        for row in table_data:
            row_values = []
            for col in columns:
                value = row.get(col, '')
                if isinstance(value, (int, float)):
                    value = f"{value:.{decimal_places}f}"
                row_values.append(value)
                # Update max length if current value is longer
                max_lengths[col] = max(max_lengths[col], len(str(value)))

            tree.insert('', tk.END, values=row_values)

        # Set the column width based on the maximum length of the content
        for col in columns:
            tree.column(col, width=max_lengths[col] * 10)  # Multiply by a factor to give some padding

        tree.pack(expand=tk.YES, fill=tk.BOTH)

        total_value_label.config(text=f"Total Portfolio Value: ${total_value:,.{decimal_places}f}")


    update_table(date_entry.get())


# Initialize tkinter GUI
root = tk.Tk()
root.title("Portfolio Performance")
sv_ttk.set_theme("dark")  # Apply the theme to the root window
root.withdraw()  # Hide the main window initially

portfolios = [f for f in os.listdir("portfolios") if f.endswith(".pkl")]

if portfolios:
    # Prompt to select portfolio at startup
    selected_portfolio = select_portfolio()
else:
    initial_window = new_user()
    root.wait_window(initial_window)  # Wait for the initial window to be closed
    selected_portfolio = select_portfolio()

if selected_portfolio:
    sv_ttk.set_theme("dark")
    portfolio_df, ticker_dfs = load_selected_portfolio(selected_portfolio)
    root.deiconify()  # Show the main window once the portfolio is selected

    # Main grid layout for the GUI
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=3)

    # Frame for the plot (make it resizable)
    plot_frame = ttk.Frame(root)
    plot_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')  # Allow resizing

    # Create a new figure for the plot
    plt.figure(figsize=(15, 7))

    # Plot initial empty plot
    plt.plot([], [], linewidth=2)  # Empty plot for initialization
    plt.xlabel('Trade Date')
    plt.ylabel('Portfolio Performance')
    plt.title('Overall Portfolio Performance')

    # Embed the plot into tkinter (allow resizing)
    canvas = FigureCanvasTkAgg(plt.gcf(), master=plot_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Frame for ticker selection
    selection_frame = ttk.LabelFrame(root, text="Stock Selection", padding=(20, 10))
    selection_frame.grid(row=0, column=0, padx=10, pady=10, sticky='n')  # Place to the left of the plot

    # Initialize the ticker selection
    ticker_vars = {}
    for i, ticker in enumerate(ticker_dfs.keys()):
        ticker_vars[ticker] = tk.IntVar()
        ttk.Checkbutton(selection_frame, text=ticker, variable=ticker_vars[ticker]).grid(row=i, column=0, sticky='w')

    # Button to select all tickers
    select_all_button = ttk.Button(selection_frame, text="Select All", command=select_all)
    select_all_button.grid(row=len(ticker_dfs), column=0, pady=5, sticky='w')

    # Button to select none of the tickers
    select_none_button = ttk.Button(selection_frame, text="Select None", command=select_none)
    select_none_button.grid(row=len(ticker_dfs) + 1, column=0, pady=5, sticky='w')

    # Button to plot selected tickers individually
    plot_individual_button = ttk.Button(root, text="Show Individually", style="Accent.TButton", command=lambda: plot_selected('individual'))
    plot_individual_button.grid(row=1, column=0, pady=10, padx=10, sticky='w')

    # Button to plot aggregated portfolio performance
    plot_aggregate_button = ttk.Button(root, text="Show Aggregate", style="Accent.TButton", command=lambda: plot_selected('aggregate'))
    plot_aggregate_button.grid(row=1, column=1, pady=10, padx=10, sticky='e')

    plot_individual_button.config(command=lambda: plot_selected('individual'))
    plot_aggregate_button.config(command=lambda: plot_selected('aggregate'))

    # Create a menu bar
    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)

    # Create the 'Plot' menu
    plot_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Plot Options", menu=plot_menu)

    # Variable to store selected plot type
    selected_plot_type = tk.StringVar(value="Profit/Loss")

    # Create the 'Data' menu
    data_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Data", menu=data_menu)
    data_menu.add_command(label="Get Template", command=get_template)
    data_menu.add_command(label="Load New Portfolio Data", command = load_new_portfolio_data)
    data_menu.add_command(label="Select Portfolio", command= select_portfolio)

    # Add menu items to the 'Plot' menu
    plot_menu.add_radiobutton(label="Value of Portfolio", variable=selected_plot_type, value="Value of Portfolio")
    plot_menu.add_radiobutton(label="Dividend Performance", variable=selected_plot_type, value="Dividend Performance")
    plot_menu.add_radiobutton(label="Profit/Loss", variable=selected_plot_type, value="Profit/Loss")
    plot_menu.add_radiobutton(label="Stacked Area Chart", variable=selected_plot_type, value="Stacked Area Chart")
    plot_menu.add_radiobutton(label="Portfolio Distribution (Pie Chart)", variable=selected_plot_type, value="Portfolio Distribution")
    plot_menu.add_radiobutton(label="Portfolio Treemap", variable=selected_plot_type, value="Portfolio Treemap")


    # Create the "Statistics" menu
    stats_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Statistics", menu=stats_menu)
    stats_menu.add_command(label="Show Statistics", command=show_statistics_panel)
    stats_menu.add_command(label="Daily Details Table", command=show_daily_details_table)

    # Run the tkinter main loop
    root.mainloop()
else:
    root.destroy()  # Close the application if no portfolio was selected or created