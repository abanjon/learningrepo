# Week 4, Session 1: Window Functions, CTEs, Subqueries
**Domain:** Employee salary analytics
**Concepts:** ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, SUM/AVG OVER, CTEs (WITH clause), correlated subqueries
**Prerequisites:** PostgreSQL running in Docker, comfort with JOINs and GROUP BY from Weeks 1-2

---

## FOLLOW-ALONG

### Step 1: Create the employee database

We need a realistic dataset with enough rows to make window functions meaningful. Departments, managers, varied hire dates -- all of this matters for the queries we'll write.

```sql
-- File: employee_analytics/schema.sql

-- We use a single employees table with a self-referencing manager_id.
-- This is a common real-world pattern: the org chart lives in one table.
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    salary NUMERIC(10, 2) NOT NULL,
    hire_date DATE NOT NULL,
    -- Self-referencing FK: every employee except the CEO has a manager
    -- who is also an employee. NULL means "top of the org chart."
    manager_id INTEGER REFERENCES employees(id)
);
```

Run this against your database, then confirm the tables exist.

### Step 2: Load seed data

We want multiple departments with salary variation and enough employees to see meaningful rankings.

```sql
-- File: employee_analytics/seed.sql

INSERT INTO departments (name) VALUES
    ('Engineering'),
    ('Marketing'),
    ('Sales'),
    ('Finance'),
    ('Operations');

-- Insert managers first (no manager_id) so the FK constraint is satisfied
INSERT INTO employees (first_name, last_name, department_id, salary, hire_date, manager_id) VALUES
    ('Alice',   'Chen',     1, 145000, '2019-03-15', NULL),  -- Engineering mgr
    ('Bob',     'Martinez', 2, 125000, '2019-06-01', NULL),  -- Marketing mgr
    ('Carol',   'Johnson',  3, 130000, '2019-01-10', NULL),  -- Sales mgr
    ('David',   'Kim',      4, 140000, '2018-11-20', NULL),  -- Finance mgr
    ('Eve',     'Patel',    5, 120000, '2020-02-01', NULL);  -- Operations mgr

-- Now insert individual contributors referencing their managers
INSERT INTO employees (first_name, last_name, department_id, salary, hire_date, manager_id) VALUES
    -- Engineering (dept 1, manager Alice = id 1)
    ('Frank',   'Liu',      1, 120000, '2020-07-01', 1),
    ('Grace',   'Wang',     1, 115000, '2021-01-15', 1),
    ('Hank',    'Brown',    1, 130000, '2020-03-10', 1),
    ('Ivy',     'Davis',    1, 110000, '2022-06-01', 1),
    ('Jack',    'Wilson',   1, 125000, '2021-09-01', 1),
    -- Marketing (dept 2, manager Bob = id 2)
    ('Karen',   'Taylor',   2,  95000, '2020-08-15', 2),
    ('Leo',     'Anderson', 2, 105000, '2021-03-01', 2),
    ('Mia',     'Thomas',   2,  90000, '2022-01-10', 2),
    ('Noah',    'Jackson',  2, 100000, '2021-07-20', 2),
    -- Sales (dept 3, manager Carol = id 3)
    ('Olivia',  'White',    3, 110000, '2020-05-01', 3),
    ('Paul',    'Harris',   3,  95000, '2021-02-15', 3),
    ('Quinn',   'Martin',   3, 105000, '2020-11-01', 3),
    ('Rachel',  'Garcia',   3, 115000, '2021-08-10', 3),
    ('Sam',     'Clark',    3,  88000, '2022-04-01', 3),
    -- Finance (dept 4, manager David = id 4)
    ('Tina',    'Lewis',    4, 110000, '2020-09-01', 4),
    ('Uma',     'Robinson', 4, 105000, '2021-05-15', 4),
    ('Victor',  'Walker',   4, 115000, '2020-01-20', 4),
    -- Operations (dept 5, manager Eve = id 5)
    ('Wendy',   'Hall',     5,  92000, '2021-04-01', 5),
    ('Xander',  'Allen',    5,  98000, '2020-10-15', 5),
    ('Yara',    'Young',    5,  88000, '2022-03-01', 5),
    ('Zach',    'King',     5, 105000, '2021-11-10', 5);
```

Run the seed file and verify with `SELECT COUNT(*) FROM employees;` -- you should get 27 rows.

### Step 3: Ranking employees by salary within department

This is where window functions shine. GROUP BY collapses rows; window functions keep every row and add computed columns alongside them.

