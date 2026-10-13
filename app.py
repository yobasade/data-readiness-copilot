from agent_service import run_readiness_agent
import os

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Data Deployment Readiness Copilot",
    page_icon="✅",
    layout="wide",
)


def create_sample_data():
    """Create a sample flat file for the demo."""
    return pd.DataFrame(
        [
            {
                "account_id": "A1001",
                "account_name": "Acme Wireless",
                "segment": "Enterprise",
                "industry": "Telecommunications",
                "primary_contact_email": "maya@acmewireless.com",
                "opportunity_amount": 250000,
                "opportunity_close_date": "2026-12-15",
                "last_updated": "2025-01-15",
            },
            {
                "account_id": "A1002",
                "account_name": "Globex Corporation",
                "segment": "Enterprise",
                "industry": "Technology",
                "primary_contact_email": "leo@globex.com",
                "opportunity_amount": 125000,
                "opportunity_close_date": "",
                "last_updated": "2025-04-15",
            },
            {
                "account_id": "A1002",
                "account_name": "Globex Corporation Duplicate",
                "segment": "Enterprise",
                "industry": "Technology",
                "primary_contact_email": "invalid-email",
                "opportunity_amount": 75000,
                "opportunity_close_date": "2026-11-30",
                "last_updated": "2025-04-15",
            },
            {
                "account_id": "A1003",
                "account_name": "Initech Communications",
                "segment": "",
                "industry": "Telecommunications",
                "primary_contact_email": "operations@initech.com",
                "opportunity_amount": 50000,
                "opportunity_close_date": "2026-10-20",
                "last_updated": "2023-02-20",
            },
        ]
    )


def load_csv(uploaded_file, default_data):
    """Use uploaded CSV data or fallback to synthetic sample data."""
    if uploaded_file is None:
        return default_data.copy()

    try:
        return pd.read_csv(uploaded_file)
    except Exception as error:
        st.error(f"Could not read {uploaded_file.name}: {error}")
        return default_data.copy()


def missing_values(df, column):
    """Count null or blank values in a column."""
    if column not in df.columns:
        return 0

    values = df[column]
    missing = values.isna() | values.astype("string").str.strip().eq("").fillna(False)
    return int(missing.sum())


def run_quality_checks(data):
    """Profile the fields present in one uploaded dataset."""
    issues = []

    if data.empty or len(data.columns) == 0:
        issues.append(
            {
                "severity": "Critical",
                "category": "Completeness",
                "dataset": "uploaded data",
                "issue": "CSV contains no data rows or columns",
                "count": 0,
                "recommendation": "Upload a CSV with a header row and at least one data row.",
            }
        )
        return pd.DataFrame(issues)

    for column in data.columns:
        count = missing_values(data, column)
        if count > 0:
            issues.append(
                {
                    "severity": "High",
                    "category": "Completeness",
                    "dataset": "uploaded data",
                    "issue": f"Missing values in {column}",
                    "count": count,
                    "recommendation": f"Review and populate missing values in {column} where required.",
                }
            )

    identifier_columns = [
        column
        for column in data.columns
        if column.strip().lower() == "id" or column.strip().lower().endswith("_id")
    ]
    for column in identifier_columns:
        duplicate_count = int(data[column].dropna().duplicated(keep=False).sum())
        if duplicate_count > 0:
            issues.append(
                {
                    "severity": "Critical",
                    "category": "Uniqueness",
                    "dataset": "uploaded data",
                    "issue": f"Duplicate identifiers in {column}",
                    "count": duplicate_count,
                    "recommendation": f"Make values in {column} unique or define a canonical identifier.",
                }
            )

    email_columns = [column for column in data.columns if "email" in column.lower()]
    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    for column in email_columns:
        present_emails = data[column].dropna().astype(str).str.strip()
        present_emails = present_emails[present_emails.ne("")]
        invalid_count = int((~present_emails.str.match(email_pattern)).sum())
        if invalid_count > 0:
            issues.append(
                {
                    "severity": "Medium",
                    "category": "Validity",
                    "dataset": "uploaded data",
                    "issue": f"Invalid email addresses in {column}",
                    "count": invalid_count,
                    "recommendation": f"Validate email addresses in {column} before engagement workflows.",
                }
            )

    freshness_columns = {
        "last_updated",
        "updated_at",
        "updated_on",
        "modified_at",
        "modified_on",
    }
    for column in data.columns:
        if column.strip().lower() not in freshness_columns:
            continue

        updated_dates = pd.to_datetime(data[column], errors="coerce", utc=True)
        stale_cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=365)
        stale_count = int((updated_dates < stale_cutoff).sum())
        if stale_count > 0:
            issues.append(
                {
                    "severity": "Medium",
                    "category": "Freshness",
                    "dataset": "uploaded data",
                    "issue": f"Records in {column} are more than one year old",
                    "count": stale_count,
                    "recommendation": "Confirm the source refresh process and monitor data freshness.",
                }
            )

    return pd.DataFrame(issues)


