Quick start: run MailHog (or docker compose up) and python phish_sim.py. 

Safety & authorization: explicit statement that the tool is for authorized testing only; list excluded groups (HR, legal, execs) and required approvals. 

Data model & exports: describe CSV schema and retention policy.

How to run campaigns: sample curl or form usage for /send_campaign.

How to review results: MailHog UI and CSV export locations. 

Security, privacy, and legal best practices
Do not send to real external addresses during testing; use MailHog or isolated SMTP. 

Never commit secrets; provide .env.example and add .env to .gitignore.

Obtain written authorization from stakeholders and document scope, exclusions, and remediation steps. 

Minimize PII in logs and exports; rotate or anonymize tokens after reporting. 

Recommended repo hygiene & CI
Add unit tests for token generation, event logging, and CSV export.

Add a pre-commit config to block accidental commits of large DB or .env.

Provide a docker-compose.yml that brings up MailHog + app for one-command local testing. 
