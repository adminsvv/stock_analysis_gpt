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

json_schema = {
    "format": {
        "type": "json_schema",
        "name": "stock_analysis",
        "schema": {
            "type": "object",
            "properties": {
                "stock": {"type": "string"},
                "section_1_current_outlook": {
                    "type": "object",
                    "properties": {
                        "stage": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "integer"},
                                "comment": {"type": "string"}
                            },
                            "required": ["value", "comment"],
                            "additionalProperties": False
                        },
                        "base": {"type": "string"},
                        
                        "chart_pattern": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Exact pattern name (e.g., cup with handle,flag,penant or no pattern)."},
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
                                    "if_holding": {"type": "string", "enum": ["Hold", "Buy", "Sell"], "description": "If quite bad technically suggest a Sell else Hold."},
                                    "if_not_holding": {"type": "string", "enum": ["Wait", "Buy"], "description": "If stock is technically coming out good suggest Buy."}
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
                    "type": "array",
                    "items": {
                        "type": "object",
                         "description": "can be left blank if no good trade setup exists. Preferable 2 setups",
                        "properties": {
                            "trigger": {"type": "string"},
                            "entry": {"type": "string"},
                            "stop": {"type": "string"},
                            "target": {"type": "string"},
                            "rr": {"type": "string"},
                            "confidence": {"type": "string"},
                            "execution_detail": {"type": "string"},
                            "time_horizon": {"type": "string"}
                        },
                        "required": ["trigger", "entry", "stop", "target", "rr", "confidence", "execution_detail", "time_horizon"],
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
                                    "level": {"type": "string"},
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
                                    "level": {"type": "string"},
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
                "section_7_detailed_tech_rating": {
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
                "section_8_overall_conclusion": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["stock", "section_1_current_outlook", "section_2_trend_horizon_buckets", "section_3_trade_setup_ideas", "section_4_support_resistance", "section_5_price_volume_action", "section_7_detailed_tech_rating", "section_8_overall_conclusion"],
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
    
    # Input NSE symbol
    nse_symbol = ticker
    doc = collection.find_one({"nsesymbol": ticker.upper()})  # ensure case-insensitive match if needed

    if doc:
        co_code = doc.get("co_code")
        print(f"co_code for {ticker}: {co_code}")
        url = f"https://admin.stocksemoji.com/api/cmot/BSENSEPriceHistorical/nse/{co_code}/d/365"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            #print("Price Data:", data)
        else:
            print("API Error:", response.status_code, response.text)
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
    
    # st.dataframe(df)
    # text_data = df.to_string(index=False)
    if not df.empty:
        text_data = df.to_json(orient='records', lines=True)

        response = client.responses.create(
        model="gpt-4.1",
        input=[
            {"role": "system", "content": "You are a technical chart analyst"},
            {
                "role": "user",
                "content": f"""you are a techincal analyst based on the ohlcv data of a stock {text_data} provide the answer
                Ensure the output is highly structured, uses markdown formatting
        
                Avoid speculation; use only what can be inferred from technical indicators and price-volume structure.
                """
            },
        ],
            text=json_schema
        )
        output_text=response.output_text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(output_text)

        data["section_6_fact_metrics"] = {
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
        html += render_table(data["section_3_trade_setup_ideas"])
        
        # Section 4
        html += render_section_title("4. Support and Resistance")
        html += "<h4>Support Levels</h4>" + render_table(data["section_4_support_resistance"]["support"])
        html += "<h4>Resistance Levels</h4>" + render_table(data["section_4_support_resistance"]["resistance"])
        
        # Section 5
        html += render_section_title("5. Price-Volume Action")
        html += render_list(data["section_5_price_volume_action"])

        html += render_section_title("6. Fact Metrics")

        fact_rows = []
        for k, v in data["section_6_fact_metrics"].items():
            label = k.replace("_", " ").title()
            value = v.get("value", "N/A")
            fact_rows.append({"Metric": label, "Value": value})
        
        html += render_table(fact_rows)
        
        # Section 7
        s7 = data["section_7_detailed_tech_rating"]
        html += render_section_title("6. Technical Rating")
        html += render_key_value("Overall Rating", s7["technical_rating_overall"])
        html += render_table(s7["factors"])
        
        # Section 8
        html += render_section_title("7. Overall Conclusion")
        html += render_list(data["section_8_overall_conclusion"])
        
        html += "</body></html>"
        
        st.markdown(html, unsafe_allow_html=True)

        input_cost=response.usage.input_tokens*2*90/1000000
        output_cost=response.usage.output_tokens*8*90/1000000
        st.write("Input Cost :" , input_cost)

        st.write("Output Cost :" , output_cost)
        st.write("Total Cost :",input_cost+output_cost)
