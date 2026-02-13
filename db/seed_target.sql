-- Create the companies table in the target (company_data) database
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    industry_vertical VARCHAR(100) NOT NULL,
    founding_year INTEGER NOT NULL,
    arr_thousands NUMERIC(10,1) NOT NULL,
    employee_count INTEGER NOT NULL,
    churn_rate_percent NUMERIC(5,2) NOT NULL,
    yoy_growth_rate_percent NUMERIC(6,2) NOT NULL
);

-- Load data via \copy (run from psql):
-- \copy companies(company_name, industry_vertical, founding_year, arr_thousands, employee_count, churn_rate_percent, yoy_growth_rate_percent) FROM '../sample_data.csv' WITH CSV HEADER
