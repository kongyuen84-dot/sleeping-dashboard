import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px  #interactive graph function
import matplotlib.dates as mdates
import plotly.express as px
import plotly.graph_objects as go
from matplotlib.ticker import MaxNLocator


#setting of the webpage
st.set_page_config(page_title="Sleeping_Data_Dashboard", layout="wide")


# check password to read the dashboard
def check_password():
    """Returns True if the user had the correct password."""

    # 1. 如果之前已經過咗關，直接放行
    if st.session_state.get("password_correct", False):
        return True

    # 2. 呢個 placeholder 用嚟登入成功後清空畫面
    login_placeholder = st.empty()

    def password_entered():
        # 比對密碼
        if st.session_state["password_input"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        
        else:
            st.session_state["password_correct"] = False

    # 3. 顯示登入介面
    with login_placeholder.container():
        st.subheader("🔐 Garmin Data Access")
        st.text_input(
            "Please enter the management password to view data", 
            type="password", 
            on_change=password_entered, 
            key="password_input"
        )
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Access Denied: Incorrect Password")
    
    return False

# 🛑 執行攔截：如果 check_password 傳回 False，就停喺度
if not check_password():
    st.stop()

st.title("My_Sleeping_Data_Dashboard")

def preprocess_data(df):
        #Prevent crashing from processing the data
        if df is None or df.empty:
                return None, 0, None

        try: 
                #define the data need to be clean
                raw_data = df.copy()

                #checking the col 
                target_cols = ["Total_sleep", "Deep_ sleep", "Light_sleep", "REM", "Avg_HR", "HRV", "Body_battery", "Score"]
                missing_cols = [c for c in  target_cols if c not in raw_data.columns]
                if missing_cols:
                        st.warning(f"Missing cols in the sheet, plz check")
                        return None, 0, None
                #all the cleaning process of the data
                cleaned_sleeping_data = raw_data.replace("NG", np.nan)
                target_sleeping_data = ["Total_sleep", "Deep_ sleep", "Light_sleep", "REM", "Avg_HR", "HRV", "Body_battery", "Score"]
                cleaned_sleeping_data = cleaned_sleeping_data.dropna(subset=target_sleeping_data)
                data_unit_change = ["Avg_HR", "HRV", "Body_battery", "Score"]

                for col in data_unit_change: #cleaning data to only numbers
                        cleaned_sleeping_data[col] = (
                        cleaned_sleeping_data[col]
                        .astype(str)
                .str.replace(r'[a-zA-Z]', '', regex=True) # 用 Regex 一次過剷走所有英文
                        .str.replace('+', '', case=False)
                        .str.strip()
                        )

                cleaned_sleeping_data[data_unit_change] = cleaned_sleeping_data[data_unit_change].apply(pd.to_numeric, errors='coerce')

                #remixed the date format
                cleaned_sleeping_data["Date"] = pd.to_datetime(cleaned_sleeping_data['Date'], 
                                                format='mixed')
                plot_date = cleaned_sleeping_data["Date"]

                #build a list of sleeping time and changing uint
                sleep_time_cols = ["Total_sleep", "Deep_ sleep", "Light_sleep", "REM"]
                cleaned_sleeping_data[sleep_time_cols] = cleaned_sleeping_data[sleep_time_cols].apply(
                lambda x: pd.to_timedelta(x, errors="coerce").dt.total_seconds() / 3600
                )

                #cal avg sleeing time
                avg_sleep_time = cleaned_sleeping_data['Total_sleep'].mean()

                #create data for graph2
                deep_pre = (cleaned_sleeping_data['Deep_ sleep'] / cleaned_sleeping_data['Total_sleep']) *100 
                light_pre = (cleaned_sleeping_data['Light_sleep'] / cleaned_sleeping_data['Total_sleep']) *100
                rem_pre =(cleaned_sleeping_data['REM'] / cleaned_sleeping_data['Total_sleep']) *100
                deep_pre_ma7 = deep_pre.rolling(window=7, min_periods=1).mean()
                light_pre_ma7 = light_pre.rolling(window=7, min_periods=1).mean()
                rem_pre_ma7 = rem_pre.rolling(window=7, min_periods=1).mean()

                #put percenatge of sleeep quality data into the df
                cleaned_sleeping_data['deep_pre'] = deep_pre
                cleaned_sleeping_data['light_pre'] = light_pre
                cleaned_sleeping_data['rem_pre'] = rem_pre
                cleaned_sleeping_data['deep_pre_ma7'] = deep_pre_ma7
                cleaned_sleeping_data['light_pre_ma7'] = light_pre_ma7
                cleaned_sleeping_data['rem_pre_ma7'] = rem_pre_ma7

                #cal the avg 7 days
                cleaned_sleeping_data['Sleep_MA7'] = cleaned_sleeping_data['Total_sleep'].rolling(window=7,min_periods=1).mean()
                return cleaned_sleeping_data, avg_sleep_time, plot_date

        except Exception as e:
                st.error(f"Error in processing data (Error Name : {type(e).__name__}): {e}")
                return None, 0, None

# --- 下面接你原本嘅 get_data() 同圖表 Code ---

#use st to grab csv 
@st.cache_data
def get_data():
        try:
                sheet_id = st.secrets["sheet_id"]
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                return pd.read_csv(sheet_url)
        except Exception as e:
              st.error(f"Error from Getting Data Form the sheet")
              return None
df = get_data()


#copy a new one
raw_data = df.copy()


# 1. 定義理想區間 (例如 6 小時 到 7.5 小時)
lower_goal = 6.0
upper_goal = 7.5
lower_debit = 3.0
upper_debit = 4.5

#creating interactive graph by streamlit
st.sidebar.header("DashBoard_Control")
days = st.sidebar.slider("check_days", 7, 60, 14)

#Bar_setting

#return the logic function to main
cleaned_sleeping_data, avg_sleep_time, plot_date = preprocess_data(df)

#-----Weekly Metrics Section ----
st.subheader("Weekly Performance")
with st.container(border=True):
        m1, m2, m3, m4 = st.columns(4)

#fix the data use to draw graph
plot_df = cleaned_sleeping_data.tail(days)

#cal the avg 7 days performance
recent_7 = plot_df.tail(7) 
prev_7 = plot_df.iloc[-14:-7] if len(plot_df) >= 14 else None

#Weekly health check
avg_sleep = recent_7['Total_sleep'].mean()
with st.container():
        if avg_sleep < 6.0:
                st.warning(f"Avg sleep of this week is only {avg_sleep:.1f} h, better take more rest")
        elif avg_sleep > 8.0:
                st.info("good sleep ,keep going！")

def calc_delta(col):
      if prev_7 is not None:
            diff =recent_7[col].mean() - prev_7[col].mean()
            return round(diff, 1)
      return None

#M1 Sleeping Time
m1.metric(
      label="Avg Sleep",
      value=f"{recent_7['Total_sleep'].mean():.1f}h",
      delta=calc_delta('Total_sleep')
)

#M2 Sleeping Score
m2.metric(
      label="Avg_Score",
      value=f"{recent_7['Score'].mean():.0f}",
      delta=calc_delta('Score')
)

# M3 HRV (higher is better)
m3.metric(
      label="Avg HRV",
      value=f"{recent_7['HRV'].mean():.0f} ms",
      delta=calc_delta('HRV')
)

# M4 Avg Heart Rate (lower is better, so delta_color="inverse")
m4.metric(
      label="Avg Resting HR",
      value=f"{recent_7['Avg_HR'].mean():.0f} bpm",
      delta=calc_delta('Avg_HR'),
      delta_color="inverse"
)

#prevent crash while drafting
if cleaned_sleeping_data is not None and not cleaned_sleeping_data.empty:
      pass
else:
      st.error("Data is not Available for drafing")
      st.stop()



#start to draw graph
col_left, col_right = st.columns(2)

with col_left:
        #graph 1 (total sleeping time)
        fig1 = px.line(plot_df,
         x='Date',
         y=['Total_sleep', 'Sleep_MA7'],  
         title="Sleep Trend",
        color_discrete_map={
                        'Total_sleep': 'lightgray',
                        'Sleep_MA7': '#FFA500'
                          })
        

        fig1.add_hline(y=avg_sleep_time,
        line_dash='dash', 
        line_color='red',
        annotation_text=f"Avg: {avg_sleep_time:.1f}h",
        annotation_position="top right",
        annotation_x=1.02,             # 1 代表最右邊邊界
        annotation_xref="paper",    # paper 代表以圖表框框為標準
        annotation_xanchor="left",
        annotation_font_color="white",
        annotation_font_size=12
               
        )

        fig1.update_traces(hovertemplate='<b>%{x|%b %d}</b><br> %{y:.1f}h')
        fig1.update_xaxes(tickangle=45)#rotate 45° of content in x_axes
        
        st.plotly_chart(fig1, width="stretch") #stretch is for reading on the smartphone

        #graph 3 (quailty of sleep) as area chart
        fig3 = px.area(plot_df, 
                        x='Date',
                        y=['rem_pre', 'deep_pre', 'light_pre'],
                        title="7_MA_Sleep_Quality",
                        groupnorm='percent', 
                        labels={
                                'rem_pre': 'REM Sleep (%)',
                                'deep_pre': 'Deep Sleep (%)',
                                'light_pre': 'Light Sleep (%)'}, 
                        color_discrete_map={'rem_pre': 'lightblue',
                                                'deep_pre': "orchid", 
                                                'light_pre': "#20CCA1"})
        

        fig3.update_xaxes(tickangle=45, tickformat="%b %d")
        fig3.update_yaxes(range=[0, 100], ticksuffix="%")
        fig3.update_traces(hovertemplate='<b>%{x|%b %d}</b><br> %{y:.1f}%')
        st.plotly_chart(fig3, width='stretch')

with col_right:
        #defind the color of 'Score'
        bar_color = [
                'rgba(46, 204, 113, 0.6)' if s >= 75 else
                'rgba(241, 196, 15, 0.6)' if s >= 60 else
                'rgba(231, 76, 60, 0.6)' 
                for s in plot_df['Score']
        ]

        #graph 2
        fig2 = go.Figure()

        #Avg_HR line
        fig2.add_trace(go.Scatter(
                x=plot_df['Date'], 
                y=plot_df['Avg_HR'],
                name="Avg_HR",
                mode='lines',
                line=dict(color='orchid', width=2),
                yaxis="y1"
             
        ))

        #Sleep HRV line
        fig2.add_trace(go.Scatter(
                x=plot_df['Date'],
                y=plot_df['HRV'],
                name="HRV ms", 
                mode='lines+markers',
                line=dict(color='teal', width=4, dash='dot'),
                opacity=0.5,
                yaxis="y2"
        ))
        
        fig2.update_layout(
                        title="Recovery Ticker: Avg_HR vs HRV",
                        xaxis=dict(tickangle=45, tickformat="%b %d"),
                
                #Left y axis
                yaxis=dict(
                        title=dict(
                                text="Avg_HR",
                                font=dict(color='orchid'),
                        ),
                                tickfont=dict(color='orchid'),
                                range=[0, 100],
                                side="left"
                ),

                #Right y axis
                yaxis2=dict(
                        title=dict(
                                text="HRV ms",
                                font=dict(color='teal')
                        ),
                                tickfont=dict(color='teal'),
                                anchor="x",
                                overlaying="y",
                                side="right"
                ),
                hovermode="x unified"
                )
                
        
        st.plotly_chart(fig2, width="stretch")

        #graph 4  Sleeeping Score + Body_battery
        
        fig4 = go.Figure()

        #Body battery recovery (Area chart)
        fig4.add_trace(go.Scatter(
                x=plot_df['Date'],
                y=plot_df['Body_battery'],
                name='Battery Recovery',
                fill='tozeroy', 
                mode='lines', 
                line=dict(color='rgba(46, 204, 113, 0.8)', width=0), #no line only color blocks
                fillcolor='rgba(46, 204, 113, 0.3)',
                yaxis="y1" #left hand-side y-axis
          ))     
        
        #Garmin Sleeping Score (Line Chart)
        fig4.add_trace(go.Scatter(
                x=plot_df['Date'],
                y=plot_df['Score'],
                name="Sleep Score",
                mode='lines+markers',
                line=dict(color='teal', width=3, dash='dot'),
                yaxis="y2"
        ))

        #Setting of graph 4
        fig4.update_layout(
                title="Recovery Efficiency: Battery vs Score",
                xaxis=dict(tickangle=45, tickformat="%b %d"),

        #left yaxis setting
        yaxis=dict(
                title=dict(
                        text="Body Battery", 
                        font=dict(color='teal')
                ),
                        range=[0, 100],
                        side="left"
        ),

        #right yaxis setting
        yaxis2=dict(
                title=dict(  
                        text="Score", 
                        font=dict(color='orchid') # 建議配紫色對應分數線
                ),
                        side="right",
                        overlaying="y",
                        anchor="x"
        ),

        hovermode="x unified",
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1
            )
        )
        st.plotly_chart(fig4, width="stretch")