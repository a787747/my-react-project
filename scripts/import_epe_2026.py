#!/usr/bin/env python3
"""Build the approved, idempotent EPE 2026 organisation import SQL."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl


DEPARTMENT_MAP = {
    "Accounting": "Accounting",
    "Administration": "Administration",
    "Board of Directors": "Board of Directors",
    "C-Level": "C-level",
    "Clinical Lab Solutions": "Clinical Lab Solutions",
    "Contract & Compliance": "Contract & Compliance",
    "Customs": "Customs",
    "HR": "HR",
    "IT": "IT",
    "Lab Solution Division": "Lab Solution Division",
    "Legal": "Legal",
    "Logistics": "Logistics",
    "Pharma Division": "Pharma Division",
    "Project": "Project",
    "Sales": "Sales",
    "Seda Academy Project": "Seda Academy Project",
    "Special Lab Solution": "Special Lab Solution",
    "Technical": "Technical",
}

NEW_DEPARTMENTS = (
    "Board of Directors",
    "Clinical Lab Solutions",
    "Pharma Division",
    "Special Lab Solution",
)

EXPLICIT_GRADES = {
    "kuvvat@sedamedical.com": "S1",
    "mahrijemal@sedamedical.com": "S1",
    "hummedov@sedamedical.com": "M1",
    "enesh@sedamedical.com": "A",
    "arslan@sedamedical.com": "A",
    "rahim@sedamedical.com": "A",
    "cheper@sedamedical.com": "S2",
    "david@sedamedical.com": "S2",
    "mive@sedamedical.com": "S1",
    "merjen@sedamedical.com": "S1",
    "chariyev@sedamedical.com": "S2",
    "esenova@sedamedical.com": "A",
    "govher@sedamedical.com": "A",
    "aysoltan@sedamedical.com": "A",
    "jeren@sedamedical.com": "S2",
    "maksut.d@sedamedical.com": "A",
    "merdan.rasulov@sedamedical.com": "S1",
    "nurnabat@sedamedical.com": "S1",
    "suleyman@sedamedical.com": "A",
}

READ_ONLY_EMAILS = {
    "cem@sedamedical.com",
    "hemra@sedamedical.com",
    "mekan@sedamedical.com",
}

ACTIVE_C_LEVEL_EMAILS = {
    "alexander@sedamedical.com",
    "bayram@sedamedical.com",
    "jemal@sedamedical.com",
}

C_LEVEL_EMAILS = {
    "bayram@sedamedical.com",
    "jemal@sedamedical.com",
    "hemra@sedamedical.com",
    "mekan@sedamedical.com",
}

POST_H1_EMAILS = {
    "esenova@sedamedical.com",
    "govher@sedamedical.com",
}

LAB_DEPARTMENTS = {
    "Clinical Lab Solutions",
    "Lab Solution Division",
    "Special Lab Solution",
}


def clean(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        return re.sub(
            r"[ \t]+",
            " ",
            value.replace("\r", " ").replace("\n", " "),
        ).strip()
    return value


def normalize_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def load_export(path: Path) -> list[dict[str, Any]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook["Default"]
    # The HR export incorrectly declares dimension A1 although cells A1:P89 exist.
    worksheet.reset_dimensions()
    raw_rows = list(worksheet.iter_rows(values_only=True))
    if not raw_rows:
        raise ValueError("HR export is empty")

    headers = [str(value).strip() for value in raw_rows[0]]
    expected = {
        "Display name",
        "Department",
        "Job title",
        "Reports to",
        "Start date",
        "Is a manager",
        "Email",
        "Full name",
        "Org level",
    }
    missing = expected - set(headers)
    if missing:
        raise ValueError(f"HR export is missing columns: {sorted(missing)}")

    records: list[dict[str, Any]] = []
    for raw_row in raw_rows[1:]:
        record = {
            headers[index]: clean(raw_row[index] if index < len(raw_row) else None)
            for index in range(len(headers))
        }
        record["email"] = str(record.get("Email") or "").lower().strip()
        record["department"] = re.sub(
            r"\s+",
            " ",
            str(record.get("Department") or ""),
        ).strip()
        records.append(record)
    return records


def role_for(record: dict[str, Any]) -> str:
    email = record["email"]
    if email == "alexander@sedamedical.com":
        return "admin"
    if email in C_LEVEL_EMAILS:
        return "c_level"
    if record["department"] == "HR":
        return "hr"
    if str(record.get("Is a manager") or "").casefold() == "yes":
        return "manager"
    return "employee"


def project_values(record: dict[str, Any]) -> tuple[str, bool]:
    department = record["department"]
    title = str(record.get("Job title") or "")
    is_project = (
        department in {"Project", "Technical", "Seda Academy Project"}
        or (department in LAB_DEPARTMENTS and title != "Application Assistant")
        or (
            department == "Administration"
            and "Hästens Project" in title
        )
    )
    return ("project", True) if is_project else ("general", False)


def build_model(
    export_records: list[dict[str, Any]],
    source_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    if len(export_records) != 88:
        raise ValueError(f"Expected 88 export employees, got {len(export_records)}")

    emails = [record["email"] for record in export_records]
    if any(not email for email in emails):
        raise ValueError("Every export employee must have an email")
    duplicates = [email for email, count in Counter(emails).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate export emails: {duplicates}")

    source_by_email = {
        user["email"].lower(): user for user in source_snapshot["users"]
    }
    export_name_to_email: dict[str, str] = {}
    for record in export_records:
        for field in ("Display name", "Full name"):
            key = normalize_name(record.get(field))
            existing = export_name_to_email.get(key)
            if existing and existing != record["email"]:
                raise ValueError(f"Ambiguous export name: {record.get(field)}")
            export_name_to_email[key] = record["email"]
    cem_name_key = normalize_name("Cem Durukan")
    if cem_name_key in export_name_to_email:
        raise ValueError(
            "Manual Cem Durukan entry collides with export email "
            f"{export_name_to_email[cem_name_key]}"
        )
    export_name_to_email[cem_name_key] = "cem@sedamedical.com"

    model: list[dict[str, Any]] = []
    unresolved_managers: list[tuple[str, str]] = []
    unresolved_grades: list[str] = []

    for record in export_records:
        email = record["email"]
        export_department = record["department"]
        if export_department not in DEPARTMENT_MAP:
            raise ValueError(f"Unapproved department: {export_department}")

        reports_to = str(record.get("Reports to") or "").strip()
        manager_email = None
        if reports_to:
            manager_email = export_name_to_email.get(normalize_name(reports_to))
            if not manager_email:
                unresolved_managers.append((record["Full name"], reports_to))

        grade_code = EXPLICIT_GRADES.get(email)
        if not grade_code:
            source_user = source_by_email.get(email)
            grade_code = source_user["grade"] if source_user else None
        if not grade_code and email not in {
            "hemra@sedamedical.com",
            "mekan@sedamedical.com",
        }:
            unresolved_grades.append(record["Full name"])

        work_category, is_project_participant = project_values(record)
        can_evaluate = email not in READ_ONLY_EMAILS
        can_be_evaluated = (
            email not in READ_ONLY_EMAILS
            and email not in ACTIVE_C_LEVEL_EMAILS
        )

        model.append(
            {
                "full_name": record["Full name"],
                "email": email,
                "role": role_for(record),
                "job_title": record.get("Job title") or None,
                "join_date": record.get("Start date") or None,
                "department": DEPARTMENT_MAP[export_department],
                "grade": grade_code,
                "manager_email": manager_email,
                "work_category": work_category,
                "is_project_participant": is_project_participant,
                "can_evaluate": can_evaluate,
                "can_be_evaluated": can_be_evaluated,
                "h1_in_scope": (
                    email not in READ_ONLY_EMAILS
                    and email not in POST_H1_EMAILS
                ),
            }
        )

    if unresolved_managers:
        raise ValueError(f"Unresolved managers: {unresolved_managers}")
    if unresolved_grades:
        raise ValueError(f"Unresolved grades: {unresolved_grades}")

    model.append(
        {
            "full_name": "Cem Durukan",
            "email": "cem@sedamedical.com",
            "role": "c_level",
            "job_title": "General Manager",
            "join_date": None,
            "department": None,
            "grade": None,
            "manager_email": None,
            "work_category": "general",
            "is_project_participant": False,
            "can_evaluate": False,
            "can_be_evaluated": False,
            "h1_in_scope": False,
        }
    )

    model_by_email = {row["email"]: row for row in model}
    if len(model_by_email) != 89:
        raise ValueError("Target model must contain 89 unique users")

    # Validate manager resolution and cycles before producing SQL.
    for row in model:
        manager_email = row["manager_email"]
        if manager_email and manager_email not in model_by_email:
            raise ValueError(
                f"Manager {manager_email} is absent for {row['email']}"
            )

    edges = {
        row["email"]: row["manager_email"]
        for row in model
        if row["manager_email"]
    }
    for start in edges:
        seen: set[str] = set()
        current: str | None = start
        while current in edges:
            if current in seen:
                raise ValueError(f"Manager cycle detected at {current}")
            seen.add(current)
            current = edges[current]

    return sorted(model, key=lambda row: row["email"])


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return "'" + str(value).replace("'", "''") + "'"


def build_sql(model: list[dict[str, Any]]) -> str:
    value_rows = []
    for row in model:
        values = [
            row["full_name"],
            row["email"],
            row["role"],
            row["job_title"],
            row["join_date"],
            row["department"],
            row["grade"],
            row["manager_email"],
            row["work_category"],
            row["is_project_participant"],
            row["can_evaluate"],
            row["can_be_evaluated"],
        ]
        value_rows.append("  (" + ", ".join(sql_literal(value) for value in values) + ")")

    new_department_values = ",\n  ".join(
        f"({sql_literal(name)})" for name in NEW_DEPARTMENTS
    )

    return f"""\\set ON_ERROR_STOP on
