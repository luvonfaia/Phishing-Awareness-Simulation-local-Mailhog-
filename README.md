### Phishing Awareness Simulator README

---

### Quick Start
1. **Start MailHog for local testing**  
   - Run MailHog directly if installed, or use Docker:
   ```bash
   docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog
   ```
   MailHog SMTP listens on port **1025** and the web UI on **8025**.

2. **Create virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Prepare recipients file**  
   Create `recipients.csv` in the repository root with the header:
   ```
   email,cohort,employee_id
   ```

4. **Run the simulator**
   ```bash
   python phish_sim.py
   ```

---

### Run a Campaign
**Trigger a campaign using curl**
```bash
curl -X POST http://127.0.0.1:5000/send_campaign \
  -H "Content-Type: application/json" \
  -d '{"campaign_id":"test-campaign-001","template_id":"it_ticket"}'
```
If `campaign_id` or `template_id` are omitted the app will choose defaults.

**Where to inspect messages**  
Open the MailHog web UI at `http://127.0.0.1:8025` to view outgoing messages and inspect embedded tracking links.

---

### Endpoints and Exports
**Primary endpoints**
- **POST /send_campaign** — Start a campaign. Accepts JSON or form data: `campaign_id`, `template_id`.  
- **/track/open/{token}.png** — Open pixel used to log opens.  
- **/track/click/{token}** — Click tracking redirect to training page.  
- **/report/{token}** — Report endpoint for users to report suspicious messages.  
- **/training/{token}** — Micro lesson and 3 question quiz shown after a click.  
- **GET or POST /export_weekly** — Generate per user and campaign CSV exports in `exports/`.

**CSV schema**
- **Per user export columns**
  - `user_email`  
  - `cohort`  
  - `campaign_id`  
  - `template_id`  
  - `opened` (boolean)  
  - `clicked` (boolean)  
  - `reported` (boolean)  
  - `training_completed` (boolean)  
  - `quiz_score` (0-3 or blank)  
  - `time_to_report_min` (minutes or blank)

- **Campaign summary export columns**
  - `campaign_id`  
  - `target_count`  
  - `click_rate_pct`  
  - `report_rate_pct`  
  - `median_time_to_report_min`

Exports are written to the `exports/` directory. Adjust retention and rotation to meet your data policy.

---

### Safety Authorization and Legal Guidance
**This tool is for authorized testing only.** Obtain written approval from stakeholders including IT, HR, and Legal before running campaigns outside a controlled test environment. **Exclude sensitive groups** such as HR, Legal, executives, and any users under special protection. Document scope, allowed targets, and remediation steps before launch.

**Minimum safeguards**
- Use MailHog or an isolated SMTP sink during development.  
- Do not point to production SMTP servers without approvals and proper SPF/DKIM alignment.  
- Keep the simulator and exports on secure infrastructure with access controls and logging.

---

### Security Privacy and Repository Files
**Do not commit secrets**. Provide a `.env.example` and add `.env` to `.gitignore`. **Minimize PII** in logs and exports; anonymize or rotate tokens after reporting. Define and document a data retention policy in `SECURITY.md`.

**Recommended repository files**
- `phish_sim.py` — Main application script.  
- `recipients.csv.example` — Example recipients file.  
- `requirements.txt` — Pinned Python dependencies.  
- `docker-compose.yml` — Compose file to run the app and MailHog locally.  
- `templates/` — Email templates used by the app.  
- `README.md` — This file.  
- `CONTRIBUTING.md` — Contribution and review guidelines.  
- `SECURITY.md` — Responsible disclosure and data handling.  
- `LICENSE` — Open source license such as MIT or Apache 2.0.  
- `.gitignore` — Exclude `sim.db`, `exports/`, `.env`, and other sensitive files.

