from agent_service import run_readiness_agent
from datetime import timedelta
import os

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Data Deployment Readiness Copilot",
    page_icon="✅",
    layout="wide",
)


def create_sample_data():
    """Create synthetic enterprise customer data for the demo."""
    accounts = pd.DataFrame(
        [
            {
                "account_id": "A1001",
                "account_name": "Acme Wireless",
                "segment": "Enterprise",
                "industry": "Telecommunications",
                "last_updated": "2025-01-15",
            },
            {
                "account_id": "A1002",
                "account_name": "Globex Corporation",
                "segment": "Enterprise",
                "industry": "Technology",
                "last_updated": "2025-04-15",
            },
            {
                "account_id": "A1002",
                "account_name": "Globex Corporation Duplicate",
                "segment": "Enterprise",
                "industry": "Technology",
                "last_updated": "2025-04-15",
            },
            {
                "account_id": "A1003",
                "account_name": "Initech Communications",
                "segment": "",
                "industry": "Telecommunications",
                "last_updated": "2023-02-20",
            },
        ]
    )

    contacts = pd.DataFrame(
        [
            {
                "contact_id": "C1001",
                "account_id": "A1001",
                "email": "maya@achme.com",
                "contact_type": "Technical",
            },
            {
                "contact_id": "C1002",
                "account_id": "A1001",
                "email": "leo@northstarmedia.com",
                "contact_type": "Executive",
            },
            {
                "contact_id": "C1003",
                "account_id": "A9999",
                "email": "invalid-email",
                "contact_type": "Technical",
            },
            {
                "contact_id": "C1004",
                "account_id": "A1003",
                "email": "",
                "contact_type": "Operations",
            },
        ]
    )

    opportunities = pd.DataFrame(
        [
            {
                "opportunity_id": "O1001",
                "account_id": "A1001",
                "amount": 250000,
                "stage": "Proposal",
                "close_date": "2025-06-30",
            },
            {
                "opportunity_id": "O1002",
                "account_id": "A1002",
                "amount": 125000,
                "stage": "Negotiation",
                "close_date": "",
            },
            {
                "opportunity_id": "O1003",
                "account_id": "A9999",
                "amount": 75000,
                "stage": "Discovery",
                "close_date": "2025-11-15",
            },
        ]
    )

    return accounts, contacts, opportunities


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
        return len(df)

    values = df[column]
    missing = values.isna()

    if values.dtype == "object":
        missing = missing | values.fillna("").astype(str).str.strip().eq("")

    return int(missing.sum())


def run_quality_checks(accounts, contacts, opportunities):
    """Run deterministic data quality checks."""
    issues = []

    required_fields = {
        "accounts": {
            "data": accounts,
            "columns": ["account_id", "account_name", "segment"],
        },
        "contacts": {
            "data": contacts,
            "columns": ["contact_id", "account_id", "email"],
        },
        "opportunities": {
            "data": opportunities,
            "columns": ["opportunity_id", "account_id", "close_date"],
        },
    }

    for dataset_name, config in required_fields.items():
        df = config["data"]
        for column in config["columns"]:
            count = missing_values(df, column)
            if count > 0:
                issues.append(
                    {
                        "severity": "High",
                        "category": "Completeness",
                        "dataset": dataset_name,
                        "issue": f"Missing values in {column}",
                        "count": count,
                        "recommendation": f"Populate {column} before enabling production workflows.",
                    }
                )

    if "account_id" in accounts.columns:
        duplicate_count = int(accounts["account_id"].duplicated(keep=False).sum())
        if duplicate_count > 0:
            issues.append(
                {
                    "severity": "Critical",
                    "category": "Uniqueness",
                    "dataset": "accounts",
                    "issue": "Duplicate account IDs",
                    "count": duplicate_count,
                    "recommendation": "Establish a canonical account ID and merge duplicates.",
                }
            )

    if "account_id" in accounts.columns:
        account_ids = set(accounts["account_id"].dropna().astype(str))

        for dataset_name, df in [
            ("contacts", contacts),
            ("opportunities", opportunities),
        ]:
            if "account_id" not in df.columns:
                continue

            child_ids = df["account_id"].fillna("").astype(str)
            orphaned_count = int((~child_ids.isin(account_ids)).sum())
            if orphaned_count > 0:
                issues.append(
                    {
                        "severity": "Critical",
                        "category": "Referential Integrity",
                        "dataset": dataset_name,
                        "issue": "Records reference non-existent accounts",
                        "count": orphaned_count,
                        "recommendation": "Resolve orphaned records before account level reporting.",
                    }
                )

    if "email" in contacts.columns:
        email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        invalid_emails = ~contacts["email"].fillna("").astype(str).str.match(email_pattern)
        invalid_count = int(invalid_emails.sum())

        if invalid_count > 0:
            issues.append(
                {
                    "severity": "Medium",
                    "category": "Validity",
                    "dataset": "contacts",
                    "issue": "Invalid or missing email addresses",
                    "count": invalid_count,
                    "recommendation": "Validate contact email addresses before engagement workflows.",
                }
            )

    close_date_count = missing_values(opportunities, "close_date")
    if close_date_count > 0:
        issues.append(
            {
                "severity": "Medium",
                "category": "Completeness",
                "dataset": "opportunities",
                "issue": "Opportunities missing close dates",
                "count": close_date_count,
                "recommendation": "Require close dates for forecasting and pipeline reporting.",
            }
        )

    if "last_updated" in accounts.columns:
        updated_dates = pd.to_datetime(accounts["last_updated"], errors="coerce")
        stale_cutoff = pd.Timestamp.today() - pd.Timedelta(days=365)
        stale_count = int((updated_dates < stale_cutoff).sum())

        if stale_count > 0:
            issues.append(
                {
                    "severity": "Medium",
                    "category": "Freshness",
                    "dataset": "accounts",
                    "issue": "Account records are more than one year old",
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

accounts_sample, contacts_sample, opportunities_sample = create_sample_data()

with st.sidebar:
    st.header("Data sources")

    accounts_file = st.file_uploader(
        "Upload accounts CSV",
        type=["csv"],
    )

    contacts_file = st.file_uploader(
        "Upload contacts CSV",
        type=["csv"],
    )

    opportunities_file = st.file_uploader(
        "Upload opportunities CSV",
        type=["csv"],
    )

accounts = load_csv(accounts_file, accounts_sample)
contacts = load_csv(contacts_file, contacts_sample)
opportunities = load_csv(opportunities_file, opportunities_sample)

remediation_plan = [
    "Establish a canonical account identifier.",
    "Resolve duplicate and orphaned records.",
    "Confirm required field definitions with business stakeholders.",
    "Re-run validation after remediation.",
    "Add authenticated enterprise-platform connectors.",
    "Add AI-assisted field mapping only after the underlying metrics are trusted.",
]

issues = run_quality_checks(accounts, contacts, opportunities)
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
        The assessment reviewed {len(accounts)} accounts,
        {len(contacts)} contacts, and {len(opportunities)} opportunities.

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

accounts_tab, contacts_tab, opportunities_tab = st.tabs(
    ["Accounts", "Contacts", "Opportunities"]
)

with accounts_tab:
    st.dataframe(accounts, use_container_width=True, hide_index=True)

with contacts_tab:
    st.dataframe(contacts, use_container_width=True, hide_index=True)

with opportunities_tab:
    st.dataframe(
        opportunities,
        use_container_width=True,
        hide_index=True,
    )

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
- Duplicate IDs
- Orphaned records
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

st.divider()