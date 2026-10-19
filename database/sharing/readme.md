# Setting up the CDSS database

This folder lets a groupmate create their own copy of the CDSS database on
their own laptop for testing. Each copy is completely separate: nothing done
on one laptop affects anyone else's database.

| File | Who uses it | Importance | What it does |
|---|---|---|---|
| `cdss_schema_v2.sql` | Groupmate | **Essential** | The database structure itself (created by `export.sh`) |
| `setup.sh` | Groupmate | Recommended | Creates the database from `cdss_schema_v2.sql` in one safe step. Without it, use the DBeaver-only route under Troubleshooting |
| `share_seed.sql` | Groupmate | Optional | Fake sample patients for testing |
| `README.md` | Everyone | Helpful | These instructions |
| `export.sh` | Database owner only | Owner's tool | Exports the database structure to `cdss_schema_v2.sql`; groupmates don't need it |

**Groupmate:** follow Part 2. **Database owner:** Part 1 is for you.

---

## Part 1: Database owner (export)

Run from the project folder:

```bash
bash database/sharing/export.sh
```

It asks for your PostgreSQL password, then writes
`database/sharing/cdss_schema_v2.sql`. By default it exports from `cdss_test`;
to export from another database, run
`SOURCE_DB=postgres bash database/sharing/export.sh`.

The file contains the **structure only**: tables, columns, constraints and
the migration version, with **no patients or users**. It is safe to send or
commit.

Send your groupmate `cdss_schema_v2.sql`, `setup.sh`, `share_seed.sql` and
this `README.md`, or commit them so they arrive with the project. At minimum
they need `cdss_schema_v2.sql`.

**When the database changes, export again.** After any new migration or
structure change, re-run `export.sh` and send or commit the new
`cdss_schema_v2.sql`. A groupmate's copy never updates by itself: they
reload it with `bash database/sharing/setup.sh database/sharing/cdss_schema_v2.sql --replace`,
which deletes their old copy, test data included.

After the real database (`postgres`) has been migrated and `cdss_test` is
deleted, export with `SOURCE_DB=postgres bash database/sharing/export.sh`.
Exporting an un-migrated database shows a warning; answer `N` and migrate it
first.

> **Sharing data.** `bash database/sharing/export.sh --with-data` includes all
> rows and asks you to type `FAKE` to confirm. Only use it if the data is made
> up. Real patient health records are sensitive personal information under
> the Data Privacy Act of 2012 (RA 10173) and must not be shared. Never commit
> a data export: keep `database/sharing/cdss_full_v2.sql` in `.gitignore`.

---

## Part 2: Groupmate (create the database)

### Step 1: Install PostgreSQL 18 and pgvector

The database uses the **pgvector** extension and was exported from
**PostgreSQL 18**. An older version may fail to load it.

Check what you have:

```bash
psql --version
```

