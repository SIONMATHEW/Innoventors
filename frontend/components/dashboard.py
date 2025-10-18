import io
import pandas as pd
import altair as alt
import requests
import streamlit as st

# ------- Data fetch (cached) -------
@st.cache_data(ttl=30)
def _fetch_incidents(api_url: str) -> pd.DataFrame:
    r = requests.get(f"{api_url}/incidents", timeout=30)
    r.raise_for_status()
    payload = r.json()

    # support both v2 (incidents: [{inc,file,analysis}]) and v3 (flat fields)
    items = payload.get("incidents", [])
    rows = []
    for it in items:
        # v3 flat
        if "summary" in it or "root_cause" in it:
            rows.append({
                "ID": it.get("id"),
                "Case Name": it.get("case_name"),
                "Summary": it.get("summary"),
                "Root Cause": it.get("root_cause"),
                "Recommendation": it.get("recommendation"),
                "Severity": it.get("severity"),
                "Category": it.get("category"),
                "File": it.get("file"),
                "Uploaded At": it.get("uploaded_at"),
            })
        else:
            # v2 shape with nested "analysis" and "file"
            a = it.get("analysis", {}) or {}
            f = it.get("file", {}) or {}
            rows.append({
                "ID": it.get("id"),
                "Case Name": it.get("case_name"),
                "Summary": a.get("summary"),
                "Root Cause": a.get("root_cause"),
                "Recommendation": a.get("recommendation"),
                "Severity": a.get("severity"),
                "Category": a.get("category"),
                "File": f.get("filename"),
                "Uploaded At": f.get("uploaded"),
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Severity"] = df["Severity"].fillna("Unknown").str.title()
        df["Category"] = df["Category"].fillna("Uncategorized")
        df["File"] = df["File"].fillna("Unknown")
    return df

def _severity_badge(sev: str) -> str:
    sev = (sev or "Unknown").strip().title()
    emoji = {"High": "🛑", "Medium": "🟠", "Low": "🟢"}.get(sev, "⚪")
    return f"{emoji} {sev}"

def _download_csv_button(df: pd.DataFrame):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Export CSV",
        data=csv,
        file_name="incidents_export.csv",
        mime="text/csv",
        use_container_width=False,
    )

def _filters_ui(df: pd.DataFrame):
    st.markdown("#### Filters")
    c1, c2, c3, c4 = st.columns([0.28, 0.24, 0.24, 0.24])
    with c1:
        files = ["All"] + sorted(df["File"].dropna().unique().tolist())
        sel_file = st.selectbox("File", files, index=0)
    with c2:
        severities = ["High", "Medium", "Low", "Unknown"]
        sel_sev = st.multiselect("Severity", severities, default=["High","Medium","Low"])
    with c3:
        cats = sorted(df["Category"].dropna().unique().tolist())
        sel_cat = st.multiselect("Category", cats, default=cats)
    with c4:
        q = st.text_input("Search (case/summary/root cause)", value="")
    return sel_file, sel_sev, sel_cat, q

def _apply_filters(df: pd.DataFrame, sel_file, sel_sev, sel_cat, q):
    filtered = df.copy()
    if sel_file and sel_file != "All":
        filtered = filtered[filtered["File"] == sel_file]
    if sel_sev:
        filtered = filtered[filtered["Severity"].isin([s.title() for s in sel_sev])]
    if sel_cat:
        filtered = filtered[filtered["Category"].isin(sel_cat)]
    if q:
        ql = q.lower()
        mask = (
            filtered["Case Name"].fillna("").str.lower().str.contains(ql) |
            filtered["Summary"].fillna("").str.lower().str.contains(ql) |
            filtered["Root Cause"].fillna("").str.lower().str.contains(ql)
        )
        filtered = filtered[mask]
    return filtered

def _kpis(df: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Incidents", len(df))
    with c2: st.metric("High", (df["Severity"] == "High").sum())
    with c3: st.metric("Medium", (df["Severity"] == "Medium").sum())
    with c4: st.metric("Low", (df["Severity"] == "Low").sum())

def _cards_list(df):
    cards_html = ""
    for _, row in df.iterrows():
        cards_html += f"""
        <div class='incident-card'>
            <h4>{row['Case Name']}</h4>
            <div class='meta'>
                <span>📄 <b>{row['File']}</b></span>
                <span>🕓 {row['Uploaded At']}</span>
                <span class='chip'>{row['Category']}</span>
                <span class='chip' style='background:#fee2e2;color:#991b1b;font-weight:700'>{row['Severity']}</span>
            </div>
            <p><b>Summary:</b> {row['Summary']}</p>
            <p><b>Root Cause:</b> {row['Root Cause']}</p>
            <p><b>Recommendation:</b> {row['Recommendation']}</p>
        </div>
        """
    st.markdown(cards_html, unsafe_allow_html=True)

def _charts(df: pd.DataFrame):
    st.markdown("#### Analytics")
    ch1, ch2 = st.columns(2)

    by_sev = df.groupby("Severity").size().reset_index(name="Count")
    by_cat = df.groupby("Category").size().reset_index(name="Count")

    with ch1:
        st.markdown("**By Severity**")
        chart1 = alt.Chart(by_sev).mark_arc(innerRadius=50).encode(
            theta="Count:Q",
            color=alt.Color("Severity:N", legend=None),
            tooltip=["Severity", "Count"]
        ).properties(height=340)
        # ✅ Make chart background consistent and clean
        chart1 = chart1.configure_view(strokeOpacity=0).configure(background='white')
        st.altair_chart(chart1, use_container_width=True)

    with ch2:
        st.markdown("**By Category**")
        chart2 = alt.Chart(by_cat).mark_bar().encode(
            x=alt.X("Count:Q", title="Incidents"),
            y=alt.Y("Category:N", sort="-x", title=None),
            tooltip=["Category", "Count"]
        ).properties(height=340)
        # ✅ Make chart background consistent and clean
        chart2 = chart2.configure_view(strokeOpacity=0).configure(background='white')
        st.altair_chart(chart2, use_container_width=True)


def show_dashboard(api_url: str):
    st.markdown("### 2) Incident Intelligence")
    st.markdown("<style>[data-testid='stProgress']{display:none!important}</style>", unsafe_allow_html=True)

    # Fetch
    try:
        df = _fetch_incidents(api_url)
    except Exception as e:
        st.error(f"Backend not reachable: {e}")
        return

    # Empty state
    if df.empty:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-emoji">📄</div>
            <h3>No incidents yet</h3>
            <p>Upload and analyze a PDF to generate insights.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Filters bar
    with st.container():
        st.markdown('<div class="card toolbar">', unsafe_allow_html=True)
        sel_file, sel_sev, sel_cat, q = _filters_ui(df)
        st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    filtered = _apply_filters(df, sel_file, sel_sev, sel_cat, q)

    # KPIs row
    _kpis(filtered)

    # Export + view toggle
    top_l, top_r = st.columns([0.6, 0.4])
    with top_l:
        view = st.segmented_control("View", options=["Cards", "Table"], default="Cards")
    with top_r:
        _download_csv_button(filtered)

    st.write("")

    # Render view
    if view == "Table":
        show_cols = ["ID","Case Name","Severity","Category","Summary","Root Cause","Recommendation","File","Uploaded At"]
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True, height=420)
    else:
        _cards_list(filtered)

    st.write("")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    _charts(filtered)
    st.markdown('</div>', unsafe_allow_html=True)
