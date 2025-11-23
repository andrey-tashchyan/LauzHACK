# AML Intelligence System

**LauzHACK 2025 - UBS Track**

An advanced Anti-Money Laundering (AML) detection and analysis system that leverages AI agents to identify suspicious financial activities, analyze transaction patterns, and generate comprehensive compliance reports.

## Overview

This project implements a multi-agent AI system designed to detect money laundering activities through sophisticated pattern recognition and behavioral analysis. Built for the UBS track at LauzHACK, it provides compliance officers with powerful tools to identify high-risk transactions, suspicious counterparties, and potential financial crimes.

## Key Features

### 1. Multi-Agent Architecture
- **Agent Router**: Intelligent query routing system that classifies user questions and dispatches them to specialized agents
- **Suspicious Activity Agent**: Detects and analyzes potential money laundering patterns
- **Company Information Agent**: Provides detailed insights about business entities and their risk profiles
- **Account Activity Agent**: Monitors and analyzes individual account behaviors

### 2. Advanced AML Detection Features

Our system analyzes **11 distinct risk indicators**:

- **Transaction Frequency Analysis**: Detects unusual transaction volumes and patterns
- **Burst & Structuring Detection**: Identifies rapid transaction bursts and amounts just below reporting thresholds (smurfing)
- **Atypical Amount Detection**: Uses statistical analysis (IQR method) to identify outlier transactions
- **Cross-Border Activity**: Flags transactions involving high-risk jurisdictions
- **Counterparty Analysis**: Examines the risk profile of transaction partners
- **Transaction Irregularity**: Detects unusual timing patterns and behavioral anomalies
- **Night Activity Monitoring**: Identifies suspicious after-hours transactions
- **Ephemeral Account Detection**: Finds accounts with short lifespans and rapid fund movement
- **Account Age Analysis**: Flags newly created accounts with high activity
- **Abnormal Activity Patterns**: Detects sudden changes in account behavior
- **Account Multiplicity**: Identifies potential shell networks and connected entities

### 3. AI-Powered Reporting

- **Natural Language Report Generation**: Converts technical analysis into clear, actionable compliance reports
- **Risk Scoring System**: Provides 0-100 risk scores with LOW/MEDIUM/HIGH classifications
- **Executive Summaries**: Generates concise alerts suitable for dashboards and immediate review
- **JSON Export**: Structured data output for integration with compliance systems

### 4. Mass Analysis Capabilities

- Batch processing for analyzing multiple accounts
- Top suspects identification and ranking
- Comprehensive dataset-wide pattern detection

## Project Structure

```
LauzHACK/
├── agent_router.py              # Main routing agent
├── suspicious_agent.py          # Suspicious activity detection
├── company_agent.py             # Company information queries
├── account_agent.py             # Account activity analysis
├── aml_utils.py                 # Shared utility functions
│
├── features/                    # AML detection modules
│   ├── run_all_features.py      # Orchestrates all feature analysis
│   ├── ai_report_generator.py  # Natural language report generation
│   ├── analyze_top_suspects.py # Top suspect identification
│   ├── mass_analysis.py         # Batch processing
│   │
│   ├── feature_frequency.py              # Transaction frequency analysis
│   ├── feature_burst_structuring.py      # Burst & structuring detection
│   ├── feature_atypical_amounts.py       # Outlier amount detection
│   ├── feature_cross_border.py           # Cross-border risk analysis
│   ├── feature_counterparties.py         # Counterparty risk assessment
│   ├── feature_irregularity.py           # Transaction irregularity detection
│   ├── feature_night_activity.py         # After-hours activity monitoring
│   ├── feature_ephemeral_account.py      # Ephemeral account detection
│   ├── feature_account_age.py            # Account age analysis
│   ├── feature_abnormal_activity.py      # Abnormal behavior detection
│   └── feature_account_multiplicity.py   # Shell network identification
│
├── client_anomaly_detection.py  # Client anomaly detection
├── client_anomaly_detection.ipynb # Jupyter notebook for exploration
│
└── utils/                       # Routing utilities
    └── router.py
```

## How It Works

### 1. Data Ingestion
The system processes financial transaction data including:
- Transaction records (amounts, timestamps, counterparties)
- Account information (creation dates, ownership)
- Partner/entity details (business profiles, jurisdictions)

### 2. Feature Analysis
Each transaction and account is analyzed across 11 risk dimensions. For example:

- **Structuring Detection**: Identifies transactions of $9,500 (just below the $10,000 reporting threshold)
- **Cross-Border Risk**: Flags transactions to/from high-risk jurisdictions (based on FATF lists)
- **Ephemeral Accounts**: Detects accounts opened, used heavily, and quickly closed

### 3. Risk Scoring
Each feature generates:
- **Risk Score** (0-100): Quantitative measure of suspiciousness
- **Risk Level** (LOW/MEDIUM/HIGH): Categorical classification
- **Risk Reasons**: Specific justifications for the score
- **Metrics**: Detailed measurements supporting the analysis

### 4. Report Generation
The AI report generator converts technical JSON output into natural language reports that:
- Provide executive summaries for quick decision-making
- Detail specific findings for each risk indicator
- Recommend actions based on overall risk level
- Include audit trails for compliance documentation
- 
```

## Technical Stack

- **Python 3.8+**: Core programming language
- **Pandas**: Data manipulation and analysis
- **NumPy**: Statistical computations
- **LangChain**: Agent orchestration and routing
- **Together AI**: LLM integration for natural language processing
- **Jupyter**: Interactive data exploration

## LauzHACK 2025 - UBS Track

This project was developed for the UBS Anti-Money Laundering challenge at LauzHACK 2025. It demonstrates:

- Advanced pattern recognition in financial data
- AI-powered compliance automation
- Multi-agent system architecture
- Natural language interfaces for complex financial analysis
- Scalable risk detection frameworks

## Team

Built with passion for financial compliance and AI innovation at LauzHACK 2025.

---

**Note**: This is a prototype system developed in a hackathon environment. Production deployment would require additional security hardening, regulatory compliance validation, and integration with existing banking systems.
