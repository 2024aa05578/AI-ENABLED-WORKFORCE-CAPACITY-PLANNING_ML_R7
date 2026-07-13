import copy
import math
from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st

from workforce_model import calculate_workforce


st.set_page_config(
    page_title="AI Enabled Workforce & Capacity Planning",
    page_icon="🚀",
    layout="wide",
)


REGIONS = ["North", "West", "South", "East"]

PRODUCTS = [
    "UPS",
    "Cooling",
    "Power Products",
    "Power System",
    "Industrial Automation",
]

PRODUCT_ALIASES = {
    "Power Product": "Power Products",
    "Power Products": "Power Products",
    "Power System": "Power System",
    "Industrial Automation": "Industrial Automation",
    "Industiral Automation": "Industrial Automation",
    "UPS": "UPS",
    "Cooling": "Cooling",
}


DEFAULT_GROWTH_PARAMETERS = {
    "North": {
        "UPS": {"BAU": 20.0, "DC": 10.0},
        "Cooling": {"BAU": 20.0, "DC": 10.0},
        "Power Products": {"BAU": 15.0, "DC": 5.0},
        "Power System": {"BAU": 15.0, "DC": 5.0},
        "Industrial Automation": {"BAU": 15.0, "DC": 5.0},
    },
    "West": {
        "UPS": {"BAU": 30.0, "DC": 20.0},
        "Cooling": {"BAU": 30.0, "DC": 20.0},
        "Power Products": {"BAU": 20.0, "DC": 10.0},
        "Power System": {"BAU": 20.0, "DC": 10.0},
        "Industrial Automation": {"BAU": 20.0, "DC": 10.0},
    },
    "South": {
        "UPS": {"BAU": 22.0, "DC": 10.0},
        "Cooling": {"BAU": 22.0, "DC": 10.0},
        "Power Products": {"BAU": 20.0, "DC": 5.0},
        "Power System": {"BAU": 20.0, "DC": 5.0},
        "Industrial Automation": {"BAU": 20.0, "DC": 5.0},
    },
    "East": {
        "UPS": {"BAU": 15.0, "DC": 5.0},
        "Cooling": {"BAU": 15.0, "DC": 5.0},
        "Power Products": {"BAU": 15.0, "DC": 5.0},
        "Power System": {"BAU": 15.0, "DC": 5.0},
        "Industrial Automation": {"BAU": 15.0, "DC": 5.0},
    },
}


DEFAULT_ATTRITION = {
    "UPS": 8.0,
    "Cooling": 8.0,
    "Power Products": 8.0,
    "Power System": 8.0,
    "Industrial Automation": 8.0,
}