def calculate_score(issues):
    """Calculate a transparent readiness score."""
    severity_penalties = {
        "Critical": 15,
        "High": 8,
        "Medium": 4,
        "Low": 2,
    }

    penalty = 0
    for _, issue in issues.iterrows():
        penalty += severity_penalties.get(issue["severity"], 1)

    return max(0, min(100, 100 - penalty))


def status_for_score(score):
    if score >= 85:
        return "Ready"
    if score >= 65:
        return "Needs remediation"
    return "High deployment risk"


# -----------------------------
# Page content
# -----------------------------

st.title("Data Deployment Readiness Copilot")

st.write(
    """
    This prototype assesses whether enterprise customer data is ready for a
    CRM, analytics, or AI deployment.
    """
)

st.info(
    """
    Prototype note: This application uses synthetic data. Findings are
    calculated deterministically and should be reviewed before production use.
    """
)

sample_data = create_sample_data()

with st.sidebar:
    st.header("Data source")
    uploaded_file = st.file_uploader(
        "Upload a CSV file",
        type=["csv"],
    )

data = load_csv(uploaded_file, sample_data)

remediation_plan = [
    "Review critical duplicate identifiers and establish canonical IDs.",
    "Resolve missing values in fields required for the target workflow.",
    "Correct invalid email addresses before engagement workflows.",
    "Refresh stale records and confirm the source update process.",
    "Re-run validation after remediation.",
]

issues = run_quality_checks(data)
score = calculate_score(issues)
status = status_for_score(score)
checks = issues.to_dict(orient="records")
risks = [
    check for check in checks if check["severity"] in {"Critical", "High"}
]

assessment = {
    "target_use_case": "CRM, analytics, or AI deployment",
    "readiness_score": score,
    "readiness_status": status,
    "checks": checks,
    "risks": risks,
    "remediation_plan": remediation_plan,
}

st.header("Deployment readiness")

metric_one, metric_two, metric_three = st.columns(3)
metric_one.metric("Readiness score", f"{score}/100")
metric_two.metric("Status", status)
metric_three.metric("Issues detected", len(issues))

if score >= 85:
    st.success("The data appears ready for the next deployment phase.")
elif score >= 65:
    st.warning("Remediate the highest-priority issues before deployment.")
else:
    st.error("The data presents significant deployment risk.")

st.header("Data-quality findings")

if issues.empty:
    st.success("No issues detected.")
else:
    st.dataframe(
        issues,
        use_container_width=True,
        hide_index=True,
    )

st.header("Executive summary")

if issues.empty:
    st.write("No material data-quality issues were detected in the supplied data.")
else:
    highest_priority = issues.iloc[0]
    st.write(
        f"""
        The assessment reviewed {len(data)} rows and {len(data.columns)} columns.

        The highest-priority finding is **{highest_priority["issue"]}**.
        The recommended next step is to **{highest_priority["recommendation"]}**
        """
    )

st.header("Recommended remediation plan")

for number, recommendation in enumerate(remediation_plan, start=1):
    st.write(f"{number}. {recommendation}")

st.divider()
st.subheader("Ask the Data Readiness Agent")

user_question = st.text_input(
    "Ask a question about this assessment",
    placeholder=(
        "What are the biggest risks to deploying an AI sales assistant "
        "on this data?"
    ),
)

if st.button("Ask Agent"):
    if not user_question.strip():
        st.warning("Enter a question first.")
    else:
        with st.spinner("Analyzing the readiness assessment..."):
            try:
                answer = run_readiness_agent(
                    user_question=user_question,
                    assessment=assessment,
                )
            except Exception as error:
                error_detail = str(error)
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    error_detail = error_detail.replace(api_key, "[redacted]")

                st.error(f"The agent request failed ({type(error).__name__}).")
                with st.expander("Technical details"):
                    st.code(error_detail or "No additional error details provided.")
            else:
                st.markdown(answer)

st.header("Source data preview")
st.dataframe(data, use_container_width=True, hide_index=True)

st.caption(
    """
    Production considerations: authentication, tenant isolation, data lineage,
    audit logging, monitoring, formal evaluation, and human approval before
    customer-facing actions.
    """
)

st.header("Planned AI capability")

st.write(
    """
    The next version would use a hosted foundation model to explain the
    deterministic findings, suggest source-to-target field mappings, prioritize
    remediation actions, and draft a customer-facing summary.
    """
)

st.code(
    """
Python calculates:
- Missing values
- Duplicate identifiers
- Invalid emails
- Stale records

The LLM handles:
- Semantic field mapping
- Explanation
- Prioritization
- Customer-facing communication
""",
    language="text",
)

st.warning(
    """
    The LLM would not be the source of truth for quality metrics. It would
    interpret trusted findings produced by deterministic code.
    """
)