BEGIN;

ALTER TABLE performance_db.users
  ADD COLUMN IF NOT EXISTS can_evaluate boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS can_be_evaluated boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN performance_db.users.can_evaluate IS
  'Permanent capability flag; period-specific scope is stored separately.';
COMMENT ON COLUMN performance_db.users.can_be_evaluated IS
  'Permanent capability flag; period-specific scope is stored separately.';

UPDATE performance_db.departments
SET name = 'Lab Solution Division'
WHERE name = 'Lab Solution Division '
  AND NOT EXISTS (
    SELECT 1
    FROM performance_db.departments
    WHERE name = 'Lab Solution Division'
  );

INSERT INTO performance_db.departments (name)
SELECT requested.name
FROM (
  VALUES
    {new_department_values}
) AS requested(name)
WHERE NOT EXISTS (
  SELECT 1
  FROM performance_db.departments existing
  WHERE existing.name = requested.name
)
ON CONFLICT (name) DO NOTHING;

INSERT INTO performance_db.grades (code, coefficient, description)
SELECT 'M1', coefficient, description
FROM performance_db.grades
WHERE code = 'S4-M1'
  AND NOT EXISTS (
    SELECT 1 FROM performance_db.grades WHERE code = 'M1'
  )
ON CONFLICT (code) DO NOTHING;