```sql
-- File: employee_analytics/queries.sql

-- RANK vs DENSE_RANK vs ROW_NUMBER: the difference only shows up when
-- there are ties. ROW_NUMBER always gives unique sequential numbers.
-- RANK skips numbers after ties (1,2,2,4). DENSE_RANK doesn't skip (1,2,2,3).
SELECT
    e.first_name,
    e.last_name,
    d.name AS department,
    e.salary,
    -- ROW_NUMBER: arbitrary tiebreaker (order not guaranteed for ties)
    ROW_NUMBER() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS row_num,
    -- RANK: ties get the same rank, next rank is skipped
    RANK()       OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS rank,
    -- DENSE_RANK: ties get the same rank, next rank is NOT skipped
    DENSE_RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS dense_rank
FROM employees e
JOIN departments d ON e.department_id = d.id
ORDER BY d.name, e.salary DESC;
```

Run this and look at the Engineering department -- Alice (145k) and Hank (130k) have clear separation, so all three functions agree. But if two people had the same salary, you'd see divergence.

### Step 4: Running total of salaries by hire date

Window functions can do aggregations without collapsing rows. The frame clause (`ROWS BETWEEN`) controls which rows the aggregate includes.

```sql
-- Running total shows the cumulative salary obligation as the company
-- grew over time. This pattern is everywhere in finance and analytics.
SELECT
    e.first_name,
    e.last_name,
    e.hire_date,
    e.salary,
    -- The default frame for ORDER BY is RANGE BETWEEN UNBOUNDED PRECEDING
    -- AND CURRENT ROW, which handles ties differently than ROWS.
    -- We use ROWS explicitly here to be unambiguous.
    SUM(e.salary) OVER (
        ORDER BY e.hire_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total_salary
FROM employees e
ORDER BY e.hire_date;
```

Notice: the running total goes up with every hire. If two people were hired the same day, the `ROWS` frame processes them one at a time (arbitrary order within the tie). If we used `RANGE` instead, both same-day hires would include each other in their total.

### Step 5: Salary difference from the previous hire (LAG)

LAG looks at the previous row; LEAD looks at the next. They let you compare each row to its neighbors without a self-join.

```sql
-- LAG(column, offset, default) -- offset defaults to 1, default to NULL.
-- This query answers: "how did the salary of each new hire compare to
-- the person hired just before them?"
SELECT
    e.first_name,
    e.last_name,
    e.hire_date,
    e.salary,
    LAG(e.salary) OVER (ORDER BY e.hire_date) AS prev_hire_salary,
    -- Compute the difference so we can see the trend
    e.salary - LAG(e.salary) OVER (ORDER BY e.hire_date) AS salary_diff_from_prev
FROM employees e
ORDER BY e.hire_date;
```

The first row will have NULL for `prev_hire_salary` because there's no previous row. That's correct behavior.

### Step 6: CTE for department averages

CTEs (Common Table Expressions) use the `WITH` clause. They're named temporary result sets that exist only for the duration of the query. Think of them as defining a variable in SQL.

```sql
-- CTEs make complex queries readable by breaking them into named steps.
-- This is the same as a subquery in the FROM clause, but much easier
-- to read when you have multiple levels of computation.
WITH dept_stats AS (
    SELECT
        department_id,
        AVG(salary) AS avg_salary,
        MIN(salary) AS min_salary,
        MAX(salary) AS max_salary,
        COUNT(*)    AS headcount
    FROM employees
    GROUP BY department_id
)
SELECT
    d.name AS department,
    ds.headcount,
    ROUND(ds.avg_salary, 2) AS avg_salary,
    ds.min_salary,
    ds.max_salary,
    ds.max_salary - ds.min_salary AS salary_spread
FROM dept_stats ds
JOIN departments d ON ds.department_id = d.id
ORDER BY ds.avg_salary DESC;
```

### Step 7: Employees earning above their department average (correlated subquery)

A correlated subquery runs once per row in the outer query. It's less efficient than a JOIN or CTE for large datasets, but it's the most direct way to express "compare this row to an aggregate of its group."

```sql
-- The subquery references e.department_id from the outer query --
-- that's what makes it "correlated." The database re-evaluates
-- the subquery for each row in the outer query.
SELECT
    e.first_name,
    e.last_name,
    d.name AS department,
    e.salary,
    -- Include the average so we can see the comparison
    (SELECT ROUND(AVG(e2.salary), 2)
     FROM employees e2
     WHERE e2.department_id = e.department_id) AS dept_avg
FROM employees e
JOIN departments d ON e.department_id = d.id
WHERE e.salary > (
    SELECT AVG(e2.salary)
    FROM employees e2
    WHERE e2.department_id = e.department_id
)
ORDER BY d.name, e.salary DESC;
```

We can rewrite this more efficiently with a CTE or window function, but the correlated subquery pattern is important to recognize because you'll encounter it in legacy code everywhere.

### Step 8: Same query rewritten with a window function (compare approaches)

