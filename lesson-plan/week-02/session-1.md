# Week 2, Session 1: Foreign Keys, JOINs, Normalization
**Domain:** University course enrollment
**Concepts:** Foreign keys, 1-to-many relationships, INNER JOIN, LEFT JOIN, normalization (1NF, 2NF, 3NF)
**Prerequisites:** Docker + PostgreSQL running, Python environment from Week 1, basic CREATE TABLE / INSERT / SELECT

---

## FOLLOW-ALONG

### Step 1: Project Setup

Create a new directory for this session's work:

```bash
mkdir -p week-02/session-1
cd week-02/session-1
```

### Step 2: The Denormalized Disaster

Before we build anything good, let's see what bad looks like. Connect to your PostgreSQL database and create this table:

```sql
-- This is the WRONG way to design a database.
-- We're doing this first so you can feel the pain of denormalization.
CREATE TABLE enrollment_flat (
    student_name VARCHAR(100),
    student_email VARCHAR(150),
    student_gpa DECIMAL(3,2),
    course_name VARCHAR(100),
    course_code VARCHAR(10),
    course_credits INTEGER,
    department_name VARCHAR(100),
    department_building VARCHAR(100),
    semester VARCHAR(20),
    grade VARCHAR(2)
);

INSERT INTO enrollment_flat VALUES
('Alice Chen', 'achen@uni.edu', 3.8, 'Intro to Databases', 'CS201', 3, 'Computer Science', 'Turing Hall', 'Fall 2024', 'A'),
('Alice Chen', 'achen@uni.edu', 3.8, 'Linear Algebra', 'MATH301', 4, 'Mathematics', 'Euler Building', 'Fall 2024', 'B+'),
('Bob Martinez', 'bmart@uni.edu', 3.2, 'Intro to Databases', 'CS201', 3, 'Computer Science', 'Turing Hall', 'Fall 2024', 'B'),
('Bob Martinez', 'bmart@uni.edu', 3.2, 'Data Structures', 'CS202', 3, 'Computer Science', 'Turing Hall', 'Fall 2024', 'A-'),
('Carol Park', 'cpark@uni.edu', 3.9, 'Linear Algebra', 'MATH301', 4, 'Mathematics', 'Euler Building', 'Fall 2024', 'A');
```

Now look at the problems:

```sql
-- Problem 1: UPDATE ANOMALY
-- Alice changed her email. We have to update EVERY row she appears in.
-- If we miss one, her data is inconsistent.
UPDATE enrollment_flat SET student_email = 'alice.chen@uni.edu'
WHERE student_name = 'Alice Chen';

-- Problem 2: INSERT ANOMALY
-- We want to add a new department "Physics" in "Newton Hall"
-- but we CAN'T unless a student is enrolled in a Physics course.
-- The department's existence depends on enrollment data -- that's backwards.

-- Problem 3: DELETE ANOMALY
-- If Carol drops Linear Algebra, we lose ALL information about Carol
-- (her GPA, her email) because that was her only enrollment.
DELETE FROM enrollment_flat WHERE student_name = 'Carol Park';

-- Undo the damage before we move on
DROP TABLE enrollment_flat;
```

Run these one at a time. Notice how each problem stems from the same root cause: unrelated data crammed into one table.

### Step 3: Normalization -- Splitting Into Proper Tables

Now let's build it right. We'll go through the normal forms:

**1NF (First Normal Form):** Every column holds a single atomic value. No repeating groups. Our flat table actually passed 1NF -- each cell has one value. But it fails higher forms.

**2NF (Second Normal Form):** Every non-key column depends on the ENTIRE primary key, not just part of it. In our flat table, `department_building` depends only on `department_name`, not on which student enrolled in what. That's a partial dependency -- violation of 2NF.

**3NF (Third Normal Form):** No non-key column depends on another non-key column. `department_building` depends on `department_name`, which depends on `course_code`. That chain (`enrollment → course → department → building`) is a transitive dependency -- violation of 3NF.

