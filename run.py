# run.py — Weather Dashboard (CSV → Streamlit), fixed selectbox indices
import io
import pandas as pd
import streamlit as st

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Weather Dashboard", page_icon="🌤️", layout="wide")
st.title("🌤️ Weather Dashboard")
st.caption("Load a CSV, pick columns, auto-convert °F→°C, and explore.")

# ----------------------------
# Sidebar: Data source
# ----------------------------
st.sidebar.header("Data Source")
default_path = "/workspaces/waterclass/data.csv"

mode = st.sidebar.radio("Choose input method:", ["Use default path", "Upload CSV"], index=0)

if mode == "Use default path":
    csv_path = st.sidebar.text_input("CSV path", value=default_path)
    try:
        df = pd.read_csv(csv_path)
        st.sidebar.success("Loaded from path ✅")
    except Exception as e:
        st.sidebar.error(f"Failed to read CSV: {e}")
        st.stop()
else:
    uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if not uploaded:
        st.info("Please upload a CSV to continue.")
        st.stop()
    try:
        df = pd.read_csv(uploaded)
        st.sidebar.success("Uploaded ✅")
    except Exception as e:
        st.sidebar.error(f"Failed to read CSV: {e}")
        st.stop()

if df.empty:
    st.warning("Your CSV appears to be empty.")
    st.stop()

# ----------------------------
# Helpers
# ----------------------------
def first_match(cols, substrings):
    """Return the first column whose name contains any of the substrings (case-insensitive)."""
    lowered = [c.lower() for c in cols]
    for sub in substrings:
        for i, name in enumerate(lowered):
            if sub in name:
                return cols[i]
    return None

def safe_index(options, value, offset=0, fallback=0):
    """Return a **plain int** index for Streamlit selectbox."""
    try:
        if value is None:
            return int(fallback)
        return int(offset + options.index(value))
    except Exception:
        return int(fallback)

# ----------------------------
# Sidebar: Column mapping & units
# ----------------------------
st.sidebar.header("Columns & Units")

cols = list(df.columns)

temp_guess = first_match(cols, ["temp"])
hum_guess  = first_match(cols, ["hum"])
x_guess    = first_match(cols, ["date", "time", "day", "timestamp"])

# Temperature select
temp_idx = safe_index(cols, temp_guess, fallback=0)
temp_col = st.sidebar.selectbox("Temperature column", options=cols, index=temp_idx)

# Humidity select (optional)
hum_options = ["<none>"] + cols
hum_idx = safe_index(cols, hum_guess, offset=1, fallback=0)
hum_col = st.sidebar.selectbox("Humidity column (optional)", options=hum_options, index=hum_idx)

# Unit select
unit = st.sidebar.selectbox("Temperature unit in CSV", ["°C", "°F"], index=0)

# X-axis select (optional)
x_options = ["<index>"] + cols
x_idx = safe_index(cols, x_guess, offset=1, fallback=0)
x_col = st.sidebar.selectbox("X-axis column (optional)", options=x_options, index=x_idx)

# ----------------------------
# Prepare & clean data
# ----------------------------
work = df.copy()

# Ensure numeric for chosen columns
work[temp_col] = pd.to_numeric(work[temp_col], errors="coerce")
if hum_col != "<none>":
    work[hum_col] = pd.to_numeric(work[hum_col], errors="coerce")

# Convert °F -> °C if needed
if unit == "°F":
    work["Temperature_C"] = (work[temp_col] - 32) * 5.0 / 9.0
else:
    work["Temperature_C"] = work[temp_col]

# Build plotting frame
plot_df = pd.DataFrame({"Temperature (°C)": work["Temperature_C"]})
if hum_col != "<none>":
    plot_df["Humidity (%)"] = work[hum_col]

# X-axis
if x_col != "<index>":
    # Try parse datetime nicely; if parsing fails, just use raw values
    parsed = pd.to_datetime(work[x_col], errors="coerce")
    idx = parsed.where(parsed.notna(), work[x_col])
    plot_df.index = idx
    plot_df.index.name = x_col

# Remove rows that are entirely NaN in both plotted series
plot_df = plot_df.dropna(how="all")

if plot_df.empty or plot_df["Temperature (°C)"].dropna().empty:
    st.error("No valid temperature data after cleaning. Please check column selection and units.")
    st.stop()

# ----------------------------
# KPIs
# ----------------------------
c1, c2, c3 = st.columns(3)
avg_temp = plot_df["Temperature (°C)"].mean()
min_temp = plot_df["Temperature (°C)"].min()
max_temp = plot_df["Temperature (°C)"].max()

c1.metric("Average Temp (°C)", f"{avg_temp:.1f}")
c2.metric("Min Temp (°C)", f"{min_temp:.1f}")
c3.metric("Max Temp (°C)", f"{max_temp:.1f}")

# ----------------------------
# Chart
# ----------------------------
st.subheader("Trend")
st.line_chart(plot_df)

# ----------------------------
# Data table
# ----------------------------
with st.expander("Show raw data"):
    st.dataframe(work)

# ----------------------------
# Temperature list (original-loop style)
# ----------------------------
st.subheader("Temperatures (°C)")
temp_values = plot_df["Temperature (°C)"].dropna().tolist()
st.write("\n".join([f"- {t:.1f}°C" for t in temp_values[:1000]]))  # safety cap

# ----------------------------
# Download processed CSV
# ----------------------------
st.subheader("Download processed data")
out = work.copy()
out["Temperature (°C)"] = out["Temperature_C"]
buf = io.StringIO()
out.to_csv(buf, index=False)
st.download_button(
    "Download CSV (with Temperature °C)",
    data=buf.getvalue(),
    file_name="weather_processed.csv",
    mime="text/csv",
)

st.caption("Tip: If your CSV is in °F, set 'Temperature unit in CSV' to °F to auto-convert.")