def clean_key(text):
    return (
        str(text)
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def add_total_row_and_column(matrix):
    matrix = matrix.copy()
    matrix["Total"] = matrix.sum(axis=1)

    total_row = pd.DataFrame(matrix.sum(axis=0)).T
    total_row.index = ["Total"]

    return pd.concat([matrix, total_row])


def ensure_growth_structure():
    """
    Ensures session state has the latest region-product growth structure.
    This prevents errors when Streamlit cache/session still contains old data.
    """
    if "growth_parameters" not in st.session_state:
        st.session_state.growth_parameters = copy.deepcopy(DEFAULT_GROWTH_PARAMETERS)

    if not isinstance(st.session_state.growth_parameters, dict):
        st.session_state.growth_parameters = copy.deepcopy(DEFAULT_GROWTH_PARAMETERS)

    for region in REGIONS:
        if region not in st.session_state.growth_parameters:
            st.session_state.growth_parameters[region] = copy.deepcopy(
                DEFAULT_GROWTH_PARAMETERS[region]
            )

        if not isinstance(st.session_state.growth_parameters[region], dict):
            st.session_state.growth_parameters[region] = copy.deepcopy(
                DEFAULT_GROWTH_PARAMETERS[region]
            )

        for product in PRODUCTS:
            if product not in st.session_state.growth_parametersst.session_state.growth_parameters[region][product] = copy.deepcopy(
                    DEFAULT_GROWTH_PARAMETERS[region][product]
                )

            if not isinstance(
                st.session_state.growth_parameters[region][product],
                dict,
            ):
                st.session_state.growth_parameters[region][product] = copy.deepcopy(
                    DEFAULT_GROWTH_PARAMETERS[region][product]
                )

            if "BAU" not in st.session_state.growth_parameters[region]st.session_state.growth_parameters[region][product]["BAU"] = (
                    DEFAULT_GROWTH_PARAMETERS[region][product]["BAU"]
                )

            if "DC" not in st.session_state.growth_parameters[region]st.session_state.growth_parameters[region][product]["DC"] = (
                    DEFAULT_GROWTH_PARAMETERS[region][product]["DC"]
                )


def build_bu_requirement_comparison(df, result):
    existing_resource = (
        df.groupby("Product")["Current_SE"]
        .sum()
        .reset_index()
        .rename(columns={"Current_SE": "Existing 2026 SE"})
    )

    next_year_requirement = (
        result.groupby("Product")["Combined Required Engineers"]
        .sum()
        .reset_index()
        .rename(columns={"Combined Required Engineers": "Next Year Required SE"})
    )

    comparison = existing_resource.merge(
        next_year_requirement,
        on="Product",
        how="outer",
    )

    comparison["Existing 2026 SE"] = comparison["Existing 2026 SE"].fillna(0)
    comparison["Next Year Required SE"] = comparison["Next Year Required SE"].fillna(0)

    comparison["Gap / Surplus"] = (
        comparison["Next Year Required SE"] - comparison["Existing 2026 SE"]
    )

    comparison["Additional Required"] = comparison["Gap / Surplus"].apply(
        lambda value: max(math.ceil(value), 0)
    )

    comparison["Existing 2026 SE"] = comparison["Existing 2026 SE"].round(1)
    comparison["Next Year Required SE"] = comparison["Next Year Required SE"].round(1)
    comparison["Gap / Surplus"] = comparison["Gap / Surplus"].round(1)

    total_row = pd.DataFrame(
        {
            "Product": ["Total"],
            "Existing 2026 SE": [comparison["Existing 2026 SE"].sum()],
            "Next Year Required SE": [comparison["Next Year Required SE"].sum()],
            "Gap / Surplus": [comparison["Gap / Surplus"].sum()],
            "Additional Required": [comparison["Additional Required"].sum()],
        }
    )

    comparison = pd.concat(
        [comparison, total_row],
        ignore_index=True,
    )

    return comparison


def safe_read_csv(uploaded_file):
    raw_bytes = uploaded_file.getvalue()

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin1")

    cleaned_lines = []

    for line in text.splitlines():
        line = line.strip()

        while line.endswith(","):
            line = line[:-1]

        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)

    df = pd.read_csv(
        StringIO(cleaned_text),
        engine="python",
    )

    df.columns = df.columns.str.strip()

    unnamed_cols = [
        col for col in df.columns
        if str(col).startswith("Unnamed")
    ]

    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)

    return df


