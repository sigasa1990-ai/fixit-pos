# FIXIT POS — Restore Procedure

## Prerequisites

- PostgreSQL 16 client tools (`pg_restore`, `psql`)
- Backup file (`.sql.gz` or custom format `.dump`)
- Database credentials
- Network access to target database

## Quick Restore

```bash
# 1. Extract backup (if compressed with gzip)
gunzip -k /backup/fixit_pos_20260101_120000.sql.gz

# 2. Restore to database
PGPASSWORD="your_password" pg_restore \
    -h your-host \
    -p 5432 \
    -U fixit \
    -d fixit_pos \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    --verbose \
    /backup/fixit_pos_20260101_120000.sql

# 3. Verify restoration
PGPASSWORD="your_password" psql \
    -h your-host -U fixit -d fixit_pos \
    -c "SELECT COUNT(*) FROM sales;"
```

## Restore from S3 Backup

```bash
# 1. Download backup from S3
aws s3 cp s3://fixit-pos-backups/production/fixit_pos_20260101_120000.sql.gz /tmp/

# 2. Verify checksum
cat /tmp/fixit_pos_20260101_120000.info | grep checksum

# 3. Restore (see steps above)
```

## Disaster Recovery (Full Database Loss)

```bash
# 1. Create database
PGPASSWORD="your_password" psql -h your-host -U fixit -d postgres \
    -c "CREATE DATABASE fixit_pos OWNER fixit;"

# 2. Grant permissions
PGPASSWORD="your_password" psql -h your-host -U fixit -d fixit_pos \
    -c "GRANT ALL ON DATABASE fixit_pos TO fixit;"

# 3. Restore from latest backup
PGPASSWORD="your_password" pg_restore \
    -h your-host -U fixit -d fixit_pos \
    --no-owner --no-acl --clean --if-exists \
    /backup/most_recent_backup.sql.gz

# 4. Run Alembic migrations (in case backup is older)
cd /app && alembic upgrade head

# 5. Verify critical data
PGPASSWORD="your_password" psql -h your-host -U fixit -d fixit_pos <<EOF
    SELECT 'tenants' as tbl, COUNT(*) FROM tenants
    UNION ALL
    SELECT 'users', COUNT(*) FROM users
    UNION ALL
    SELECT 'products', COUNT(*) FROM products
    UNION ALL
    SELECT 'sales', COUNT(*) FROM sales
    UNION ALL
    SELECT 'inventory', COUNT(*) FROM inventory
    UNION ALL
    SELECT 'cash_registers', COUNT(*) FROM cash_registers;
EOF
```

## Point-in-Time Recovery

If WAL archiving is configured:

```bash
# 1. Restore base backup
pg_restore -h your-host -U fixit -d fixit_pos \
    --no-owner --no-acl --clean \
    /backup/base_backup.sql.gz

# 2. Configure recovery.conf or use pg_rewind
# 3. Apply WAL up to desired timestamp
```

## Validation Checklist

After restore, verify:

- [ ] All tenants exist: `SELECT COUNT(*) FROM tenants`
- [ ] Users can login: Test with known credentials
- [ ] Sales data intact: `SELECT COUNT(*) FROM sales WHERE status = 'completed'`
- [ ] Inventory quantities correct: `SELECT SUM(quantity) FROM inventory`
- [ ] Cash register balances match: `SELECT SUM(current_balance) FROM cash_registers`
- [ ] Folio sequences are correct: `SELECT * FROM folio_controls`
- [ ] Recent audits present: `SELECT COUNT(*) FROM audit_logs WHERE created_at > NOW() - INTERVAL '1 day'`
- [ ] API health check passes: `curl http://localhost:8000/health`

## Critical Notes

- **NEVER** run `DROP DATABASE` in production
- **ALWAYS** test restore on staging first
- **KEEP** at least 30 days of backups
- **STORE** backups in a different region/availability zone
- **DOCUMENT** every restore with timestamp and reason
- **TEST** restore procedure monthly