If it's missing or below 18, install PostgreSQL 18 and pgvector from the
official PostgreSQL repository (<https://www.postgresql.org/download/>).
Typical package names are below; if yours differ, check the pgvector install
page (<https://github.com/pgvector/pgvector#installation>).

| System | Packages |
|---|---|
| Fedora | `postgresql18-server`, `pgvector_18` |
| Ubuntu / Debian | `postgresql-18`, `postgresql-18-pgvector` |
| Windows | PostgreSQL 18 installer from postgresql.org, then pgvector per its install page |

Make sure the server is running and you know the password of the `postgres`
user. It's the same password you use in DBeaver.

### Step 2: Put the files in place

Inside your copy of the project, the files go in `database/sharing/`:

```
database/sharing/cdss_schema_v2.sql
database/sharing/setup.sh
database/sharing/share_seed.sql
```

Check they arrived intact. None should show `0`:

```bash
wc -l database/sharing/*
```

### Step 3: Store your password for this terminal

Run this line **by itself**, type your password, and press Enter. Nothing
appears while you type; that's normal.

```bash
read -s -p "postgres password: " PGPASSWORD; export PGPASSWORD; echo
```

This stops every following command from asking for the password again.

### Step 4: Create the database

From the project folder:

```bash
bash database/sharing/setup.sh database/sharing/cdss_schema_v2.sql --sample-data
```

Leave out `--sample-data` if you want an empty database.

The script:

1. Checks it can connect, and warns if your PostgreSQL is older than 18.
2. Checks that pgvector is installed.
3. Creates a database named `cdss`. If that name already exists, it stops
   instead of overwriting.
4. Loads the structure in one transaction: if anything fails, nothing is
   half-loaded.
5. With `--sample-data`, adds the fake patients from `share_seed.sql`.

Success ends with:

```
Done: 'cdss' has 23 tables.
```

Useful options:

| Option | Effect |
|---|---|
| `--replace` | Deletes and recreates `cdss` if it already exists |
| `TARGET_DB=cdss_mine bash database/sharing/setup.sh ...` | Uses a different database name |
| `--help` | Shows all options |

### Step 5: Point the app at your database

In **your own** `.env` file in the project folder, set:

```
DATABASE_URL=postgresql://postgres:<your password>@localhost:5432/cdss
```

Replace `<your password>` with your own password. **Never commit `.env`**,
because it contains your password. Then restart the backend.

### Step 6: Check it in DBeaver (optional)

1. Right-click your PostgreSQL connection, choose **Edit Connection**, open the
   **PostgreSQL** tab, and tick **Show all databases**.
2. Press **F5** to refresh.
3. Open `cdss` → Schemas → public → Tables. You should see 23 tables,
   including `risk_results`, `shap_explanations`, `model_versions` and
   `documents`.

When you're done, run `unset PGPASSWORD` or close the terminal.

---

## About the sample data

`share_seed.sql` adds **made-up** records only: one sample doctor and three
patients, each with family history (T2D, CVD, CRD, NEURO) and a few clinical
readings. Some readings are left blank on purpose, to test optional inputs.

- **The sample accounts cannot log in.** Their passwords are placeholders.
  Register your own account through the app.
- It only runs on an **empty** database. If users already exist, it stops.
- Values such as `doctor`/`patient` for roles and `First-degree` for
  relationships may not match what the app expects. If something displays
  oddly, tell the database owner.

---

## Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| `Peer authentication failed for user "postgres"` | Connecting without `-h localhost` | The scripts already use `localhost`. For your own `psql` commands, add `-h localhost` |
| `fe_sendauth: no password supplied` | Several commands pasted at once; the password prompt swallowed the next lines | Do Step 3 first, on its own line |
| `cannot connect to PostgreSQL` | Server not running, or wrong password | Start PostgreSQL; on Linux, `sudo systemctl start postgresql-18` (the service name may differ). Redo Step 3 with the correct password |
| `the pgvector extension is not installed` | pgvector missing | Install pgvector for your PostgreSQL version (Step 1) |
| `database 'cdss' already exists` | It was created before | Add `--replace`, or use `TARGET_DB=another_name` |
| `No such file or directory` | Wrong folder, a file not saved, or a hidden space in a folder name | Run from the project folder. Check with `wc -l database/sharing/*` and `ls database \| cat -A`; a folder shown as `sharing $` has a trailing space, so fix it with `mv "database/sharing " database/sharing` |
| A file shows `0` lines | It was never saved | Paste the content again and press Ctrl+S |
| `WARNING: this server is PostgreSQL 16` | Older PostgreSQL | It may still work. If loading fails, install PostgreSQL 18 |

### No terminal? (DBeaver only)

1. In DBeaver, right-click **Databases** and choose **Create New Database**.
   Name it `cdss`.
2. Right-click `cdss` and choose **SQL Editor → Open SQL script**. Paste the
   contents of `cdss_schema_v2.sql`, then run it with **Execute SQL Script**
   (Alt+X), not Ctrl+Enter.
3. Optionally, do the same with `share_seed.sql`.
4. If any statement fails, delete the `cdss` database, create it again, and
   retry. A half-loaded database is not safe to use.

The terminal method is preferred: it checks your version and pgvector first,
and it loads everything as one unit.