def validate_input_data(df):
    required_columns = [
        "Region",
        "Product",
        "Current_SE",
        "Breakdown_WO",
        "Breakdown_Hrs",
        "PM_WO",
        "PM_Hrs",
        "Startup_WO",
        "Startup_Hrs",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}")
        st.stop()

    df = df.copy()

    df["Region"] = df["Region"].astype(str).str.strip()
    df["Product"] = df["Product"].astype(str).str.strip()
    df["Product"] = df["Product"].replace(PRODUCT_ALIASES)

    invalid_regions = sorted(
        set(df["Region"].unique()) - set(REGIONS)
    )

    invalid_products = sorted(
        set(df["Product"].unique()) - set(PRODUCTS)
    )

    if invalid_regions:
        st.error(f"Invalid regions found in uploaded file: {invalid_regions}")
        st.stop()

    if invalid_products:
        st.error(f"Invalid products found in uploaded file: {invalid_products}")
        st.stop()

    numeric_columns = [
        "Current_SE",
        "Breakdown_WO",
        "Breakdown_Hrs",
        "PM_WO",
        "PM_Hrs",
        "Startup_WO",
        "Startup_Hrs",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    if df[numeric_columns].isnull().any().any():
        st.error("Some numeric columns contain blank or invalid numeric values.")
        st.stop()

    return df


def show_bar_chart_with_values(data, x_col, y_col, title, color_col=None):
    if color_col is None:
        color_col = x_col

    fig = px.bar(
        data,
        x=x_col,
        y=y_col,
        color=color_col,
        text=y_col,
        title=title,
        color_discrete_sequence=[
            "#1F77B4",
            "#FF7F0E",
            "#2CA02C",
            "#D62728",
            "#9467BD",
            "#8C564B",
            "#E377C2",
            "#7F7F7F",
            "#BCBD22",
            "#17BECF",
        ],
    )

    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        height=430,
        title_x=0.05,
        showlegend=False,
        margin=dict(
            l=40,
            r=30,
            t=70,
            b=90,
        ),
        xaxis_title="",
        yaxis_title="Engineers",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(
            size=12,
            color="#243447",
        ),
    )

    fig.update_xaxes(
        fixedrange=True,
        tickangle=-20,
    )

    fig.update_yaxes(
        fixedrange=True,
        rangemode="tozero",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "scrollZoom": False,
            "staticPlot": False,
        },
    )


# =====================================================
# SESSION STATE
# =====================================================

if "growth_parameters" not in st.session_state:
    st.session_state.growth_parameters = copy.deepcopy(DEFAULT_GROWTH_PARAMETERS)

ensure_growth_structure()

if "attrition_parameters" not in st.session_state:
    st.session_state.attrition_parameters = copy.deepcopy(DEFAULT_ATTRITION)

for product in PRODUCTS:
    if product not in st.session_state.attrition_parameters:
        st.session_state.attrition_parameters[product] = DEFAULT_ATTRITION[product]

if "productive_hours" not in st.session_state:
    st.session_state.productive_hours = 7.0

if "working_days" not in st.session_state:
    st.session_state.working_days = 20

if "target_utilization" not in st.session_state:
    st.session_state.target_utilization = 90.0

if "input_df" not in st.session_state:
    st.session_state.input_df = None

if "result_df" not in st.session_state:
    st.session_state.result_df = None

if "needs_recalc" not in st.session_state:
    st.session_state.needs_recalc = False

if "uploaded_file_id" not in st.session_state:
    st.session_state.uploaded_file_id = None


# =====================================================
# SIDEBAR FORM
# =====================================================

st.sidebar.header("Planning Assumptions")

st.sidebar.info(
    "Update product-wise BAU and DC growth, then click Apply Assumptions."
)