UPDATE performance_db.grades target
SET coefficient = source.coefficient,
    description = source.description
FROM performance_db.grades source
WHERE target.code = 'M1'
  AND source.code = 'S4-M1'
  AND (target.coefficient, target.description)
      IS DISTINCT FROM (source.coefficient, source.description);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM performance_db.grades WHERE code = 'M1'
  ) THEN
    RAISE EXCEPTION
      'M1 grade was not created; S4-M1 is absent from performance_db.grades';
  END IF;
END
$$;

CREATE TEMP TABLE epe_import_users (
  full_name text NOT NULL,
  email text PRIMARY KEY,
  role text NOT NULL,
  job_title text,
  join_date date,
  department_name text,
  grade_code text,
  manager_email text,
  work_category text NOT NULL,
  is_project_participant boolean NOT NULL,
  can_evaluate boolean NOT NULL,
  can_be_evaluated boolean NOT NULL
) ON COMMIT DROP;

INSERT INTO epe_import_users (
  full_name,
  email,
  role,
  job_title,
  join_date,
  department_name,
  grade_code,
  manager_email,
  work_category,
  is_project_participant,
  can_evaluate,
  can_be_evaluated
)
VALUES
{",\n".join(value_rows)};

WITH resolved AS (
  SELECT
    staged.*,
    departments.id AS department_id,
    grades.id AS grade_id
  FROM epe_import_users staged
  LEFT JOIN performance_db.departments departments
    ON departments.name = staged.department_name
  LEFT JOIN performance_db.grades grades
    ON grades.code = staged.grade_code
),
inserted AS (
  INSERT INTO performance_db.users (
    full_name,
    email,
    password_hash,
    role,
    department_id,
    grade_id,
    job_title,
    join_date,
    work_category,
    is_project_participant,
    can_evaluate,
    can_be_evaluated
  )
  SELECT
    full_name,
    email,
    NULL,
    role::performance_db.user_role_type,
    department_id,
    grade_id,
    job_title,
    join_date,
    work_category,
    is_project_participant,
    can_evaluate,
    can_be_evaluated
  FROM resolved
  WHERE NOT EXISTS (
    SELECT 1
    FROM performance_db.users existing
    WHERE existing.email = resolved.email
  )
  ON CONFLICT (email) DO NOTHING
  RETURNING 1
)
SELECT 'users_inserted' AS metric, count(*)::text AS value FROM inserted;

