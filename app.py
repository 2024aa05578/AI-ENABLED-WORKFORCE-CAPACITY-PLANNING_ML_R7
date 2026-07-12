import copy
from io import StringIO

import pandas as pd
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
        lambda value: int(value) + 1 if value > int(value) and value > 0 else max(int(value), 0)
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


# =====================================================
# SESSION STATE
# =====================================================

if "growth_parameters" not in st.session_state:
    st.session_state.growth_parameters = copy.deepcopy(DEFAULT_GROWTH_PARAMETERS)

if "attrition_parameters" not in st.session_state:
    st.session_state.attrition_parameters = copy.deepcopy(DEFAULT_ATTRITION)

if "productive_hours" not in st.session_state:
    st.session_state.productive_hours = 7.0

if "working_days" not in st.session_state:
    st.session_state.working_days = 20

if "target_utilization" not in st.session_state:
    st.session_state.target_utilization = 90.0

if "input_df" not in st.session_state:
    st.session_state.input_df = None


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