The fix: split data so each table stores facts about ONE type of entity.

```sql
-- Departments table: facts about departments, nothing else
-- This is the "parent" in our hierarchy -- it depends on nothing
CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,  -- SERIAL auto-increments; surrogate key avoids using name as PK
    name VARCHAR(100) NOT NULL UNIQUE, -- UNIQUE because two departments can't share a name
    building VARCHAR(100) NOT NULL
);

-- Courses table: facts about courses
-- Each course belongs to exactly one department (1-to-many: one department has many courses)
CREATE TABLE courses (
    course_id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,    -- natural key (human-readable), but we use surrogate PK for joins
    name VARCHAR(100) NOT NULL,
    credits INTEGER NOT NULL CHECK (credits BETWEEN 1 AND 6),  -- CHECK prevents nonsense values
    department_id INTEGER NOT NULL,
    -- REFERENCES creates the foreign key constraint:
    -- this column MUST contain a value that exists in departments.department_id
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- Students table: facts about students
-- No foreign keys here because students exist independently of courses
CREATE TABLE students (
    student_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    gpa DECIMAL(3,2) CHECK (gpa BETWEEN 0.00 AND 4.00)
);

-- Enrollments table: the RELATIONSHIP between students and courses
-- This is a junction/bridge table -- it exists because the relationship is many-to-many
-- (one student takes many courses, one course has many students)
CREATE TABLE enrollments (
    enrollment_id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    semester VARCHAR(20) NOT NULL,
    grade VARCHAR(2),
    -- Two foreign keys: one to each side of the many-to-many relationship
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    -- Composite unique constraint: a student can't enroll in the same course twice in the same semester
    UNIQUE (student_id, course_id, semester)
);
```

Run this block. Notice how each table stores facts about exactly one thing. That's 3NF.

### Step 4: Load Sample Data

```sql
-- Insert departments first (no dependencies)
INSERT INTO departments (name, building) VALUES
('Computer Science', 'Turing Hall'),
('Mathematics', 'Euler Building'),
('Physics', 'Newton Hall'),           -- Physics can exist now even with zero enrollments!
('English', 'Shakespeare Center');

-- Insert courses (depends on departments existing)
INSERT INTO courses (code, name, credits, department_id) VALUES
('CS201', 'Intro to Databases', 3, 1),
('CS202', 'Data Structures', 3, 1),
('CS301', 'Operating Systems', 4, 1),
('MATH301', 'Linear Algebra', 4, 2),
('MATH101', 'Calculus I', 4, 2),
('PHYS201', 'Quantum Mechanics', 4, 3),
('ENG101', 'Creative Writing', 3, 4);

-- Insert students (independent)
INSERT INTO students (name, email, gpa) VALUES
('Alice Chen', 'achen@uni.edu', 3.80),
('Bob Martinez', 'bmart@uni.edu', 3.20),
('Carol Park', 'cpark@uni.edu', 3.90),
('David Kim', 'dkim@uni.edu', 2.75),
('Eva Torres', 'etorres@uni.edu', 3.50);

-- Insert enrollments (depends on both students and courses existing)
INSERT INTO enrollments (student_id, course_id, semester, grade) VALUES
(1, 1, 'Fall 2024', 'A'),     -- Alice -> Intro to Databases
(1, 4, 'Fall 2024', 'B+'),    -- Alice -> Linear Algebra
(2, 1, 'Fall 2024', 'B'),     -- Bob -> Intro to Databases
(2, 2, 'Fall 2024', 'A-'),    -- Bob -> Data Structures
(3, 4, 'Fall 2024', 'A'),     -- Carol -> Linear Algebra
(3, 5, 'Fall 2024', 'B+'),    -- Carol -> Calculus I
(4, 1, 'Fall 2024', 'C'),     -- David -> Intro to Databases
(4, 2, 'Fall 2024', 'C+'),    -- David -> Data Structures
(4, 3, 'Fall 2024', 'B-');    -- David -> Operating Systems
-- Note: Eva has NO enrollments -- she'll be useful for LEFT JOIN demos
```

