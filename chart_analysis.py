import base64
from openai import OpenAI
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta,date,time as dt_time
import pandas as pd

st.set_page_config(
    layout="wide",  # 👈 enables wide mode
    page_title="Stock Analyzer",
    page_icon="📈"
)

with open('D:/Chat Gpt/chatgpt_api.txt', 'r') as file:
    api_key = file.read()
# openai.api_key=api_key
client = OpenAI(api_key=api_key)

CREDENTIALS = {
    "stocks": "stocks_ib"

}

def login_block():
    """Returns True when user is authenticated."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    # ── Login form ──
    st.title("🔐 Login required")
    with st.form("login_form", clear_on_submit=False):
        user = st.text_input("Username")
        pwd  = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log in")

    if submit:
        if user in CREDENTIALS and pwd == CREDENTIALS[user]:
            st.session_state["authenticated"] = True
            st.experimental_rerun()
        else:
            st.error("❌ Incorrect username or password")
    return False


# Call the blocker right at the top of your script
if not login_block():
    st.stop()

with st.form("stock_form"):
    ticker = st.text_input("Enter NSE Symbol (e.g., TCS, INFY)", "MCX")
    submit = st.form_submit_button("Fetch Data")

if submit:
    ticker = ticker.strip().upper()
    if not ticker.endswith(".NS"):
        ticker += ".NS"

    st.write(ticker)
    all_data_today1 = yf.download(ticker, period="100d", progress=False, interval="1d")
    all_data_today1= all_data_today1.unstack(level=0)
    all_data_today1 = all_data_today1.unstack(level=0)
    all_data_today1 = all_data_today1.reset_index()
    all_data_today1.head()
    # all_data_today1['Date'] = all_data_today1['Date'].astype(str)
    all_data_today1['Date'] = pd.to_datetime(all_data_today1['Date'])
    all_data_today1=all_data_today1[all_data_today1['Date']<=(datetime.today() - timedelta(days=1))]
    all_data_today1['Date'] = all_data_today1['Date'].astype(str)
    st.write(all_data_today1.head())
    # st.dataframe(all_data_today1)
    # text_data = all_data_today1.to_string(index=False)
    if not all_data_today1.empty:
        text_data = all_data_today1.to_json(orient='records', lines=True)
        


        prompt = f"""
        You are a technical stock analyst. Perform an in-depth technical analysis of the stock: {text_data}, using OHLCV (Open, High, Low, Close, Volume) data **.

        Your response should include:

        1. A clearly written introduction specifying the date range and the purpose of comparison.
        2. A detailed table comparing both stocks on the following metrics:
        - Start and End Price (Close)
        - Absolute Price Change (%)
        - Highest and Lowest Prices
        - Maximum Drawdown (%)
        - Volatility (qualitative)
        - Volume Patterns and Liquidity
        - Notable Rallies and Corrections
        - Trend Structure
        - Support and Resistance Levels
        - Breakout Moves
        - Relative Strength
        - Volume Confirmation
        - Volatility (ATR proxy if possible)
        - Recovery Pattern
        - Sector Sensitivity
        - Overall Technical Bias
        - short term 
            -Mid Term
            -Long Term 
            - Define important bases 
        -Tell stages 1,2,3,4 
        -Mark patterns ( FLag , Pennant , Cup and Handle ) 
        -Show  major SL and Targets
        - Technical Rating
        -Risk Score


        3. A final conclusion table with these columns:
        - Ticker
        - Technical Rating (scale of 1 to 10)
        - Trend
        - Volatility
        - Relative Strength
        - Volume Confirmation
        - Liquidity
        - Final Technical Bias


        Ensure the output is highly structured, uses markdown formatting

        Avoid speculation; use only what can be inferred from technical indicators and price-volume structure.

        Stocks: 


        Now begin your analysis.
        """



        response = client.responses.create(
        model="gpt-4.1",
        input=[
            {"role": "system", "content": "You are a technical chart analyst"},
            {
                "role": "user",
                "content": prompt
            }
        ]


        )

        st.write(response.output_text)
        input_cost=response.usage.input_tokens*2*90/1000000
        output_cost=response.usage.output_tokens*8*90/1000000
        st.write("Input Cost :" , input_cost)

        st.write("Output Cost :" , output_cost)
        st.write("Total Cost :",input_cost+output_cost)
