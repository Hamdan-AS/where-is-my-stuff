# Cloud deployment practice

Use the `where-is-my-stuff` repository.
V2 has redesigned templates, private item photos, owner-managed six-month QR labels,
and adversarial, image, QR, and PostgreSQL concurrency tests. Account follow-up features
and production deployment remain unfinished. See `README.md` for current feature status.

## Choosing a cloud

| Cloud | Suggested route | What you practice | My assessment |
| --- | --- | --- | --- |
| AWS | Elastic Beanstalk + RDS PostgreSQL | IAM, networking, application environments, logs, database lifecycle | Best if your goal is learning AWS infrastructure; more moving parts |
| Microsoft Azure | Linux App Service + PostgreSQL Flexible Server | Managed app deployment, environment settings, logs, GitHub delivery | My recommendation for a first deployment of this app |
| Google Cloud | Cloud Run + Cloud SQL | Containers, revisions, service accounts, secrets, jobs | Good for learning containers; private file storage needs adaptation |

These learning assessments are judgments, not benchmarks. AI model rankings
do not determine Django hosting quality. Prices depend on region and resources;
check the provider's estimate before creating anything.

Official walkthroughs:

- AWS: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-django.html
- Azure: https://learn.microsoft.com/en-us/azure/app-service/tutorial-python-postgresql-app-django
- Google: https://docs.cloud.google.com/python/django/run

## What is prepared

`config.production` is separate from local settings. It requires a random secret,
explicit hosts, PostgreSQL, and an absolute path for durable private media. It
enables secure cookies, HTTPS redirects, a short initial HSTS policy, console
logging, and WhiteNoise's compressed static manifest. Install
`requirements-production.txt` rather than only `requirements.txt` on the cloud.
`.env.production.example` lists variables; Django does not load that file itself.

The missing Leaflet source-map reference was removed so manifest collection works.
HSTS preload stays disabled for practice domains; `check --deploy` therefore
reports W021 intentionally. Do not register a temporary domain for preloading.

## First Azure exercise with this repository

1. Use a fresh database and fictional reports. Keep local `db.sqlite3`, private
   media, and demo credentials out of the deployment. This repository has
   existing uncommitted work; review the diff before committing it to a private
   GitHub repository.
2. Create a dedicated practice resource group. Follow the official Azure Django
   tutorial to create Linux App Service and PostgreSQL, choosing a supported
   Python version compatible with this project (3.12 is a suitable starting point).
   Review cost estimates and create a budget alert. Alerts are not a spending cap.
3. Set the variables in `.env.production.example` through App Service environment
   settings. Use the actual app hostname for allowed hosts (no scheme) and its
   HTTPS origin for CSRF. Supply a PostgreSQL URL, including `?sslmode=require`.
   URL-encode special characters in database credentials. Generate a fresh secret
   locally with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
4. Mount durable private storage and set `DJANGO_MEDIA_ROOT` to its absolute mount
   path. Confirm persistence across restart/redeploy. Do not map this directory
   to a public URL. Without a verified durable mount, photo and QR label storage
   is incomplete. App Service storage configuration depends on the deployment
   mode; verify it before uploading anything.
5. Deploy the repository with a build step that installs
   `requirements-production.txt` and runs `python manage.py collectstatic --noinput`
   using the production environment. Azure's default requirements discovery
   installs only `requirements.txt`, so explicitly install the production file
   in your build workflow. Never embed the secret or database URL in an artifact.
6. Before serving traffic, run `python manage.py migrate --noinput` once in the
   app environment. Create your own administrator with
   `python manage.py createsuperuser`. Do not import the local demonstration DB.
7. Set startup to `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile -`.
   Set `DJANGO_SETTINGS_MODULE=config.production`. Enable `DJANGO_TRUST_PROXY=1`
   only after confirming the trusted frontend overwrites `X-Forwarded-Proto`.
8. Run `python manage.py check --deploy`. Visit the HTTPS app; register two test
   accounts, publish opposite reports, review a match, and arrange a handover.
   Verify CSS/map assets, owner-only photos, and QR scans. Restart and redeploy,
   then verify reports and media still exist.
9. Practice one small update and a code rollback. Database migrations need their
   own rollback/backup plan. Inspect logs without printing contacts or matching
   answers. Export a PostgreSQL backup and copy the private media, then practice
   restoring both into a separate test environment.
10. Delete the dedicated practice resource group when done and verify the app,
    database, disks/storage, and any separately created resources are gone.

## Remaining before real campus use

This is deployment preparation, not a completed production rollout. Local
PostgreSQL migration, concurrent matching/reservation tests, and backup/restore
verification are complete; see POSTGRESQL.md. Login throttling, scheduled cloud
backups, durable cloud media, production load tests, and a security review
remain open.
Cloud Run and autoscaled AWS deployments should use private object storage
through an access-controlled storage backend rather than ephemeral local files.
No cloud resources were created by this change.
