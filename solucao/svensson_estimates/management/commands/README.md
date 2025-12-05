# Management Commands

## populate_feriados

Populates the Feriados model with Brazilian holiday dates from `feriados.csv`.

### Usage

```bash
python3 manage.py populate_feriados
```

### Notes

- This command will delete all existing holiday records before populating
- Dates in the CSV file should be in Brazilian format: dd/mm/yyyy
- The CSV file should be located at: `svensson_estimates/feriados.csv`
- Invalid dates will be skipped with a warning message

### Automatic Population

The Feriados model is automatically populated after running migrations using Django signals. The signal will:
- Only run once when the table is empty
- Parse dates from the CSV file in Brazilian format (dd/mm/yyyy)
- Create unique records for each holiday date

If you need to re-populate or update the data, you can run the management command manually.
