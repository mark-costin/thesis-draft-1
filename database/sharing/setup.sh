#!/usr/bin/env bash
# =====================================================================
# export.sh
# Run on YOUR laptop. Exports the CDSS database structure (and, only if
# you confirm the data is fake, the data) into a file a groupmate can
# load with setup.sh.
#
# Usage (from the project folder):
#   bash database/sharing/export.sh                 # structure only
#   bash database/sharing/export.sh --with-data     # structure + data
#
# Options (environment variables):
#   SOURCE_DB  database to export      (default: cdss_test)
#   PGHOST     server                  (default: localhost)
#   PGUSER     user                    (default: postgres)
#   OUT_DIR    where to write the file (default: database/share)
# =====================================================================
set -euo pipefail

SOURCE_DB="${SOURCE_DB:-cdss_test}"
export PGHOST="${PGHOST:-localhost}"
export PGUSER="${PGUSER:-postgres}"
OUT_DIR="${OUT_DIR:-database/share}"
WITH_DATA=false

for arg in "$@"; do
  case "$arg" in
    --with-data) WITH_DATA=true ;;
    -h|--help)   sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg (use --with-data or --help)"; exit 1 ;;
  esac
done

for tool in pg_dump psql; do
  command -v "$tool" >/dev/null || { echo "ERROR: $tool not found. Install the PostgreSQL client tools."; exit 1; }
done

# Ask for the password once, unless it is already set in this terminal.
if [ -z "${PGPASSWORD:-}" ]; then
  read -r -s -p "Password for $PGUSER@$PGHOST: " PGPASSWORD; echo
  export PGPASSWORD
fi

psql -d "$SOURCE_DB" -tAc "SELECT 1" >/dev/null \
  || { echo "ERROR: cannot connect to database '$SOURCE_DB'."; exit 1; }

# Warn if the database has not had migration v2.
has_v2=$(psql -d "$SOURCE_DB" -tAc \
  "SELECT to_regclass('public.schema_version') IS NOT NULL
          AND EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'risk_results')")
if [ "$has_v2" != "t" ]; then
  echo "WARNING: '$SOURCE_DB' does not look migrated to v2 (no risk_results table)."
  read -r -p "Export it anyway? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 1; }
fi

if $WITH_DATA; then
  echo
  echo "You asked to include DATA. Patient health records are sensitive personal"
  echo "information under the Data Privacy Act (RA 10173). Only share data that"
  echo "is fake / made up for testing."
  read -r -p "Type FAKE to confirm the data contains no real patients: " confirm
  [ "$confirm" = "FAKE" ] || { echo "Cancelled. Run without --with-data to share structure only."; exit 1; }
  OUT_FILE="$OUT_DIR/cdss_full_v2.sql"
  DUMP_ARGS=()
else
  OUT_FILE="$OUT_DIR/cdss_schema_v2.sql"
  DUMP_ARGS=(--schema-only)
fi

mkdir -p "$OUT_DIR"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

pg_dump -d "$SOURCE_DB" "${DUMP_ARGS[@]}" --no-owner --no-privileges -f "$TMP_FILE"

# A structure-only export would leave the migration bookkeeping tables
# empty, so the copy would look un-migrated. Append just their rows
# (no patient data in them).
if ! $WITH_DATA; then
  bookkeeping=()
  for t in schema_version migration_v2_fk_changes; do
    [ "$(psql -d "$SOURCE_DB" -tAc "SELECT to_regclass('public.$t') IS NOT NULL")" = "t" ] \
      && bookkeeping+=(-t "public.$t")
  done
  if [ ${#bookkeeping[@]} -gt 0 ]; then
    pg_dump -d "$SOURCE_DB" --data-only --no-owner --no-privileges "${bookkeeping[@]}" >> "$TMP_FILE"
  fi
fi

# Remove the \restrict / \unrestrict lines that pg_dump 18 adds: they are
# psql-only commands, and without them the file also runs in DBeaver.
sed -e '/^\\restrict /d' -e '/^\\unrestrict /d' "$TMP_FILE" > "$OUT_FILE"

echo
echo "Exported '$SOURCE_DB' to $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
if $WITH_DATA; then
  echo "This file contains DATA. Send it directly; do not commit it to git."
else
  echo "Structure only, no patient data (just the migration version rows). Safe to send or commit."
fi
echo "Your groupmate loads it with:  bash database/sharing/setup.sh $OUT_FILE"