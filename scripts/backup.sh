#!/bin/bash
# FIXIT POS — PostgreSQL Backup Script
# Usage: ./backup.sh [backup_dir]
# Environment: POSTGRES_PASSWORD must be set
set -euo pipefail

BACKUP_DIR="${1:-/backup}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/fixit_pos_${TIMESTAMP}.sql.gz"
BACKUP_INFO="${BACKUP_DIR}/fixit_pos_${TIMESTAMP}.info"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-fixit_pos}"
DB_USER="${DB_USER:-fixit}"
S3_BUCKET="${S3_BUCKET:-}"
ENVIRONMENT="${ENVIRONMENT:-production}"

echo "========================================"
echo "FIXIT POS Backup - ${TIMESTAMP}"
echo "Environment: ${ENVIRONMENT}"
echo "Database: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "========================================"

# Verify connectivity
PGPASSWORD="${POSTGRES_PASSWORD}" pg_isready \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
    || { echo "ERROR: Database not reachable"; exit 1; }

# Create backup with compression
echo "Creating backup: ${BACKUP_FILE}"
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-owner \
    --no-acl \
    --format=custom \
    --compress=9 \
    --file="${BACKUP_FILE}" \
    --verbose 2>&1 | tail -5

# Verify backup integrity
echo "Verifying backup integrity..."
pg_restore --list "${BACKUP_FILE}" > /dev/null 2>&1 \
    && echo "Backup integrity: OK" \
    || { echo "ERROR: Backup integrity check failed"; exit 1; }

# Generate backup metadata
cat > "${BACKUP_INFO}" << EOF
{
  "filename": "$(basename ${BACKUP_FILE})",
  "timestamp": "${TIMESTAMP}",
  "environment": "${ENVIRONMENT}",
  "database": "${DB_NAME}",
  "host": "${DB_HOST}",
  "size_bytes": $(stat -c%s "${BACKUP_FILE}" 2>/dev/null || echo 0),
  "pg_version": "$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -t -c 'SELECT version()' 2>/dev/null | head -1)",
  "checksum": "$(sha256sum ${BACKUP_FILE} | cut -d' ' -f1)"
}
EOF

echo "Backup metadata: ${BACKUP_INFO}"

# Upload to S3 if configured
if [ -n "${S3_BUCKET}" ]; then
    echo "Uploading to S3: s3://${S3_BUCKET}/${ENVIRONMENT}/"
    aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/${ENVIRONMENT}/" --no-progress
    aws s3 cp "${BACKUP_INFO}" "s3://${S3_BUCKET}/${ENVIRONMENT}/" --no-progress
    echo "S3 upload complete"
fi

# Rotate old backups
echo "Removing backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "fixit_pos_*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -name "fixit_pos_*.info" -type f -mtime "+${RETENTION_DAYS}" -delete
echo "Cleanup complete"

echo "========================================"
echo "Backup completed successfully"
echo "File: ${BACKUP_FILE}"
echo "Size: $(du -h ${BACKUP_FILE} | cut -f1)"
echo "========================================"
