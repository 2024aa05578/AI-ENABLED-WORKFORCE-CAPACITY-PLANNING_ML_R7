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


UP_ARROW = chr(8593)
BAU_UP_LABEL = "BAU " + UP_ARROW + "%"
DC_UP_LABEL = "DC " + UP_ARROW + "%"


# =====================================================
# COMPACT FIXED SIDEBAR WITH COLORS
# =====================================================

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        width: 380px !important;
        min-width: 380px !important;
        max-width: 380px !important;
        background: linear-gradient(180deg, #F8FAFC 0%, #EEF4FA 100%);
    }

    section[data-testid="stSidebar"] > div {
        width: 380px !important;
        min-width: 380px !important;
        max-width: 380px !important;
        padding-left: 6px !important;
        padding-right: 6px !important;
    }

    div[data-testid="stSidebarContent"] {
        width: 380px !important;
        max-width: 380px !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 12px !important;
        margin-top: 5px !important;
        margin-bottom: 3px !important;
        color: #1F4E79 !important;
    }

    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {
        font-size: 9px !important;
        line-height: 1.1 !important;
    }

    section[data-testid="stSidebar"] button {
        font-size: 10px !important;
        padding-top: 3px !important;
        padding-bottom: 3px !important;
        background-color: #1F4E79 !important;
        color: white !important;
        border-radius: 6px !important;
    }

    section[data-testid="stSidebar"] .stAlert {
        font-size: 9px !important;
    }

    .region-header {
        padding: 5px 8px;
        border-radius: 7px;
        margin-top: 6px;
        margin-bottom: 4px;
        font-weight: 700;
        font-size: 11px;
    }

    .sidebar-note {
        font-size: 9px;
        color: #475569;
        padding: 5px 7px;
        border-radius: 6px;
        background: #EAF2F8;
        border-left: 3px solid #1F4E79;
        margin-bottom: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================
# MASTER DATA
# =====================================================

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

PRODUCT_DISPLAY = {
    "UPS": "UPS",
    "Cooling": "Cooling",
    "Power Products": "Power Prod",
    "Power System": "Power Sys",
    "Industrial Automation": "Ind Auto",
}

PRODUCT_REVERSE_DISPLAY = {
    value: key for key, value in PRODUCT_DISPLAY.items()
}

REGION_STYLES = {
    "North": {
        "bg": "#EAF4FF",
        "border": "#1F77B4",
        "text": "#174A7C",
    },
    "West": {
        "bg": "#FFF4E5",
        "border": "#FF7F0E",
        "text": "#8A4A00",
    },
    "South": {
        "bg": "#EAF8EF",
        "border": "#2CA02C",
        "text": "#1B6B28",
    },
    "East": {
        "bg": "#F3EAFB",
        "border": "#9467BD",
        "text": "#573B78",
    },
}


# =====================================================
# DEFAULT PARAMETERS
# =====================================================

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

APP_SCHEMA_VERSION = "v13_filters_baseline_colored_sidebar"


# =====================================================
# SESSION INITIALIZATION
# =====================================================

def init_state():
    if st.session_state.get("schema_version") != APP_SCHEMA_VERSION:
        st.session_state.schema_version = APP_SCHEMA_VERSION
        st.session_state.growth_parameters = copy.deepcopy(DEFAULT_GROWTH_PARAMETERS)
        st.session_state.attrition_parameters = copy.deepcopy(DEFAULT_ATTRITION)
        st.session_state.productive_hours = 7.0
        st.session_state.working_days = 20
        st.session_state.target_utilization = 90.0
        st.session_state.input_df = None
        st.session_state.result_df = None
        st.session_state.needs_recalc = False
        st.session_state.uploaded_file_id = None
        st.session_state.last_filter_signature = None


# =====================================================
# SIDEBAR DISPLAY HELPERS
# =====================================================

def show_region_header(region):
    style = REGION_STYLES[region]

    st.markdown(
        f"""
        <div class="region-header"
             style="background:{style['bg']};
                    border-left:4px solid {style['border']};
                    color:{style['text']};">
            {region} Growth
        </div>
        """,
        unsafe_allow_html=True,
    )


def growth_region_to_df(growth_parameters, region):
    rows = []

    for product in PRODUCTS:
        params = growth_parameters[region][product]

        rows.append(
            {
                "Product": PRODUCT_DISPLAY[product],
                "BAU": float(params["BAU"]),
                "DC": float(params["DC"]),
            }
        )

    return pd.DataFrame(rows)


def growth_region_dfs_to_dict(edited_growth_dfs):
    growth_parameters = copy.deepcopy(DEFAULT_GROWTH_PARAMETERS)

    for region, growth_df in edited_growth_dfs.items():
        for _, row in growth_df.iterrows():
            product_label = str(row["Product"]).strip()
            product = PRODUCT_REVERSE_DISPLAY.get(product_label)

            if product in PRODUCTS:
                growth_parameters[region][product] = {
                    "BAU": float(row["BAU"]),
                    "DC": float(row["DC"]),
                }

    return growth_parameters


def attrition_dict_to_df(attrition_parameters):
    rows = []

    for product in PRODUCTS:
        rows.append(
            {
                "Product": PRODUCT_DISPLAY[product],
                "Attr %": float(attrition_parameters.get(product, 8.0)),
            }
        )

    return pd.DataFrame(rows)


def attrition_df_to_dict(attrition_df):
    attrition_parameters = copy.deepcopy(DEFAULT_ATTRITION)

    for _, row in attrition_df.iterrows():
        product_label = str(row["Product"]).strip()
        product = PRODUCT_REVERSE_DISPLAY.get(product_label)

        if product in PRODUCTS:
            attrition_parameters[product] = float(row["Attr %"])

    return attrition_parameters


def productivity_to_df():
    return pd.DataFrame(
        [
            {
                "Hrs/Day": float(st.session_state.productive_hours),
                "Days/M": int(st.session_state.working_days),
                "Util %": float(st.session_state.target_utilization),
            }
        ]
    )


def productivity_df_to_values(productivity_df):
    row = productivity_df.iloc[0]

    productive_hours = float(row["Hrs/Day"])
    working_days = int(row["Days/M"])
    target_utilization = float(row["Util %"])

    return productive_hours, working_days, target_utilization


# =====================================================
# GENERAL HELPERS
# =====================================================

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

    return pd.concat(
        [comparison, total_row],
        ignore_index=True,
    )


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