with st.sidebar.form("planning_assumptions_form"):
    st.subheader("Region and Product Wise Growth")

    updated_growth_parameters = {}

    for region in REGIONS:
        updated_growth_parameters[region] = {}

        st.markdown(f"### {region} Growth")

        header_product_col, header_bau_col, header_dc_col = st.columns([1.8, 1, 1])

        with header_product_col:
            st.markdown("**Product**")

        with header_bau_col:
            st.markdown("**BAU %**")

        with header_dc_col:
            st.markdown("**DC %**")

        for product in PRODUCTS:
            product_col, bau_col, dc_col = st.columns([1.8, 1, 1])

            with product_col:
                st.write(product)

            with bau_col:
                bau_value = st.number_input(
                    label=f"{region} {product} BAU %",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(
                        st.session_state.growth_parameters[region][product]["BAU"]
                    ),
                    step=1.0,
                    key=f"{clean_key(region)}_{clean_key(product)}_bau_form",
                    label_visibility="collapsed",
                )

            with dc_col:
                dc_value = st.number_input(
                    label=f"{region} {product} DC %",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(
                        st.session_state.growth_parameters[region][product]["DC"]
                    ),
                    step=1.0,
                    key=f"{clean_key(region)}_{clean_key(product)}_dc_form",
                    label_visibility="collapsed",
                )

            updated_growth_parameters[region][product] = {
                "BAU": bau_value,
                "DC": dc_value,
            }

        st.markdown("---")

    st.subheader("BU Wise Attrition")

    updated_attrition = {}

    for product in PRODUCTS:
        updated_attrition[product] = st.number_input(
            f"{product} Attrition %",
            min_value=0.0,
            max_value=30.0,
            value=float(st.session_state.attrition_parameters[product]),
            step=0.5,
            key=f"{clean_key(product)}_attrition_form",
        )

    st.subheader("Workforce Productivity")

    updated_productive_hours = st.number_input(
        "Productive Hours Per Day",
        min_value=1.0,
        max_value=24.0,
        value=float(st.session_state.productive_hours),
        step=0.5,
    )

    updated_working_days = st.number_input(
        "Working Days Per Month",
        min_value=1,
        max_value=31,
        value=int(st.session_state.working_days),
        step=1,
    )

    updated_target_utilization = st.number_input(
        "Target Engineer Utilization %",
        min_value=1.0,
        max_value=100.0,
        value=float(st.session_state.target_utilization),
        step=1.0,
    )

    apply_assumptions = st.form_submit_button("Apply Assumptions")


if apply_assumptions:
    st.session_state.growth_parameters = updated_growth_parameters
    st.session_state.attrition_parameters = updated_attrition
    st.session_state.productive_hours = updated_productive_hours
    st.session_state.working_days = updated_working_days
    st.session_state.target_utilization = updated_target_utilization

    st.session_state.needs_recalc = True

    st.sidebar.success("Assumptions applied. Dashboard will refresh.")


# =====================================================
# MAIN PAGE
# =====================================================

st.title("AI Enabled Workforce & Capacity Planning")

st.info(
    "Upload workforce_input.csv, update assumptions in the sidebar, "
    "click Apply Assumptions, and review existing 2026 resources vs predicted next year requirement."
)

uploaded_file = st.file_uploader(
    "Upload workforce_input.csv",
    type=["csv"],
)

if uploaded_file is not None:
    current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"

    if current_file_id != st.session_state.uploaded_file_id:
        try:
            raw_df = safe_read_csv(uploaded_file)
            st.session_state.input_df = validate_input_data(raw_df)
            st.session_state.uploaded_file_id = current_file_id
            st.session_state.needs_recalc = True
            st.success("CSV uploaded successfully.")

        except Exception as error:
            st.error("CSV upload failed. Please check file format.")
            st.exception(error)
            st.stop()


if st.session_state.input_df is None:
    st.warning("Please upload workforce_input.csv to start workforce planning.")
    st.stop()


df = st.session_state.input_df


# =====================================================
# CALCULATE WORKFORCE ONLY WHEN NEEDED
# =====================================================

if st.session_state.needs_recalc or st.session_state.result_df is None:
    try:
        result = calculate_workforce(
            df=df,
            growth_parameters=st.session_state.growth_parameters,
            attrition_parameters=st.session_state.attrition_parameters,
            productive_hours=st.session_state.productive_hours,
            working_days=st.session_state.working_days,
            target_utilization=st.session_state.target_utilization,
        )

        st.session_state.result_df = result
        st.session_state.needs_recalc = False

    except Exception as error:
        st.error("Calculation failed. Please check workforce_model.py.")
        st.exception(error)
        st.stop()

else:
    result = st.session_state.result_df


required_result_columns = [
    "Available Engineers",
    "BAU Required Engineers",
    "DC Incremental Engineers",
    "Combined Required Engineers",
    "Combined Additional Required",
]

missing_result_columns = [
    col for col in required_result_columns
    if col not in result.columns
]

if missing_result_columns:
    st.error(
        "workforce_model.py is not updated. Missing result columns: "
        + str(missing_result_columns)
    )
    st.stop()


# =====================================================
# DASHBOARD SUMMARY
# =====================================================

st.subheader("Dashboard Summary")

