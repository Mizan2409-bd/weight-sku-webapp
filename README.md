# Weight & SKU Management Web App (Starter)

## Features in this starter
- Multi-user login with Admin/User roles
- Central database (SQLite locally; PostgreSQL when DATABASE_URL is configured)
- Material master add/update/search
- Delivery entry and dashboard totals

## Local run
1. Install Python 3.10+
2. `python -m venv .venv`
3. Activate the environment
4. `pip install -r requirements.txt`
5. Set `ADMIN_PASSWORD` and `SECRET_KEY` environment variables
6. `flask --app app init-db`
7. `flask --app app run`

Default username: `admin`. Password is the `ADMIN_PASSWORD` value used for init-db; if omitted, `ChangeMe123!` (change it immediately).

## Cloud deployment
The included `render.yaml` is a deployment starting point for Render + PostgreSQL. Create the service, set a strong ADMIN_PASSWORD, and deploy. A public URL/domain and cloud database are required for real anywhere access.

## Important migration note
This is the first functional foundation, not a completed conversion of the workbook. The uploaded XLSM contains VBA and many interdependent sheets. Before production use, migrate and test each calculation/workflow: Product Variance, SKU Weight, Wrapper Weight, Weight Variation, SAP Delivery, Delivery, monthly/yearly schedules, truck summaries, Missing Check and Dashboard. Reconcile totals against the original workbook before importing live company data. Add HTTPS, backups, audit logs, password reset, permissions and validation before production.
