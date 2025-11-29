import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- Configuration & Setup ---
st.set_page_config(page_title="SmartSub AI", page_icon="💳", layout="wide")
DATA_FILE = 'subscriptions_data.csv'

# --- Compatibility Fix for st.rerun() ---
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# --- 1. AI Logic & Helper Functions ---

def suggest_category(name):
    name = str(name).lower()
    keywords = {
        'Entertainment': ['netflix', 'hulu', 'disney', 'hbo', 'prime', 'cinema', 'youtube', 'tv'],
        'Music': ['spotify', 'apple music', 'tidal', 'deezer', 'pandora', 'music', 'sound'],
        'Productivity': ['notion', 'evernote', 'todoist', 'linear', 'jira', 'slack', 'zoom', 'office', 'microsoft'],
        'Utilities': ['internet', 'electric', 'water', 'gas', 'mobile', 'phone', 'verizon', 'at&t', 't-mobile'],
        'Software': ['adobe', 'figma', 'github', 'gitlab', 'aws', 'cloud', 'hosting', 'domain', 'chatgpt', 'openai'],
        'Fitness': ['gym', 'fitness', 'yoga', 'peloton', 'strava', 'health', 'myfitnesspal'],
        'Shopping': ['amazon', 'walmart', 'costco', 'prime', 'delivery', 'uber'],
    }
    
    for category, keys in keywords.items():
        if any(k in name for k in keys):
            return category
    return 'Uncategorized'

def get_priority(category):
    essentials = ['Utilities', 'Productivity', 'Software', 'Fitness']
    if category in essentials:
        return '1st Priority'
    return '2nd Priority'

def normalize_cost(cost, cycle):
    try:
        cost = float(cost)
        if cycle == 'Yearly': return cost / 12
        if cycle == 'Quarterly': return cost / 3
        return cost
    except:
        return 0.0

# --- 2. Data Management ---

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=['Name', 'Cost', 'Billing Cycle', 'Category', 'Renewal Date'])
    
    try:
        df = pd.read_csv(DATA_FILE)
        df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce').fillna(0.0)
        df['Renewal Date'] = df['Renewal Date'].astype(str)
        return df
    except Exception as e:
        st.error(f"Error loading data file: {e}")
        return pd.DataFrame(columns=['Name', 'Cost', 'Billing Cycle', 'Category', 'Renewal Date'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 3. AI Insights Engine ---

def generate_insights(df):
    insights = []
    today = datetime.now().date()
    
    if df.empty:
        return insights

    # A. Renewal Alerts (2 Days)
    for index, row in df.iterrows():
        try:
            renewal_date = datetime.strptime(str(row['Renewal Date']), '%Y-%m-%d').date()
            days_until = (renewal_date - today).days
            
            if 0 <= days_until <= 2:
                insights.append({
                    "type": "Critical",
                    "title": f"Renewal Alert: {row['Name']}",
                    "msg": f"Renews in {days_until} day(s). Cost: ₹{row['Cost']}"
                })
        except:
            continue

    # B. Suggest pausing costly lifestyle subscriptions
    try:
        lifestyle_subs = df[df['Category'].apply(get_priority) == '2nd Priority']
        if not lifestyle_subs.empty:
            most_expensive = lifestyle_subs.loc[lifestyle_subs['Cost'].idxmax()]
            insights.append({
                "type": "Suggestion",
                "title": "Spending Strategy",
                "msg": f"Consider pausing '{most_expensive['Name']}' (₹{most_expensive['Cost']}) if you need to save money."
            })
    except:
        pass

    # C. Duplicate Detection
    duplicates = df[df.duplicated(subset=['Name'], keep=False)]
    if not duplicates.empty:
        for name in duplicates['Name'].unique():
            insights.append({
                "type": "Warning",
                "title": "Duplicate Found",
                "msg": f"You have multiple subscriptions for '{name}'."
            })

    return insights

# --- 4. Main Application UI ---

def main():
    st.sidebar.header("➕ Add New Subscription")
    
    with st.sidebar.form("add_sub_form", clear_on_submit=True):
        name = st.text_input("Service Name (e.g. Netflix)")
        
        suggested_cat = suggest_category(name) if name else "Uncategorized"
        
        col1, col2 = st.columns(2)
        with col1:
            cost = st.number_input("Cost (₹)", min_value=0.0, step=0.01)
        with col2:
            cycle = st.selectbox("Billing Cycle", ["Monthly", "Yearly", "Quarterly"])
            
        category = st.selectbox("Category", [
            suggested_cat, "Entertainment", "Music", "Productivity", 
            "Utilities", "Software", "Fitness", "Shopping", "Uncategorized"
        ])
        
        renewal = st.date_input("Next Renewal Date")
        
        submitted = st.form_submit_button("Track Subscription")
        
        if submitted and name:
            df = load_data()
            new_row = pd.DataFrame([{
                'Name': name,
                'Cost': cost,
                'Billing Cycle': cycle,
                'Category': category,
                'Renewal Date': renewal
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success(f"Added {name}!")
            safe_rerun()

    st.title("💳 SmartSub AI Tracker")
    st.caption("Manage recurring expenses, detect duplicates, and get budget insights.")
    
    df = load_data()

    if not df.empty:
        df['Monthly Cost'] = df.apply(lambda x: normalize_cost(x['Cost'], x['Billing Cycle']), axis=1)
        df['Priority'] = df['Category'].apply(get_priority)
        
        total_monthly = df['Monthly Cost'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Monthly Cost", f"₹{total_monthly:.2f}")
        m2.metric("Yearly Projection", f"₹{total_monthly * 12:.2f}")
        m3.metric("Active Services", len(df))

        st.markdown("---")

        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.subheader("Your Subscriptions")
            for i, row in df.iterrows():
                icon = "🟢" if row['Priority'] == "1st Priority" else "🟠"
                
                with st.expander(f"{icon} {row['Name']} — ₹{row['Cost']} ({row['Billing Cycle']})"):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Category:** {row['Category']}")
                    c2.write(f"**Priority:** {row['Priority']}")
                    c3.write(f"**Renews:** {row['Renewal Date']}")
                    
                    if st.button("Delete Subscription", key=f"del_{i}"):
                        df = df.drop(index=i)
                        save_data(df)
                        safe_rerun()

        with col_right:
            st.subheader("AI Insights")
            insights = generate_insights(df)
            
            if insights:
                for item in insights:
                    if item['type'] == 'Critical':
                        st.error(f"**{item['title']}**\n\n{item['msg']}")
                    elif item['type'] == 'Warning':
                        st.warning(f"**{item['title']}**\n\n{item['msg']}")
                    else:
                        st.info(f"**{item['title']}**\n\n{item['msg']}")
            else:
                st.success("All systems go! No alerts detected.")

            st.markdown("### Spend Distribution")
            if total_monthly > 0:
                fig = px.pie(df, values='Monthly Cost', names='Category', hole=0.4)
                fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("👋 Welcome! Add a subscription to get started!")

if __name__ == "__main__":
    main()