Run the inserts. Verify: `SELECT COUNT(*) FROM enrollments;` should return 9.

### Step 5: Foreign Key Enforcement in Action

```sql
-- Try to enroll a nonexistent student (student_id 99 doesn't exist)
INSERT INTO enrollments (student_id, course_id, semester) VALUES (99, 1, 'Fall 2024');
-- ERROR: insert or update on table "enrollments" violates foreign key constraint
-- The database REFUSES to create an orphan record. This is referential integrity.

-- Try to create a course in a nonexistent department
INSERT INTO courses (code, name, credits, department_id) VALUES ('BIO101', 'Biology', 3, 99);
-- Same error. The FK constraint protects your data from becoming inconsistent.

-- Try to delete a department that has courses pointing to it
DELETE FROM departments WHERE name = 'Computer Science';
-- ERROR: update or delete on table "departments" violates foreign key constraint
-- PostgreSQL blocks this by default (RESTRICT behavior) because courses reference this department.
```

Run each statement and observe the errors. This is the whole point of foreign keys -- the database enforces your data relationships so your application code doesn't have to.

### Step 6: INNER JOIN -- Matching Rows Only

```sql
-- INNER JOIN returns ONLY rows where the join condition matches on both sides.
-- If a student has no enrollments, they won't appear. If a course has no students, it won't appear.

-- Query: Which students are enrolled in which courses?
SELECT
    s.name AS student_name,
    c.code AS course_code,
    c.name AS course_name,
    e.grade
FROM students s
-- "s" is a table alias -- shorter to type and required when joining a table to itself
INNER JOIN enrollments e ON s.student_id = e.student_id
-- We chain joins: students -> enrollments -> courses
INNER JOIN courses c ON e.course_id = c.course_id
ORDER BY s.name, c.code;
```

Run it. Notice Eva Torres doesn't appear -- she has no enrollments, so the INNER JOIN excludes her. The Creative Writing and Quantum Mechanics courses also don't appear -- no one enrolled.

### Step 7: LEFT JOIN -- Keep All Rows From the Left Table

```sql
-- LEFT JOIN keeps EVERY row from the left table, even if there's no match on the right.
-- Unmatched rows get NULL for all right-table columns.

-- Query: ALL students and their enrollments (including students with none)
SELECT
    s.name AS student_name,
    c.code AS course_code,
    c.name AS course_name,
    e.grade
FROM students s
LEFT JOIN enrollments e ON s.student_id = e.student_id
LEFT JOIN courses c ON e.course_id = c.course_id
ORDER BY s.name, c.code;
-- Eva Torres now appears with NULLs for course_code, course_name, and grade

-- Query: Find students with NO enrollments (the LEFT JOIN + NULL trick)
SELECT s.name, s.email
FROM students s
LEFT JOIN enrollments e ON s.student_id = e.student_id
WHERE e.enrollment_id IS NULL;
-- Only Eva Torres. The WHERE clause filters to rows where the join found no match.
-- This pattern (LEFT JOIN + IS NULL) is one of the most useful in SQL.
```

Run both queries. The first shows Eva with NULLs. The second isolates only unmatched rows -- this is how you find orphans, gaps, and missing data.

### Step 8: Multi-Table JOINs With Aggregation

