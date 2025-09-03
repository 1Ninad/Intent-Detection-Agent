# Scripts Directory

This directory contains utility scripts for development, administration, and data management.

## Planned Scripts

### Data Management
- `.py` - Populate database with sample data for testing
- `.py` - Create database backups
- `.py` - Handle schema migrations and updates

### Administration
- `.py` - Check health of all services and databases
- `.py` - Remove old signals and expired cache entries
- `.py` - Rebuild Qdrant vector indexes

### Development
- `.py` - Create synthetic test data
- `.py` - Performance testing for database queries
- `.py` - Validate data against JSON schemas

### Monitoring
- `.py` - Track service performance metrics
- `.py` - Send alerts for system issues

## Usage

All scripts should be run from the project root:

```bash
python scripts/script_name.py [options]
```