WITH resolved AS (
  SELECT
    staged.*,
    departments.id AS department_id,
    grades.id AS grade_id
  FROM epe_import_users staged
  LEFT JOIN performance_db.departments departments
    ON departments.name = staged.department_name
  LEFT JOIN performance_db.grades grades
    ON grades.code = staged.grade_code
),
changed AS (
  UPDATE performance_db.users users
  SET full_name = resolved.full_name,
      role = resolved.role::performance_db.user_role_type,
      department_id = resolved.department_id,
      grade_id = resolved.grade_id,
      job_title = resolved.job_title,
      join_date = resolved.join_date,
      work_category = resolved.work_category,
      is_project_participant = resolved.is_project_participant,
      can_evaluate = resolved.can_evaluate,
      can_be_evaluated = resolved.can_be_evaluated
  FROM resolved
  WHERE users.email = resolved.email
    AND (
      users.full_name,
      users.role,
      users.department_id,
      users.grade_id,
      users.job_title,
      users.join_date,
      users.work_category,
      users.is_project_participant,
      users.can_evaluate,
      users.can_be_evaluated
    ) IS DISTINCT FROM (
      resolved.full_name,
      resolved.role::performance_db.user_role_type,
      resolved.department_id,
      resolved.grade_id,
      resolved.job_title,
      resolved.join_date,
      resolved.work_category,
      resolved.is_project_participant,
      resolved.can_evaluate,
      resolved.can_be_evaluated
    )
  RETURNING 1
)
SELECT 'users_updated' AS metric, count(*)::text AS value FROM changed;

WITH changed AS (
  UPDATE performance_db.users users
  SET manager_id = managers.id
  FROM epe_import_users staged
  LEFT JOIN performance_db.users managers
    ON managers.email = staged.manager_email
  WHERE users.email = staged.email
    AND users.manager_id IS DISTINCT FROM managers.id
  RETURNING 1
)
SELECT 'manager_links_changed' AS metric, count(*)::text AS value FROM changed;

DO $$
DECLARE
  actual_count integer;
BEGIN
  SELECT count(*) INTO actual_count FROM performance_db.users;
  IF actual_count <> 89 THEN
    RAISE EXCEPTION
      'Post-import user count is %, expected 89', actual_count;
  END IF;
END
$$;

COMMIT;
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", required=True, type=Path)
    parser.add_argument("--source-snapshot", required=True, type=Path)
    parser.add_argument("--sql-output", required=True, type=Path)
    parser.add_argument("--model-output", required=True, type=Path)
    args = parser.parse_args()

    source_snapshot = json.loads(args.source_snapshot.read_text())
    export_records = load_export(args.xlsx)
    model = build_model(export_records, source_snapshot)
    sql = build_sql(model)

    args.sql_output.write_text(sql)
    args.model_output.write_text(
        json.dumps(model, ensure_ascii=False, indent=2)
    )

    role_counts = Counter(row["role"] for row in model)
    print(
        json.dumps(
            {
                "export_rows": len(export_records),
                "target_users": len(model),
                "roles": dict(sorted(role_counts.items())),
                "project_participants": sum(
                    row["is_project_participant"] for row in model
                ),
                "read_only": sum(
                    not row["can_evaluate"] and not row["can_be_evaluated"]
                    for row in model
                ),
                "h1_out_of_scope": sorted(
                    row["email"] for row in model if not row["h1_in_scope"]
                ),
                "sql_output": str(args.sql_output),
                "model_output": str(args.model_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