```sql
-- Query: How many students are enrolled in each department?
-- This requires joining 4 tables: departments -> courses -> enrollments -> students
SELECT
    d.name AS department,
    COUNT(DISTINCT e.student_id) AS student_count
    -- DISTINCT because a student might take multiple courses in the same department
FROM departments d
LEFT JOIN courses c ON d.department_id = c.department_id
LEFT JOIN enrollments e ON c.course_id = e.course_id
GROUP BY d.name
ORDER BY student_count DESC;
-- English and Physics show 0 -- LEFT JOIN ensures they appear even with no enrollments

-- Query: Average grade per department (converting letter grades to GPA-like numbers)
-- This uses a CASE expression to map letter grades to numeric values
SELECT
    d.name AS department,
    ROUND(AVG(
        CASE e.grade
            WHEN 'A'  THEN 4.0
            WHEN 'A-' THEN 3.7
            WHEN 'B+' THEN 3.3
            WHEN 'B'  THEN 3.0
            WHEN 'B-' THEN 2.7
            WHEN 'C+' THEN 2.3
            WHEN 'C'  THEN 2.0
            ELSE NULL  -- unknown grades treated as NULL (ignored by AVG)
        END
    ), 2) AS avg_grade_points
FROM departments d
JOIN courses c ON d.department_id = c.department_id
JOIN enrollments e ON c.course_id = e.course_id
GROUP BY d.name
ORDER BY avg_grade_points DESC;
```

Run both. The first query demonstrates why LEFT JOIN matters for reporting -- you want departments with zero students to still appear. The second shows how JOINs combine with aggregation to answer real analytical questions.

### Step 9: ON DELETE Behavior

```sql
-- Let's explore what happens when you delete a parent record.
-- First, create a test table to experiment without breaking our real data.

CREATE TABLE test_parent (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50)
);

-- CASCADE: deleting parent automatically deletes all children
CREATE TABLE test_child_cascade (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES test_parent(id) ON DELETE CASCADE,
    value VARCHAR(50)
);

-- SET NULL: deleting parent sets the FK column to NULL in children
CREATE TABLE test_child_setnull (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES test_parent(id) ON DELETE SET NULL,
    value VARCHAR(50)
);

-- RESTRICT (default): blocks deletion if children exist
CREATE TABLE test_child_restrict (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES test_parent(id) ON DELETE RESTRICT,
    value VARCHAR(50)
);

INSERT INTO test_parent VALUES (1, 'Parent A'), (2, 'Parent B'), (3, 'Parent C');
INSERT INTO test_child_cascade VALUES (1, 1, 'cascade child');
INSERT INTO test_child_setnull VALUES (1, 2, 'setnull child');
INSERT INTO test_child_restrict VALUES (1, 3, 'restrict child');

-- CASCADE: parent deleted, child automatically deleted too
DELETE FROM test_parent WHERE id = 1;
SELECT * FROM test_child_cascade;  -- empty!

-- SET NULL: parent deleted, child kept but parent_id set to NULL
DELETE FROM test_parent WHERE id = 2;
SELECT * FROM test_child_setnull;  -- row exists, parent_id is NULL

-- RESTRICT: deletion blocked because child exists
DELETE FROM test_parent WHERE id = 3;
-- ERROR: violates foreign key constraint

-- Clean up test tables
DROP TABLE test_child_cascade, test_child_setnull, test_child_restrict, test_parent;
```

Run each delete one at a time and check the results. The choice between CASCADE, SET NULL, and RESTRICT depends on your domain: CASCADE for "delete everything related," SET NULL for "keep the record but break the link," RESTRICT for "never allow orphaning."

### Step 10: Cleanup Reminder

Keep the `departments`, `courses`, `students`, and `enrollments` tables -- you'll need them for the independent exercise.

---

## INDEPENDENT

### Your Task

Extend the university database with two new tables and three queries. You have 15-20 minutes.

### Part 1: Add a `professors` Table

Create a table to track professors. Each professor belongs to one department. The table needs columns for: an auto-incrementing ID, the professor's name, their email (must be unique), their hire date, and a foreign key linking to their department.

After creating the table, insert at least 4 professors across at least 2 different departments.

### Part 2: Add an `assignments` Table

Create a junction table that links professors to the courses they teach. A professor can teach multiple courses, and a course can be taught by multiple professors (in different semesters). The table needs: an auto-incrementing ID, a foreign key to professors, a foreign key to courses, the semester, and a constraint ensuring the same professor can't be assigned to the same course in the same semester twice.

Insert assignments so that at least 2 professors are teaching courses, and at least one course has been taught by different professors in different semesters.

### Part 3: Write Three Queries