```sql
-- This does the same thing as Step 7 but without the correlated subquery.
-- The window function computes avg_salary once per partition, not once per row.
-- For large datasets this can be dramatically faster.
WITH salary_vs_avg AS (
    SELECT
        e.first_name,
        e.last_name,
        d.name AS department,
        e.salary,
        ROUND(AVG(e.salary) OVER (PARTITION BY e.department_id), 2) AS dept_avg
    FROM employees e
    JOIN departments d ON e.department_id = d.id
)
SELECT *
FROM salary_vs_avg
WHERE salary > dept_avg
ORDER BY department, salary DESC;
```

Run both Step 7 and Step 8 and confirm they return the same results. The window function version is the one you'd use in practice.

---

## INDEPENDENT

You have 15-20 minutes. Write **all five queries** in a file called `employee_analytics/independent_queries.sql`. Each query should be preceded by a SQL comment explaining what it does.

### Task 1: Percentile rank of each salary

Write a query that shows every employee with their salary and a percentile rank (0 to 1) within their department. Use a window function that computes percentile rank directly. The highest-paid person in each department should be at or near 1.0, the lowest at or near 0.0.

**Expected output columns:** `first_name`, `last_name`, `department`, `salary`, `percentile_rank`

### Task 2: 3-month rolling average salary by department

Write a query that computes, for each employee ordered by hire date within their department, the average salary of the current employee and the two employees hired before them in the same department. If fewer than 3 people have been hired so far, average whatever is available.

**Expected output columns:** `first_name`, `last_name`, `department`, `hire_date`, `salary`, `rolling_avg_salary`

### Task 3: Employees whose salary is within 10% of their manager's

Write a query that compares each employee's salary to their manager's salary and returns only those whose salary is within 10% (above or below) of their manager's. Exclude employees who have no manager.

**Expected output columns:** `employee_name`, `employee_salary`, `manager_name`, `manager_salary`, `salary_difference_pct`

### Task 4: Year-over-year headcount change per department

Write a query using a CTE that calculates the number of employees hired per department per year, then uses a window function to show the change from the previous year. If there were 3 hires in 2020 and 5 in 2021, the change for 2021 is +2.

**Expected output columns:** `department`, `hire_year`, `hires`, `prev_year_hires`, `yoy_change`

### Task 5: Cumulative hiring timeline

Write a query that shows a company-wide cumulative count of employees over time, ordered by hire date. Each row should show the employee hired, the date, and the total headcount as of that date.

**Expected output columns:** `first_name`, `last_name`, `hire_date`, `cumulative_headcount`

---

## REVIEW CHECKLIST

When reviewing the student's independent work, check for:

- [ ] **Task 1:** Uses `PERCENT_RANK()` or `CUME_DIST()` (not a manual calculation). PARTITION BY department is present.
- [ ] **Task 2:** Uses `AVG() OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)`. Frame specification is correct (not RANGE).
- [ ] **Task 3:** Uses a JOIN (self-join on employees) or subquery to get manager salary. The 10% comparison uses `ABS(e.salary - m.salary) / m.salary <= 0.10` or equivalent.
- [ ] **Task 4:** CTE correctly groups by department and year. LAG is used with PARTITION BY department to compare years.
- [ ] **Task 5:** Uses `ROW_NUMBER()` or `COUNT(*) OVER (ORDER BY hire_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`.
- [ ] All queries run without errors.
- [ ] Column aliases match the expected output columns.
- [ ] Results are ordered logically (by department, date, or rank as appropriate).

---

## QUIZ

Answer all 15 questions. The session quiz will use 10 of these; extras are reserved for retries.

---

**Q1 (Multiple Choice).** What is the difference between `RANK()` and `DENSE_RANK()` when there are ties?

A) RANK() starts from 0, DENSE_RANK() starts from 1
B) RANK() skips numbers after ties, DENSE_RANK() does not
C) DENSE_RANK() skips numbers after ties, RANK() does not
D) There is no difference when there are ties

---

**Q2 (Short Answer).** Explain in one sentence: what does `PARTITION BY` do in a window function?

---

**Q3 (What does this code output?).** Given a table with salaries [100, 200, 200, 300] all in the same partition, ordered by salary ASC, what values does `ROW_NUMBER()` assign?

---

**Q4 (Multiple Choice).** Which of the following is TRUE about CTEs?

A) CTEs are stored permanently in the database
B) CTEs can reference themselves (recursive CTEs)
C) CTEs are always faster than subqueries
D) CTEs cannot be used with window functions

---

**Q5 (Spot the Bug).** What is wrong with this query?

```sql
SELECT
    department_id,
    first_name,
    SUM(salary) OVER (PARTITION BY department_id) AS dept_total
FROM employees
GROUP BY department_id;
```

---

**Q6 (Short Answer).** What is a correlated subquery, and why is it typically slower than a JOIN?

