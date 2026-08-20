-- DROP SCHEMA performance_db;

CREATE SCHEMA performance_db AUTHORIZATION "admin";

-- DROP TYPE performance_db."user_role_type";

CREATE TYPE performance_db."user_role_type" AS ENUM (
	'admin',
	'c_level',
	'manager',
	'employee',
	'hr');

-- DROP TYPE performance_db."work_category_type";

CREATE TYPE performance_db."work_category_type" AS ENUM (
	'general',
	'project',
	'hybrid',
	'tender');

-- DROP SEQUENCE performance_db.criteria_id_seq;

CREATE SEQUENCE performance_db.criteria_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE performance_db.departments_id_seq;

CREATE SEQUENCE performance_db.departments_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE performance_db.evaluation_periods_id_seq;

CREATE SEQUENCE performance_db.evaluation_periods_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE performance_db.evaluation_scores_id_seq;

CREATE SEQUENCE performance_db.evaluation_scores_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE performance_db.evaluations_id_seq;

CREATE SEQUENCE performance_db.evaluations_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE performance_db.grades_id_seq;

CREATE SEQUENCE performance_db.grades_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE performance_db.users_id_seq;

CREATE SEQUENCE performance_db.users_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;-- performance_db.criteria definition

-- Drop table

-- DROP TABLE performance_db.criteria;

CREATE TABLE performance_db.criteria (
	id serial4 NOT NULL,
	title varchar(200) NOT NULL,
	category varchar(50) NOT NULL,
	description text NULL,
	score_definitions jsonb NULL,
	weight numeric(5, 2) DEFAULT 1.0 NULL,
	is_active bool DEFAULT true NULL,
	target_audience varchar(50) DEFAULT 'all'::character varying NULL,
	level_0_desc text NULL,
	level_1_desc text NULL,
	level_2_desc text NULL,
	level_3_desc text NULL,
	level_4_desc text NULL,
	level_5_desc text NULL,
	level_6_desc text NULL,
	level_7_desc text NULL,
	level_8_desc text NULL,
	level_9_desc text NULL,
	level_10_desc text NULL,
	selfassesment bool DEFAULT true NOT NULL,
	c_level_only bool DEFAULT false NOT NULL,
	for_manager bool DEFAULT true NOT NULL,
	CONSTRAINT criteria_pkey PRIMARY KEY (id)
);


-- performance_db.departments definition

-- Drop table

-- DROP TABLE performance_db.departments;

CREATE TABLE performance_db.departments (
	id serial4 NOT NULL,
	"name" varchar(100) NOT NULL,
	description text NULL,
	CONSTRAINT departments_name_key UNIQUE (name),
	CONSTRAINT departments_pkey PRIMARY KEY (id)
);


-- performance_db.evaluation_periods definition

-- Drop table

-- DROP TABLE performance_db.evaluation_periods;

CREATE TABLE performance_db.evaluation_periods (
	id serial4 NOT NULL,
	"name" varchar(100) NOT NULL,
	start_date date NULL,
	end_date date NULL,
	is_active bool DEFAULT true NULL,
	CONSTRAINT evaluation_periods_pkey PRIMARY KEY (id)
);


-- performance_db.global_settings definition

-- Drop table

-- DROP TABLE performance_db.global_settings;

CREATE TABLE performance_db.global_settings (
	setting_key varchar(100) NOT NULL,
	setting_value numeric(10, 4) NULL,
	description text NULL,
	CONSTRAINT global_settings_pkey PRIMARY KEY (setting_key)
);


-- performance_db.grades definition

-- Drop table

-- DROP TABLE performance_db.grades;

CREATE TABLE performance_db.grades (
	id serial4 NOT NULL,
	code varchar(10) NOT NULL,
	coefficient numeric(5, 2) DEFAULT 1.00 NOT NULL,
	description text NULL,
	CONSTRAINT grades_code_key UNIQUE (code),
	CONSTRAINT grades_pkey PRIMARY KEY (id)
);


-- performance_db.users definition

-- Drop table

-- DROP TABLE performance_db.users;

CREATE TABLE performance_db.users (
	id serial4 NOT NULL,
	full_name varchar(150) NOT NULL,
	email varchar(150) NOT NULL,
	password_hash varchar(255) NULL,
	"role" performance_db."user_role_type" DEFAULT 'employee'::performance_db.user_role_type NOT NULL,
	department_id int4 NULL,
	grade_id int4 NULL,
	manager_id int4 NULL,
	job_title varchar(100) NULL,
	employment_type varchar(50) DEFAULT 'Full-time'::character varying NULL,
	join_date date NULL,
	salary_current numeric(12, 2) NULL,
	salary_proposed numeric(12, 2) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	is_project_participant bool DEFAULT false NOT NULL,
	work_category varchar(50) DEFAULT 'general'::character varying NULL,
	has_subordinates bool DEFAULT false NOT NULL,
	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_pkey PRIMARY KEY (id),
	CONSTRAINT users_department_id_fkey FOREIGN KEY (department_id) REFERENCES performance_db.departments(id),
	CONSTRAINT users_grade_id_fkey FOREIGN KEY (grade_id) REFERENCES performance_db.grades(id),
	CONSTRAINT users_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES performance_db.users(id)
);


