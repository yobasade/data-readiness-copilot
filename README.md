# Data Deployment Readiness Copilot

A Streamlit prototype that assesses whether enterprise customer data is ready
for a CRM, analytics, or AI deployment.

## Problem

Enterprise data often contains missing fields, duplicate identifiers, invalid
values, stale records, and broken relationships. These issues create risk for
reporting, automation, and AI workflows.

## What the prototype does

- Loads account, contact, and opportunity data
- Runs deterministic data-quality checks
- Calculates a deployment-readiness score
- Identifies high-priority risks
- Produces a remediation plan
- Displays the underlying source records


## Future improvements

The application calculates data-quality metrics deterministically using Python and Pandas. A future AI layer would be used for semantic field mapping, explanation, prioritization, and communication—not for inventing metrics.

    •    Amazon Bedrock integration
    •    Salesforce or enterprise-platform connectors
    •    Authentication and tenant isolation
    •    Data lineage and audit logging
    •    Formal evaluation datasets
    •    Human approval before customer-facing actions
    •    Production monitoring and alerting


## Architecture

```text
CSV data
   ↓
Pandas data profiling
   ↓
Deterministic data-quality checks
   ↓
Readiness score
   ↓
Remediation plan
   ↓
Streamlit interface

