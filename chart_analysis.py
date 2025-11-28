#url = f"https://admin.stocksemoji.com/flavours//BSENSEPriceHistorical/{index_code}/d/365/"

import base64
from openai import OpenAI
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta,date,time as dt_time
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from pymongo import MongoClient
import requests
import json

st.set_page_config(
    layout="wide",  # 👈 enables wide mode
    page_title="Stock Analyzer",
    page_icon="📈"
)

api_key = st.secrets["OPENAI_API_KEY"]
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
            st.rerun()
        else:
            st.error("❌ Incorrect username or password")
    return False


# Call the blocker right at the top of your script
if not login_block():
    st.stop()

yesterday = date.today() - timedelta(days=1)

json_schema = {
    "format": {
        "type": "json_schema",
        "name": "stock_analysis",
        "schema": {
            "type": "object",
            "properties": {
                "date_ran": {
                    "type": "string",
                    "description": "Date when the analysis was run"
                },
                "stock": {"type": "string"},
                "section_1_current_outlook": {
                    "type": "object",
                    "properties": {
                        "stage": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "integer","description":"Stage 1 – Base Building (Accumulation): Stock trades sideways in a range after a decline, volume is light, institutions quietly accumulate.Stage 2 – Advancing (Uptrend): Breakout from Stage 1 base, stock trends higher with strong price and volume action. Best stage for buying.Stage 3 – Topping (Distribution): Stock stops making progress, shows choppy sideways action near highs, distribution by institutions begins.Stage 4 – Declining (Downtrend): Breakdown from Stage 3, prolonged downtrend with lower highs/lows, heavy selling pressure."},
                                "comment": {"type": "string"}
                            },
                            "required": ["value", "comment"],
                            "additionalProperties": False
                        },
                        "base": {"type": "string"},
                        
                        "chart_pattern": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": f"""Exact pattern name:
                                                                                Step Chart – Shows price moving in distinct horizontal and vertical steps, reflecting consolidation phases followed by sharp directional moves.

                                                                                Flag – A short consolidation channel after a strong trend, signaling continuation once the flag breaks in the trend’s direction.
                                                                                
                                                                                Pennant – A small symmetrical triangle following a sharp price move, indicating trend continuation after a brief pause.
                                                                                
                                                                                1-2-3 Pattern – A three-point reversal or continuation structure that marks a trend change when the third point confirms breakout.
                                                                                
                                                                                Cup and Handle – A rounded “U” shape followed by a small dip, suggesting accumulation before a bullish breakout.
                                                                                
                                                                                Triangle – Converging trendlines showing price compression, typically resolving in a breakout aligned with the prevailing trend.
                                                                                
                                                                                Low Cheat – An early breakout entry setup within a base, entered near support before full pattern confirmation.
                                                                                
                                                                                VCP (Volatility Contraction Pattern) – Successive tighter price contractions signaling institutional accumulation and a potential breakout.
                                                                                
                                                                                Inverted Head and Shoulders – A three-trough reversal formation where the middle trough is deepest, signaling a bullish reversal.
                                                                                
                                                                                Engulfing / Reversal – A candlestick pattern where a large candle fully engulfs the previous one, indicating a possible trend reversal."""},
                                "comment": {"type": "string"}
                            },
                            "required": ["value", "comment"],
                            "additionalProperties": False
                        },
                        "overall_outlook_trend": {"type": "string"},
                        "technical_score": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "number"},
                                "reason": {"type": "string"}
                            },
                            "required": ["value", "reason"],
                            "additionalProperties": False
                        },
                        "risk_score": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "number"},
                                "reason": {"type": "string"}
                            },
                            "required": ["value", "reason"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["stage", "base","chart_pattern","overall_outlook_trend", "technical_score", "risk_score"],
                    "additionalProperties": False
                },
                "section_2_trend_horizon_buckets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "horizon": {"type": "string", "enum": ["Short", "Medium", "Long"]},
                            "status": {"type": "string"},
                            "key_metrics": {"type": "string"},
                            "comment": {"type": "string"},
                            "final_verdict": {
                                "type": "object",
                                "properties": {
                                    # "if_holding": {"type": "string", "enum": ["Hold", "Buy", "Sell","Reduce","Increase"], "description": "If quite bad technically suggest a Sell else Hold.If looking good and consolidating Increase"},
                                    # "if_not_holding": {"type": "string", "enum": ["Wait", "Buy","Avoid"]}
                                    
                                  "if_holding": {
                                    "type": "string",
                                    "enum": ["Hold", "Buy", "Sell", "Reduce", "Increase"],
                                    "description": "Action for an investor who ALREADY owns the stock.\n\
                                • Hold     – Maintain position when technicals are neutral or trendless.\n\
                                • Buy      – Add aggressively because a strong new breakout or catalyst is in play.The stock is in early stage 2. For all short, medium,long term\n\
                                • Sell     – Exit completely when technical picture is clearly bearish or a major breakdown occurs.\n\
                                • Reduce   – Trim part of the position to lock gains or control risk when momentum stalls or resistance looms or is extremely extended.\n\
                                • Increase – Add modestly (scale‑in) when the stock is basing constructively or breaking out on rising volume.\n\
                                This should be decided based on short medium long horizon. Basis on your final verdict decide Hold, buy,sell,reduce,increase"
                                  },
                                
                                  "if_not_holding": {
                                    "type": "string",
                                    "enum": ["Wait", "Buy", "Avoid"],
                                    "description": "Action for an investor who DOES NOT own the stock.\n\
                                • Wait  – Stay on the sidelines until a cleaner technical entry appears.\n\
                                • Buy   – Initiate a position now because the setup is strong and risk‑reward is attractive. Stock is in early stage 2. If good technicals buy for medium and long\n\
                                • Avoid – Skip the stock altogether due to weak technicals, excessive volatility, or poor liquidity.\n\
                                 This should be decided based on short medium long horizon. Basis on your final verdict decide Hold, buy,sell,reduce,increase"
                                  }

                                },
                                "required": ["if_holding", "if_not_holding"],
                                "additionalProperties": False
                            }
                        },
                        "required": ["horizon","status","key_metrics","comment", "final_verdict"],
                        "additionalProperties": False
                    }
                },
                "section_3_trade_setup_ideas": {
                  "type": "object",
                  "properties": {
                    "short_term": {
                      "type": "array",
                      "description": "Short-term trades (1- 10 days). Can be left blank if no good setup. Trade entry can be on a breakout as well as pull back. Dont just restrict to pull back",
                      "items": {
                        "type": "object",
                        "properties": {
                          "trigger": { "type": "string" },
                          "entry": { "type": "number" },
                          "stop": { "type": "number" },
                          "target": {
                            "type": "string",
                            "description": "Leave blank if it looks a good trade and no profit booking needed"
                          },
                          "rr": { "type": "number" },
                          "confidence": { "type": "string" },
                          "execution_detail": {
                            "type": "string",
                            "description": "Detailed execution plan"
                          },
                          "time_horizon": { "type": "string", "enum": ["Short"] }
                        },
                        "required": ["trigger", "entry", "stop", "target", "rr", "confidence", "execution_detail", "time_horizon"],
                        "additionalProperties": False
                      }
                    },
                    "mid_term": {
                      "type": "array",
                      "description": "Mid-term trades (typically 1- 3 months).",
                      "items": {
                        "type": "object",
                        "properties": {
                          "trigger": { "type": "string" },
                          "entry": { "type": "number" },
                          "stop": { "type": "number" },
                          "target": {
                            "type": "string",
                            "description": "Leave blank if it looks a good trade and no profit booking needed"
                          },
                          "rr": { "type": "number" },
                          "confidence": { "type": "string" },
                          "execution_detail": {
                            "type": "string",
                            "description": "Detailed execution plan"
                          },
                          "time_horizon": { "type": "string", "enum": ["Mid"] }
                        },
                        "required": ["trigger", "entry", "stop", "target", "rr", "confidence", "execution_detail", "time_horizon"],
                        "additionalProperties": False
                      }
                    },
                    "long_term": {
                      "type": "array",
                      "description": "Long-term trades (typically months or more).",
                      "items": {
                        "type": "object",
                        "properties": {
                          "trigger": { "type": "string" },
                          "entry": { "type": "number" },
                          "stop": { "type": "number" },
                          "target": {
                            "type": "string",
                            "description": "Leave blank if it looks a good trade and no profit booking needed"
                          },
                          "rr": { "type": "number" },
                          "confidence": { "type": "string" },
                          "execution_detail": {
                            "type": "string",
                            "description": "Detailed execution plan"
                          },
                          "time_horizon": { "type": "string", "enum": ["Long"] }
                        },
                        "required": ["trigger", "entry", "stop", "target", "rr", "confidence", "execution_detail", "time_horizon"],
                        "additionalProperties": False
                      }
                    }
                  },
                  "required": ["short_term", "mid_term", "long_term"],
                  "additionalProperties": False
                },
                "section_3.1_trade_setup_fno_ideas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                         "description": "Give me fno strategies atleast 2",
                        "properties": {
                            "Option strategy type": {"type": "string"},
                            "entry": {"type": "string"},
                            "stop": {"type": "string"},
                            "target": {"type": "string"},
                            "rr": {"type": "string"},
                            "payoff": {"type": "string"},
                            
                            "confidence": {"type": "string"},
                            "execution_detail": {"type": "string"},
                            "time_horizon": {"type": "string"}
                        },
                        "required": ["Option strategy type", "entry", "stop", "target", "rr", "payoff","confidence", "execution_detail", "time_horizon"],
                        "additionalProperties": False
                    }
                },
                
                "section_4_support_resistance": {
                    "type": "object",
                    "properties": {
                        "support": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "level": {"type": "string","description":"A close range of number like 100-101"},
                                    "note": {"type": "string"}
                                },
                                "required": ["level", "note"],
                                "additionalProperties": False
                            }
                        },
                        "resistance": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "level": {"type": "number","description":"A close range of number like 100-101"},
                                    "note": {"type": "string"}
                                },
                                "required": ["level", "note"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["support", "resistance"],
                    "additionalProperties": False
                },
                "section_5_price_volume_action": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "section_6_index_correlation": {
                  "type": "object",
                  "properties": {
                    "index_name": {
                      "type": "string",
                      "description": "The name of the index relevant to the stock's market cap type (e.g., NIFTY, MIDCAP100)."
                    },
                    "index_ema_20": {
                      "type": "number",
                      "description": "20-day EMA of the mapped index."
                    },
                    "index_ema_50": {
                      "type": "number",
                      "description": "50-day EMA of the mapped index."
                    },
                    "index_ema_100": {
                      "type": "number",
                      "description": "100-day EMA of the mapped index."
                    },
                    "correlation_type": {
                  "type": "string",
                  "enum": ["Leading", "Lagging", "In Sync", "Decoupled", "Converging", "Diverging"],
                  "description": "One-word summary of how the stock is behaving relative to the index."
                    },
                    "correlation_comment": {
                      "type": "string",
                      "description": "Interpretation of how the stock's trend aligns or diverges from the index trend (e.g., 'Stock is outperforming index', 'Tracking index closely', etc.)"
                    },
                      "Correlation_Factor": {
                      "type": "number",
                      "description": "Correlation between index and stock"
                    },
                  },
                  "required": ["index_name", "index_ema_20", "index_ema_50", "index_ema_100","correlation_type","correlation_comment","Correlation_Factor"],
                    "additionalProperties": False
                },
                "section_7_extended_moves": {
                  "type": "object",
                  "properties": {
                    "is_extended": {
                      "type": "boolean",
                      "description": "True if the stock is significantly extended from key moving averages.'10% from 10 SMA, 20% from 20 EMA, 50% from 50 SMA'"
                    },
                    "extension_description": {
                      "type": "string",
                      "description": "Describes the degree of extension, e.g., '10% from 10 SMA, 20% from 20 EMA, 50% from 50 SMA'."
                    },
                    "profit_booking_note": {
                      "type": "string",
                      "description": "Suggested action if holding, such as partial or full profit booking based on extension level."
                    }
       
                  },
                  "required": ["is_extended", "extension_description", "profit_booking_note"],
                  "additionalProperties": False
                },
                "section_8_distance_from_breakout": {
                  "type": "object",
                  "properties": {
                    "distance_from_breakout_perc": {
                      "type": "number",
                      "description": "Percentage gain from the last confirmed breakout level. Positive if above breakout.It should be a major breakout. Make sure calculation is correct"
                    },
                    "breakout_level": {
                      "type": "number",
                      "description": "The price at which the last attempted breakout occurred."
                    },
                    "current_price": {
                      "type": "number",
                      "description": "The current market price of the stock."
                    },
                    "breakout_date": {
                      "type": "string",
                     
                      "description": "The time period when last attempted breakout happened."
                    },
                    "profit_booking_note": {
                      "type": "string",
                      "description": "Suggested action depending on how far the stock has run from breakout, e.g., 'Trail stop-loss' or 'Consider partial exit'."
                    }
                  },
                  "required": ["distance_from_breakout_perc", "breakout_level", "current_price", "breakout_date", "profit_booking_note"],
                  "additionalProperties": False
                },
                
                "section_9_detailed_tech_rating": {
                    "type": "object",
                    "properties": {
                        "technical_rating_overall": {"type": "number"},
                        "factors": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "score": {"type": "number"},
                                    "comment": {"type": "string"}
                                },
                                "required": ["name", "score", "comment"],
                                "additionalProperties": False
                            }
                        },
                        "total_weighted_avg": {"type": "number"}
                    },
                    "required": ["technical_rating_overall", "factors", "total_weighted_avg"],
                    "additionalProperties": False
                },
                "section_10_overall_conclusion": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                
                 
                
            },
            "required": ["date_ran","stock", "section_1_current_outlook", "section_2_trend_horizon_buckets", "section_3_trade_setup_ideas","section_3.1_trade_setup_fno_ideas", "section_4_support_resistance", "section_5_price_volume_action","section_6_index_correlation","section_7_extended_moves","section_8_distance_from_breakout", "section_9_detailed_tech_rating","section_10_overall_conclusion"],
            "additionalProperties": False
        },
        "strict":True
    }
}



with st.form("stock_form"):
    ticker = st.text_input("Enter NSE Symbol (e.g., TCS, INFY)", "MCX")
    submit = st.form_submit_button("Fetch Data")

if submit:
    ticker = ticker.strip().upper()


    start_time=datetime.now()
    client_mongo = MongoClient("mongodb+srv://prachi:Akash5555@stockgpt.fryqpbi.mongodb.net/")  # update if needed
    db = client_mongo["CAG_CHATBOT"]
    collection = db["CompaniesDetails"]
    index_map = {
    "Large Cap": "NIFTY",
    "Mid Cap": "NMIDCAP150",
    "Small Cap": "SMALLCA250"
    }

    # Step 3: Precompute index EMAs
    index_ema_map = {}
    
    for mcaptype, index_symbol in index_map.items():
        doc_index = collection.find_one({"nsesymbol": index_symbol.upper()})
        if doc_index:
            index_code = doc_index.get("co_code")
        url = f"https://admin.stocksemoji.com/flavours/BSENSEPriceHistorical/nse/{index_code}/d/365"
        resp = requests.get(url)
    
        if resp.status_code != 200:
            print(f"❌ EMA fetch failed for {index_symbol}")
            continue
    
        df = pd.DataFrame(resp.json()["data"]).sort_values("Date")
        #df.columns = [col.upper() for col in df.columns]
    
        index_ema_map[mcaptype] = {
            "Index": index_symbol,
            "EMA_20": round(df["Close"].ewm(span=20, adjust=False).mean().iloc[-1], 2),
            "EMA_50": round(df["Close"].ewm(span=50, adjust=False).mean().iloc[-1], 2),
            "EMA_100": round(df["Close"].ewm(span=100, adjust=False).mean().iloc[-1], 2)
        }

    
    # Input NSE symbol
    nse_symbol = ticker
    doc = collection.find_one({"nsesymbol": ticker.upper()})  # ensure case-insensitive match if needed

    if doc:
        co_code = doc.get("co_code")
        print(f"co_code for {ticker}: {co_code}")
        url = f"https://admin.stocksemoji.com/flavours/BSENSEPriceHistorical/nse/{co_code}/d/365"
        response = requests.get(url)
        mcaptype = doc.get("mcaptype")  # Default to Large Cap
        index_ema = index_ema_map.get(mcaptype)

        if response.status_code == 200:
            data = response.json()
            #print("Price Data:", data)
        url_dv=f"https://admin.stocksemoji.com/api/cmot/DeliverableVolume/NSE/{co_code}/H/d/110"
        response_dv = requests.get(url_dv)
        # if response_dv.status_code == 200:
        #     data_dv = response_dv.json()
        # else:
        #     print("API Error:", response.status_code, response.text)
    else:
        print("No company found with given NSE symbol.")
        
        
    df = pd.DataFrame(data["data"])

    df = df.sort_values('Date')

    # Compute DMA values
    dma_9 = round(df['Close'].rolling(window=9).mean().iloc[-1], 2)
    dma_20 = round(df['Close'].rolling(window=20).mean().iloc[-1], 2)
    dma_50 = round(df['Close'].rolling(window=50).mean().iloc[-1], 2)
    dma_100 = round(df['Close'].rolling(window=100).mean().iloc[-1], 2)
    week_52_high= df['HIGH'].max()
    week_52_low= df['LOW'].min()
    current_price = df['Close'].iloc[-1]
    df['NSE_SYMBOL'] = ticker
    df['Date'] = pd.to_datetime(df['Date'])
    today = df['Date'].max() 

    df = df[df['Date'] >= today - timedelta(days=150)]
    # df_dv=pd.DataFrame(data_dv["data"])
    # df_dv['tr_date'] = pd.to_datetime(df_dv['tr_date']).dt.strftime('%Y-%m-%d')
    # df_dv['tr_date']=df_dv['tr_date'].astype(str)
    # df_dv.rename(columns={'tr_date': 'Date'}, inplace=True)
    df=df[['NSE_SYMBOL','Date','OPEN','HIGH','LOW','Close','Volume']]
    # data
    print(df.head())
    df['Date']=df['Date'].astype(str)

    st.write(ticker)

    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.7, 0.3], vertical_spacing=0.05,
        specs=[[{"type": "scatter"}], [{"type": "bar"}]]
    )
    
    # Close Price Line Chart
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Close'],
        mode='lines', name='Close Price',
        line=dict(color='blue')
    ), row=1, col=1)
    
    # Volume Bar Chart
    fig.add_trace(go.Bar(
        x=df['Date'], y=df['Volume'],
        name='Volume',
        marker_color='green'
    ), row=2, col=1)
    
    # Update layout to treat Date as category (removes gaps)
    fig.update_layout(
        title="Stock Close Price and Volume",
        height=600,
        showlegend=False,
        xaxis=dict(type='category'),
        xaxis2=dict(type='category'),
        yaxis1_title="Close Price",
        yaxis2_title="Volume",
        xaxis2_title="Date"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    df['Date'] = df['Date'].astype(str)
    #df=df.merge(df_dv[['Date','DevlieryVolume']],how='left',on='Date')
    
    # st.dataframe(df)
    # text_data = df.to_string(index=False)
    if not df.empty:
        text_data = df.to_json(orient='records', lines=True)

        response = client.responses.create(
        model="gpt-4.1",
        input=[
            {"role": "system", "content": f"""You are a technical chart analyst. You will be provided ohlcv data of a stock of 100 days and as a pro chartist you need to identify stages, chart patterns and trade setup.
                                    These are the stage rules
                                    Stage 1 – Base Building (Accumulation): Stock trades sideways in a range after a decline, volume is light, institutions quietly accumulate.Stage 2 – Advancing (Uptrend): Breakout from Stage 1 base, stock trends higher with strong price and volume action. Best stage for buying.Stage 3 – Topping (Distribution): Stock stops making progress, shows choppy sideways action near highs, distribution by institutions begins.Stage 4 – Declining (Downtrend): Breakdown from Stage 3, prolonged downtrend with lower highs/lows, heavy selling pressure.
                                     Do not reinvent data. Solely focus on data provided. Make sure to look how much correction has been made from top to look at stages and rating.

                                     For trade setups the trade can be taken even on a clean breakout. Not necessary all entries to be taken on pull back.
             """},
            {
                "role": "user",
                "content": f"""you are a techincal analyst based on the ohlcv data and delivery volume of a stock {text_data} provide the answer
             
                
               
                You are also given teh EMA for the Index assocaited with the stock
                     Market Cap Type: {mcaptype}
                    " Index: {index_ema['Index']}
                    "EMA-20: {index_ema['EMA_20']}, EMA-50: {index_ema['EMA_50']}, EMA-100: {index_ema['EMA_100']}

                    date_ran={yesterday}
          
                 Ensure the output is highly structured, uses markdown formatting
                Avoid speculation; use only what can be inferred from technical indicators and price-volume structure.

                Decide on `if_holding` and `if_not_holding` based on technical structure. Apply this with variations for both short term ,mid term, long term horizon trend.
                Dont act conservative and always give Hold and wait.

                • Hold     – Maintain position when technicals are neutral or trendless.\n\
                • Buy      – Add aggressively because a strong new breakout or catalyst is in play.The stock is in early stage 2\n\
                • Sell     – Exit completely when technical picture is clearly bearish or a major breakdown occurs.\n\
                • Reduce   – Trim part of the position to lock gains or control risk when momentum stalls or resistance looms or is extremely extended.\n\
                • Increase – Add modestly (scale‑in) when the stock is basing constructively or breaking out on rising volume."

                When making your analysis dont just go by numbers but by % change.
              
                """
            },
        ],
            text=json_schema
        )
        output_text=response.output_text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(output_text)

        collection_ta=db['technical_summary']
        collection_ta.replace_one(
            {"stock": ticker},  # match on stock
            data,
            upsert=True             # insert if doesn't exist
        )

        data["section_11_fact_metrics"] = {
            "current_price": {"value": current_price},
            "week_52_high": {"value": week_52_high},
            "week_52_low": {"value": week_52_low},
            "dma_9": {"value": dma_9},
            "dma_20": {"value": dma_20},
            "dma_50": {"value": dma_50},
            "dma_100": {"value": dma_100}
        }
        

        def render_section_title(title):
            return f"<h2 style='color:#2e6f9e;border-bottom:2px solid #ccc;padding-bottom:4px;margin-top:20px'>{title}</h2>"
        
        def render_key_value(label, value):
            return f"<p><strong>{label}:</strong> {value}</p>"
        
        def render_list(items):
            return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"
        
        def render_table(rows):
            if not rows: return ""
            headers = rows[0].keys()
            table = "<table style='width:100%;border-collapse:collapse;border:1px solid #ccc'>"
            table += "<tr>" + "".join(f"<th style='border:1px solid #ccc;padding:6px'>{h}</th>" for h in headers) + "</tr>"
            for row in rows:
                table += "<tr>" + "".join(f"<td style='border:1px solid #ccc;padding:6px'>{row[h]}</td>" for h in headers) + "</tr>"
            table += "</table>"
            return table
        
        
        # ---------- 3. Compose the HTML content ----------
        def render_section_title(title):
            return f"<h2 style='color:#2e6f9e;border-bottom:2px solid #ccc;padding-bottom:4px;margin-top:20px'>{title}</h2>"

        def render_key_value(label, value):
            return f"<p><strong>{label}:</strong> {value}</p>"
        
        def render_list(items):
            return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"
        
        def render_table(rows):
            if not rows: return ""
            headers = rows[0].keys()
            table = "<table style='width:100%;border-collapse:collapse;border:1px solid #ccc'>"
            table += "<tr>" + "".join(f"<th style='border:1px solid #ccc;padding:6px'>{h}</th>" for h in headers) + "</tr>"
            for row in rows:
                table += "<tr>" + "".join(f"<td style='border:1px solid #ccc;padding:6px'>{row[h]}</td>" for h in headers) + "</tr>"
            table += "</table>"
            return table
        
        # ---------- 3. Compose the HTML content ----------
        html = f"<html><head><meta charset='utf-8'><title>Technical Report - {data['stock']}</title></head><body style='font-family:Segoe UI;padding:20px'>"
        
        html += f"<h1>Technical Analysis Report: {data['stock']}</h1>"
        
        # Section 1
        s1 = data["section_1_current_outlook"]
        html += render_section_title("1. Current Outlook")
        html += render_key_value("Stage", f"{s1['stage']['value']} - {s1['stage']['comment']}")
        html += render_key_value("Base", s1['base'])
        html += render_key_value("Chart Pattern", f"{s1['chart_pattern']['value']} – {s1['chart_pattern']['comment']}")
        html += render_key_value("Overall Outlook/Trend", s1['overall_outlook_trend'])
        html += render_key_value("Technical Score", f"{s1['technical_score']['value']} – {s1['technical_score']['reason']}")
        html += render_key_value("Risk Score", f"{s1['risk_score']['value']} – {s1['risk_score']['reason']}")
        
        # Section 2
        html += render_section_title("2. Trend Horizons")
        trend_rows = []
        for bucket in data["section_2_trend_horizon_buckets"]:
            trend_rows.append({
                "Horizon": bucket["horizon"],
                "Status": bucket["status"],
                "Key Metrics": bucket["key_metrics"],
                "Comment": bucket["comment"],
                "If Holding": bucket["final_verdict"]["if_holding"],
                "If Not Holding": bucket["final_verdict"]["if_not_holding"]
            })
        html += render_table(trend_rows)
        
# Section 3
        html += render_section_title("3. Trade Setup Ideas")
        
        # Loop through each time horizon
        for horizon_label, horizon_title in [
            ("short_term", "🕒 Short-Term Setups"),
            ("mid_term", "📆 Mid-Term Setups"),
            ("long_term", "📅 Long-Term Setups")
        ]:
            if data["section_3_trade_setup_ideas"].get(horizon_label):
                html += render_section_title(horizon_title)
                html += render_table(data["section_3_trade_setup_ideas"][horizon_label])
            else:
                html += f"<p><i>No {horizon_title.lower()} available.</i></p>"

        
        # Section 3.1
        html += render_section_title("3.1 F&O Trade Setup Ideas")
        html += render_table(data["section_3.1_trade_setup_fno_ideas"])
        
        # Section 4
        html += render_section_title("4. Support and Resistance")
        html += "<h4>Support Levels</h4>" + render_table(data["section_4_support_resistance"]["support"])
        html += "<h4>Resistance Levels</h4>" + render_table(data["section_4_support_resistance"]["resistance"])
        
        # Section 5
        html += render_section_title("5. Price-Volume Action")
        html += render_list(data["section_5_price_volume_action"])
        
        # Section 6
        s6 = data["section_6_index_correlation"]
        html += render_section_title("6. Index Correlation")
        html += render_key_value("Index Name", s6["index_name"])
        html += render_key_value("EMA-20", s6["index_ema_20"])
        html += render_key_value("EMA-50", s6["index_ema_50"])
        html += render_key_value("EMA-100", s6["index_ema_100"])
        html += render_key_value("Correlation Type", s6["correlation_type"])
        html += render_key_value("Comment", s6["correlation_comment"])
        html += render_key_value("Correlation Factor", s6["Correlation_Factor"])
        
        
        # Section 7
        s7 = data["section_7_extended_moves"]
        html += render_section_title("7. Extended Moves")
        html += render_key_value("Is Extended", s7["is_extended"])
        html += render_key_value("Extension Description", s7["extension_description"])
        html += render_key_value("Profit Booking Note", s7["profit_booking_note"])
        
        # Section 8
        s8 = data["section_8_distance_from_breakout"]
        html += render_section_title("8. Distance from Breakout")
        html += render_key_value("Distance from Breakout (%)", s8["distance_from_breakout_perc"])
        html += render_key_value("Breakout Level", s8["breakout_level"])
        html += render_key_value("Current Price", s8["current_price"])
        html += render_key_value("Breakout Date", s8["breakout_date"])
        html += render_key_value("Profit Booking Note", s8["profit_booking_note"])
        
        # Section 9
        s9 = data["section_9_detailed_tech_rating"]
        html += render_section_title("9. Technical Rating")
        html += render_key_value("Overall Rating", s9["technical_rating_overall"])
        html += render_table(s9["factors"])
        
        # Section 10
        html += render_section_title("10. Overall Conclusion")
        html += render_list(data["section_10_overall_conclusion"])
        
        html += "</body></html>"
        # # Section 11
        # html += render_section_title("11. Scenario Map")
        
        # # Render each scenario as a structured list or table row
        # scenario_map = data.get("section_11_scenario_map", [])
        # if scenario_map:
        #     html += "<table><thead><tr><th>Direction</th><th>Condition</th><th>Delivery %</th><th>Target Zone</th><th>Action</th></tr></thead><tbody>"
        #     for scenario in scenario_map:
        #         condition_str = f"Price {scenario['price_condition']} {scenario['price_trigger']}"
        #         html += f"<tr><td>{scenario['direction'].capitalize()}</td><td>{condition_str}</td><td>{scenario['delivery_pct_threshold']}%</td><td>{scenario['target_zone']}</td><td>{scenario['action']}</td></tr>"
        #     html += "</tbody></table>"
        # else:
        #     html += "<p>No scenario map available.</p>"

        
        st.markdown(html, unsafe_allow_html=True)

        input_cost=response.usage.input_tokens*2*90/1000000
        output_cost=response.usage.output_tokens*8*90/1000000
        st.write("Input Cost :" , input_cost)

        st.write("Output Cost :" , output_cost)
        st.write("Total Cost :",input_cost+output_cost)