-- performance_db.evaluations definition

-- Drop table

-- DROP TABLE performance_db.evaluations;

CREATE TABLE performance_db.evaluations (
	id serial4 NOT NULL,
	period_id int4 NULL,
	subject_id int4 NULL,
	evaluator_id int4 NULL,
	status varchar(20) DEFAULT 'draft'::character varying NULL,
	general_comment text NULL,
	private_comment text NULL,
	calculated_score numeric(10, 2) NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	evaluation_type varchar(20) DEFAULT 'manager'::character varying NULL,
	is_self_evaluation bool DEFAULT false NOT NULL,
	evaluation_source varchar(20) DEFAULT 'manager'::character varying NULL,
	CONSTRAINT evaluations_pkey PRIMARY KEY (id),
	CONSTRAINT evaluations_evaluator_id_fkey FOREIGN KEY (evaluator_id) REFERENCES performance_db.users(id),
	CONSTRAINT evaluations_period_id_fkey FOREIGN KEY (period_id) REFERENCES performance_db.evaluation_periods(id),
	CONSTRAINT evaluations_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES performance_db.users(id)
);
CREATE UNIQUE INDEX idx_evaluations_unique_pair ON performance_db.evaluations USING btree (subject_id, evaluator_id, is_self_evaluation) WHERE (is_self_evaluation = false);


-- performance_db.evaluation_scores definition

-- Drop table

-- DROP TABLE performance_db.evaluation_scores;

CREATE TABLE performance_db.evaluation_scores (
	id serial4 NOT NULL,
	evaluation_id int4 NULL,
	criteria_id int4 NULL,
	score_value int4 NOT NULL,
	"comment" text NULL,
	CONSTRAINT evaluation_scores_pkey PRIMARY KEY (id),
	CONSTRAINT evaluation_scores_criteria_id_fkey FOREIGN KEY (criteria_id) REFERENCES performance_db.criteria(id),
	CONSTRAINT evaluation_scores_evaluation_id_fkey FOREIGN KEY (evaluation_id) REFERENCES performance_db.evaluations(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX idx_evaluation_scores_unique ON performance_db.evaluation_scores USING btree (evaluation_id, criteria_id);


-- performance_db.invite_tokens definition

-- Drop table

-- DROP TABLE performance_db.invite_tokens;

CREATE TABLE performance_db.invite_tokens (
	id serial4 NOT NULL,
	token varchar(64) NOT NULL,
	created_by int4 NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	expires_at timestamp NOT NULL,
	is_used bool DEFAULT false NULL,
	used_by int4 NULL,
	used_at timestamp NULL,
	CONSTRAINT invite_tokens_pkey PRIMARY KEY (id),
	CONSTRAINT invite_tokens_token_key UNIQUE (token),
	CONSTRAINT invite_tokens_created_by_fkey FOREIGN KEY (created_by) REFERENCES performance_db.users(id),
	CONSTRAINT invite_tokens_used_by_fkey FOREIGN KEY (used_by) REFERENCES performance_db.users(id)
);
CREATE INDEX idx_invite_tokens_token ON performance_db.invite_tokens USING btree (token);
CREATE INDEX idx_invite_tokens_expires ON performance_db.invite_tokens USING btree (expires_at);


-- performance_db.email_verification_codes definition

-- Drop table

-- DROP TABLE performance_db.email_verification_codes;

CREATE TABLE performance_db.email_verification_codes (
	id serial4 NOT NULL,
	email varchar(150) NOT NULL,
	code varchar(6) NOT NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	expires_at timestamp NOT NULL,
	is_verified bool DEFAULT false NULL,
	verified_at timestamp NULL,
	attempts int4 DEFAULT 0 NULL,
	CONSTRAINT email_verification_codes_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_verification_email ON performance_db.email_verification_codes USING btree (email);
CREATE INDEX idx_verification_code ON performance_db.email_verification_codes USING btree (code);
CREATE INDEX idx_verification_expires ON performance_db.email_verification_codes USING btree (expires_at);


-- performance_db.score_coefficients definition

-- Drop table

-- DROP TABLE performance_db.score_coefficients;

CREATE TABLE performance_db.score_coefficients (
	id serial4 NOT NULL,
	criteria_id int4 NOT NULL,
	score_level int4 NOT NULL,
	coefficient numeric(5, 2) DEFAULT 1.0 NOT NULL,
	CONSTRAINT score_coefficients_pkey PRIMARY KEY (id),
	CONSTRAINT score_coefficients_criteria_id_fkey FOREIGN KEY (criteria_id) REFERENCES performance_db.criteria(id) ON DELETE CASCADE,
	CONSTRAINT score_coefficients_score_level_check CHECK (score_level >= 0 AND score_level <= 10),
	CONSTRAINT score_coefficients_unique UNIQUE (criteria_id, score_level)
);
CREATE INDEX idx_score_coefficients_criteria ON performance_db.score_coefficients USING btree (criteria_id);