1. **Courses per professor:** Write a query that lists each professor's name alongside every course they teach (code and name), including the department the course belongs to. Use appropriate JOINs to connect professors → assignments → courses → departments.

2. **Students with no enrollments:** Write a query that finds all students who are not enrolled in ANY course. Use the LEFT JOIN + IS NULL pattern demonstrated in the follow-along.

3. **Average grade per department:** Write a query that computes the average numeric grade for each department (using the letter-to-number CASE mapping from the follow-along). The results should include ALL departments, even those with no graded enrollments -- those should show NULL for the average.

### Expected Results

- The `professors` table should enforce referential integrity (try inserting a professor with a nonexistent department_id to verify).
- The `assignments` table should reject duplicate professor+course+semester combinations.
- Query 1 should return one row per professor-course pair.
- Query 2 should return Eva Torres (and only Eva, given the sample data).
- Query 3 should include Physics and English with NULL averages.

---

## REVIEW CHECKLIST

When the student shares their code, check for:

- [ ] `professors` table has a proper SERIAL PRIMARY KEY
- [ ] `professors.department_id` is a FOREIGN KEY referencing `departments(department_id)`
- [ ] `professors.email` has a UNIQUE constraint
- [ ] `assignments` table has foreign keys to BOTH `professors` and `courses`
- [ ] `assignments` has a UNIQUE constraint on (professor_id, course_id, semester)
- [ ] Query 1 uses JOINs across 3+ tables (professors → assignments → courses, optionally → departments)
- [ ] Query 2 uses LEFT JOIN + WHERE ... IS NULL pattern (not a subquery -- that works but isn't what we practiced)
- [ ] Query 3 uses LEFT JOIN from departments to ensure Physics/English appear with NULLs
- [ ] Query 3 includes the CASE expression for grade conversion
- [ ] All foreign key constraints actually work (student tested with invalid data)

---

## QUIZ

Answer all 15 questions. You must score at least 8/10 on the 10 selected for grading.

**Q1 (Multiple Choice):** What does a foreign key constraint guarantee?
a) That the child table has fewer rows than the parent table
b) That every value in the FK column exists in the referenced table's column (or is NULL)
c) That the two tables always have the same number of rows
d) That the FK column is automatically indexed

**Q2 (Short Answer):** You have a `books` table and an `authors` table. Each book has exactly one author, but an author can write many books. Which table gets the foreign key column, and why?

**Q3 (What Does This Output?):**
```sql
CREATE TABLE parent (id SERIAL PRIMARY KEY, name TEXT);
CREATE TABLE child (id SERIAL PRIMARY KEY, parent_id INT REFERENCES parent(id));
INSERT INTO parent VALUES (1, 'X');
INSERT INTO child VALUES (1, 1);
DELETE FROM parent WHERE id = 1;
```
What happens when the DELETE runs?

**Q4 (Multiple Choice):** Which JOIN type returns ALL rows from the left table, even if there's no match in the right table?
a) INNER JOIN
b) RIGHT JOIN
c) LEFT JOIN
d) CROSS JOIN

**Q5 (Spot the Bug):**
```sql
SELECT s.name, c.name
FROM students s
INNER JOIN courses c ON s.student_id = c.course_id;
```
This query runs without error but returns wrong results. What's the bug?

**Q6 (Short Answer):** Explain the difference between 2NF and 3NF in one sentence each.

**Q7 (Multiple Choice):** What does `ON DELETE CASCADE` do?
a) Sets the FK column to NULL when the parent row is deleted
b) Prevents deletion of the parent row if children exist
c) Automatically deletes all child rows when the parent row is deleted
d) Deletes the FK constraint itself

**Q8 (What Does This Output?):**
```sql
SELECT d.name, COUNT(e.enrollment_id)
FROM departments d
LEFT JOIN courses c ON d.department_id = c.department_id
LEFT JOIN enrollments e ON c.course_id = e.course_id
GROUP BY d.name
ORDER BY d.name;
```
Given our sample data, what value appears for the Physics department?