total_current = df["Current_SE"].sum()
total_available = round(result["Available Engineers"].sum(), 1)
total_bau_required = round(result["BAU Required Engineers"].sum(), 1)
total_dc_required = round(result["DC Incremental Engineers"].sum(), 1)
total_combined_required = round(result["Combined Required Engineers"].sum(), 1)
total_combined_hiring = int(result["Combined Additional Required"].sum())

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

kpi1.metric("Existing 2026 SE", total_current)
kpi2.metric("After Attrition", total_available)
kpi3.metric("BAU Required SE", total_bau_required)
kpi4.metric("DC Addl. SE", total_dc_required)
kpi5.metric("Next Year Required SE", total_combined_required)
kpi6.metric("Additional Required", total_combined_hiring)


# =====================================================
# VISUAL DASHBOARD
# =====================================================

st.markdown("---")
st.subheader("Visual Dashboard")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    product_required = (
        result.groupby("Product")["Combined Required Engineers"]
        .sum()
        .reset_index()
    )

    show_bar_chart_with_values(
        data=product_required,
        x_col="Product",
        y_col="Combined Required Engineers",
        title="Next Year Required SE by Product",
        color_col="Product",
    )

with chart_col2:
    region_required = (
        result.groupby("Region")["Combined Required Engineers"]
        .sum()
        .reset_index()
    )

    show_bar_chart_with_values(
        data=region_required,
        x_col="Region",
        y_col="Combined Required Engineers",
        title="Next Year Required SE by Region",
        color_col="Region",
    )

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    product_hiring = (
        result.groupby("Product")["Combined Additional Required"]
        .sum()
        .reset_index()
    )

    show_bar_chart_with_values(
        data=product_hiring,
        x_col="Product",
        y_col="Combined Additional Required",
        title="Additional Requirement by Product",
        color_col="Product",
    )

with chart_col4:
    region_hiring = (
        result.groupby("Region")["Combined Additional Required"]
        .sum()
        .reset_index()
    )

    show_bar_chart_with_values(
        data=region_hiring,
        x_col="Region",
        y_col="Combined Additional Required",
        title="Additional Requirement by Region",
        color_col="Region",
    )


# =====================================================
# DETAIL TABS
# =====================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Input Data",
        "Full Results",
        "BU Requirement Comparison",
        "DC and Combined",
        "Download",
    ]
)

with tab1:
    st.subheader("Uploaded Input Data")
    st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("Workforce Planning Results")
    st.dataframe(result, use_container_width=True)

with tab3:
    st.subheader("BU Requirement Comparison")

    st.info(
        "This table compares existing 2026 resources with predicted next year requirement."
    )

    bu_comparison = build_bu_requirement_comparison(
        df=df,
        result=result,
    )

    st.dataframe(
        bu_comparison,
        use_container_width=True,
    )

with tab4:
    st.subheader("DC Addition Requirement Table")

    dc_table = result.pivot_table(
        values="DC Incremental Engineers",
        index="Product",
        columns="Region",
        fill_value=0,
        aggfunc="sum",
    )

    st.dataframe(
        add_total_row_and_column(dc_table).round(1),
        use_container_width=True,
    )

    st.subheader("Combined BAU + DC Requirement Table")

    combined_table = result.pivot_table(
        values="Combined Required Engineers",
        index="Product",
        columns="Region",
        fill_value=0,
        aggfunc="sum",
    )

    st.dataframe(
        add_total_row_and_column(combined_table).round(1),
        use_container_width=True,
    )

    st.subheader("Combined Hiring Requirement Table")

    hiring_table = result.pivot_table(
        values="Combined Additional Required",
        index="Product",
        columns="Region",
        fill_value=0,
        aggfunc="sum",
    )

    st.dataframe(
        add_total_row_and_column(hiring_table).round(1),
        use_container_width=True,
    )

with tab5:
    st.subheader("Download Output")

    csv_output = result.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Workforce Planning Output",
        data=csv_output,
        file_name="workforce_planning_output.csv",
        mime="text/csv",
    )