---

**Q7 (Multiple Choice).** What does `LAG(salary, 2, 0) OVER (ORDER BY hire_date)` return?

A) The salary from 2 rows ahead, defaulting to 0 if none exists
B) The salary from 2 rows behind, defaulting to 0 if none exists
C) The salary from 2 rows behind, defaulting to NULL if none exists
D) The average of the previous 2 salaries

---

**Q8 (What does this code output?).** Given this query on a 5-row table ordered by id (1-5):

```sql
SELECT id, SUM(id) OVER (ORDER BY id ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) AS result
FROM t;
```

What is the value of `result` for the row where `id = 3`?

---

**Q9 (Multiple Choice).** What happens if you use a window function in a `WHERE` clause?

A) It works normally
B) It causes a syntax error
C) It silently returns wrong results
D) It works but is slower than using it in SELECT

---

**Q10 (Short Answer).** Name two advantages of CTEs over subqueries.

---

**Q11 (Spot the Bug).** What is wrong with this CTE?

```sql
WITH avg_salary AS (
    SELECT department_id, AVG(salary) AS avg_sal
    FROM employees
)
SELECT e.first_name, avg_sal
FROM employees e
JOIN avg_salary a ON e.department_id = a.department_id;
```

---

**Q12 (Multiple Choice).** What does `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` mean?

A) Include all rows in the partition
B) Include all rows from the start of the partition up to and including the current row
C) Include only the current row
D) Include the current row and all rows after it

---

**Q13 (Short Answer).** When would you choose a correlated subquery over a window function? Give one scenario.

---

**Q14 (What does this code output?).** Given employees with salaries [50000, 60000, 70000] in that order:

```sql
SELECT salary, salary - LAG(salary) OVER (ORDER BY salary) AS diff
FROM employees;
```

What are the three values in the `diff` column?

---

**Q15 (Multiple Choice).** What is the default frame specification when you write `SUM(x) OVER (ORDER BY y)` without specifying a frame?

A) ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
B) ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
C) RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
D) ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING

---

### ANSWER KEY

**Q1:** B -- RANK() skips numbers after ties (1,2,2,4), DENSE_RANK() does not (1,2,2,3).

**Q2:** PARTITION BY divides the result set into groups (partitions), and the window function is applied independently within each partition -- similar to GROUP BY but without collapsing rows.

**Q3:** 1, 2, 3, 4 -- ROW_NUMBER() always assigns unique sequential integers, even for tied values (the order of the tied rows is arbitrary).

**Q4:** B -- CTEs can reference themselves (recursive CTEs). They are not stored permanently (A is wrong), not always faster (C is wrong), and can be combined with window functions (D is wrong).

**Q5:** The query uses `GROUP BY department_id` but also selects `first_name`, which is not in the GROUP BY and not aggregated. You can't mix GROUP BY and window functions on non-aggregated columns like this. Either remove the GROUP BY (and let the window function handle the partitioning) or aggregate `first_name`.

**Q6:** A correlated subquery references a column from the outer query, causing the database to re-execute the subquery once for each row in the outer query. A JOIN executes once and matches rows, making it typically faster for large datasets.

**Q7:** B -- LAG with offset 2 looks 2 rows behind, and the third argument (0) is the default when there aren't enough preceding rows.

**Q8:** 6 -- For id=3, the frame includes id=2, id=3, and id=4, so 2+3+4=9. Wait -- let me recompute: ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING for id=3 means rows 2,3,4 → SUM = 2+3+4 = 9. The answer is **9**.

**Q9:** B -- Window functions cannot be used in WHERE clauses. You must wrap the query in a subquery or CTE and filter in the outer query.

**Q10:** (Any two of:) 1) Readability -- CTEs have names that document intent. 2) Reusability -- a CTE can be referenced multiple times in the same query. 3) Recursion -- CTEs support recursive queries, which subqueries do not.

**Q11:** The CTE is missing `GROUP BY department_id`. `AVG(salary)` is an aggregate function, but without GROUP BY, it computes a single average across ALL employees, not per department.

**Q12:** B -- It includes all rows from the very first row of the partition up to and including the current row. This is the frame used for running totals.

**Q13:** When you need to use the result in a WHERE clause for existence checks (e.g., `WHERE EXISTS (SELECT 1 FROM ... WHERE correlated_condition)`). Window functions can only appear in SELECT and ORDER BY, so correlated subqueries are necessary when the comparison must filter rows.

**Q14:** NULL, 10000, 10000 -- The first row has no preceding row so LAG returns NULL. 60000-50000=10000. 70000-60000=10000.

**Q15:** C -- The default frame is RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW. Note: this is RANGE, not ROWS. The difference matters when there are ties in the ORDER BY column -- RANGE includes all rows with the same value as the current row.