**Q9 (Multiple Choice):** A table has columns: `order_id`, `product_name`, `product_category`, `customer_name`, `customer_address`. Which normal form does this violate?
a) 1NF
b) 2NF
c) 3NF
d) It doesn't violate any normal form

**Q10 (Short Answer):** Why do we use `COUNT(DISTINCT e.student_id)` instead of `COUNT(e.student_id)` when counting students per department?

**Q11 (Spot the Bug):**
```sql
SELECT s.name
FROM students s
LEFT JOIN enrollments e ON s.student_id = e.student_id
WHERE e.grade = 'A';
```
A developer wrote this expecting to find students with an A grade, but they also wanted students with no enrollments to appear (with NULL grade). Why doesn't this work?

**Q12 (Multiple Choice):** Which statement about junction/bridge tables is TRUE?
a) They always have exactly two columns
b) They resolve many-to-many relationships by holding foreign keys to both parent tables
c) They cannot have additional columns beyond the foreign keys
d) They don't need a primary key

**Q13 (What Does This Output?):**
```sql
SELECT COUNT(*)
FROM students s
INNER JOIN enrollments e ON s.student_id = e.student_id;
```
Given our sample data (5 students, 9 enrollments, Eva has none), what number is returned?

**Q14 (Short Answer):** A table stores: `employee_name`, `department_name`, `department_manager`. The department_manager depends on department_name, not on employee_name. Which normal form is violated and why?

**Q15 (Multiple Choice):** What is the result of a LEFT JOIN when the right table has NO matching rows?
a) The row is excluded from the results
b) The row appears with NULL values for all right-table columns
c) The query throws an error
d) The row appears with empty strings for right-table columns

---

### ANSWER KEY

**Q1:** b) That every value in the FK column exists in the referenced table's column (or is NULL)

**Q2:** The `books` table gets the foreign key (`author_id`). In a 1-to-many relationship, the FK always goes on the "many" side. Each book points to its one author; putting author_ids in the books table means each book has exactly one author reference.

**Q3:** The DELETE fails with a foreign key violation error. The default ON DELETE behavior is RESTRICT, which prevents deleting a parent row that has children referencing it.

**Q4:** c) LEFT JOIN

**Q5:** The ON clause joins `s.student_id = c.course_id` -- it's comparing a student ID to a course ID, which are unrelated columns. The query should join through the `enrollments` table: `students JOIN enrollments ON s.student_id = e.student_id JOIN courses ON e.course_id = c.course_id`.

**Q6:** 2NF: Every non-key column must depend on the ENTIRE primary key (no partial dependencies). 3NF: No non-key column can depend on another non-key column (no transitive dependencies).

**Q7:** c) Automatically deletes all child rows when the parent row is deleted

**Q8:** 0. Physics has courses (Quantum Mechanics) but no enrollments, so `COUNT(e.enrollment_id)` counts zero non-NULL enrollment IDs.

**Q9:** c) 3NF. `customer_address` depends on `customer_name` (a non-key column), not directly on the primary key. That's a transitive dependency.

**Q10:** Without DISTINCT, a student taking 3 courses in the CS department would be counted 3 times. DISTINCT ensures each student is counted only once per department, regardless of how many courses they take in that department.

**Q11:** The WHERE clause filters AFTER the LEFT JOIN. `WHERE e.grade = 'A'` eliminates any row where grade is NULL -- including students with no enrollments. To fix it: `WHERE e.grade = 'A' OR e.enrollment_id IS NULL`.

**Q12:** b) They resolve many-to-many relationships by holding foreign keys to both parent tables

**Q13:** 9. INNER JOIN returns one row per matching enrollment. Eva has no enrollments so she's excluded. The 4 remaining students have 9 enrollments total.

**Q14:** 3NF is violated. `department_manager` depends on `department_name`, which is a non-key column -- that's a transitive dependency. The fix is to put `department_manager` in a separate `departments` table.

**Q15:** b) The row appears with NULL values for all right-table columns
