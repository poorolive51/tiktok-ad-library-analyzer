import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

def parse_reach_value(reach_str):
    """
    Converts a reach string like '10K-100K' or '94K' to a numeric value.
    Ranges are converted to their midpoint.
    """
    if not reach_str:
        return 0
    
    reach_str = reach_str.upper().replace(',', '')
    
    if '-' in reach_str:
        parts = reach_str.split('-')
        min_val = parse_single_reach(parts[0])
        max_val = parse_single_reach(parts[1])
        return (min_val + max_val) / 2
    else:
        return parse_single_reach(reach_str)

def parse_single_reach(value_str):
    """Parses a single reach value string, e.g., '10K' or '1M'."""
    if 'K' in value_str:
        return float(value_str.replace('K', '')) * 1000
    elif 'M' in value_str:
        return float(value_str.replace('M', '')) * 1000000
    else:
        return float(value_str)

def parse_date(date_str):
    """Converts a date string like '20240808' to a datetime object."""
    return datetime.strptime(date_str, '%Y%m%d')

def load_and_process_ad_data(json_file_path):
    """
    Loads ad data from a JSON file and processes it into a list of dictionaries.

    Args:
        json_file_path (str): The path to the JSON data file.

    Returns:
        list: A list of dictionaries, each representing a processed ad.
    """
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    ads_data = []
    
    # Handle both single ad object and list of ads
    if isinstance(data, dict):
        data = [data]

    for i, item in enumerate(data):
        try:
            if 'data' in item: # For ad_details.py output
                ad_info = item['data']['ad']
                advertiser_info = item['data'].get('advertiser', {})
            else: # For ad_ids.json output
                ad_info = item.get('ad', item)
                advertiser_info = item.get('advertiser', {})

            # Skip if there's an error or key data is missing
            if 'error' in item and item['error']['code'] != 'ok':
                continue
            if 'id' not in ad_info or 'first_shown_date' not in ad_info:
                continue

            ad_id = ad_info['id']
            first_shown = parse_date(ad_info['first_shown_date'])
            last_shown = parse_date(ad_info['last_shown_date'])
            
            reach_info = ad_info.get('reach', {})
            global_reach = parse_reach_value(reach_info.get('unique_users_seen', '0'))
            country_reach = reach_info.get('unique_users_seen_by_country', {})
            total_country_reach = sum(parse_reach_value(v) for v in country_reach.values())
            
            reach_volume = max(global_reach, total_country_reach) # Use max of global or sum of country reach
            advertiser_name = advertiser_info.get('business_name', 'Unknown')
            
            ads_data.append({
                'ad_id': ad_id,
                'first_shown': first_shown,
                'last_shown': last_shown,
                'reach_volume': reach_volume,
                'advertiser': advertiser_name
            })
        except (KeyError, ValueError) as e:
            # print(f"Skipping malformed ad entry {i}: {e} in {item}")
            continue # Skip malformed entries
            
    return ads_data

def create_date_range_data(ads_data):
    """
    Expands ad data into daily records for a given date range.

    Args:
        ads_data (list): A list of dictionaries with ad information.

    Returns:
        pd.DataFrame: A DataFrame with one row per day for each ad.
    """
    daily_data = []
    for ad in ads_data:
        current_date = ad['first_shown']
        while current_date <= ad['last_shown']:
            daily_data.append({
                'date': current_date,
                'ad_id': ad['ad_id'],
                'reach_volume': ad['reach_volume'],
                'advertiser': ad['advertiser']
            })
            current_date += timedelta(days=1)
    return pd.DataFrame(daily_data)

def create_total_volume_plot(df):
    """
    Generates an interactive Plotly plot of total ad volume over time.

    Args:
        df (pd.DataFrame): The DataFrame containing daily ad data.

    Returns:
        plotly.graph_objects.Figure: The generated Plotly figure.
    """
    daily_totals = df.groupby('date')['reach_volume'].sum().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_totals['date'],
        y=daily_totals['reach_volume'],
        mode='lines+markers',
        name='Total Ad Volume',
        hovertemplate='<b>Date:</b> %{x|%Y-%m-%d}<br>' +
                      '<b>Total Volume:</b> %{y:,.0f}<br>' +
                      '<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': 'Crypto Ad Reach Over Time',
            'x': 0.5,
            'xanchor': 'center'
        },
        yaxis_title='Total Reach (Users)',
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        showlegend=False
    )
    
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.2)',
        showline=True,
        linewidth=1,
        linecolor='rgb(204, 204, 204)'
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.2)',
        showline=True,
        linewidth=1,
        linecolor='rgb(204, 204, 204)',
        tickformat='.0s'
    )
    
    return fig

if __name__ == '__main__':
    json_file_path = 'your_ad_data.json' # Replace with your actual JSON file path
    
    try:
        ads_data = load_and_process_ad_data(json_file_path)
        
        if ads_data:
            df_daily = create_date_range_data(ads_data)
            fig = create_total_volume_plot(df_daily)
            fig.show()
        else:
            print("No ad data was processed. Please check your JSON file.")
            
    except FileNotFoundError:
        print(f"Error: The file '{json_file_path}' was not found. Please ensure the file path is correct.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")