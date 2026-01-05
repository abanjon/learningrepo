errors = []



with open("etl_errors.log", "r") as f:
    error_log = f.read()

for error_log_lines in error_log.splitlines():
    print(error_log_lines.strip())







