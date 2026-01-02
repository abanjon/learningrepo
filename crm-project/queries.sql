-- @query: Leads By Status
SELECT
    status,
    COUNT(*) as lead_count,
    -- Calculate percantage of total (subquery in SELECT)
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM leads), 2) as percentage
FROM leads
GROUP BY status
ORDER BY lead_count DESC;

-- @query: Recent Leads
SELECT
    id,
    company_name,
    contact_person,
    email,
    status,
    created_at,
    CURRENT_DATE - DATE(created_at) AS days_ago
FROM leads
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY created_at DESC;

-- @query: Industry Breakdown
SELECT
    industry,
    COUNT(*) as total_leads,
    COUNT(CASE WHEN STATUS = 'Converted' THEN 1 END) as converted,
    COUNT(CASE WHEN STATUS = 'Qualified' THEN 1 END) as qualified,
    COUNT(CASE WHEN STATUS = 'New' THEN 1 END) as new_leads,
    ROUND(100.0 * COUNT(CASE WHEN status = 'Converted' THEN 1 END) /
          NULLIF(COUNT(*),0), 2) as conversion_rate
 FROM leads
 GROUP BY industry
 HAVING COUNT(*) >= 3
 ORDER BY conversion_rate DESC NULLS LAST;

-- @query: Time-based analysis
SELECT
    status,
    COUNT(*) as count,
    -- MIN/MAX/AVG are aggregate functions
    MIN(created_at) as earliest_lead,
    MAX(created_at) as latest_lead,
    -- EXTRACT gets parts of timestampes (EPOCH = seconds since 1970)
    -- Divide by 86400 to convert secs to days
    ROUND(AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / 86400), 1) as avg_age_days
FROM leads
GROUP BY status
ORDER BY avg_age_days DESC;

-- @query: Email domain analysis
SELECT
    SUBSTRING(email FROM '@(.*)$') AS domain,
    COUNT(*) as lead_count,
    STRING_AGG(company_name, ', ' ORDER BY company_name) as companies
FROM leads
WHERE email IS NOT NULL
GROUP BY domain
ORDER BY lead_count DESC
LIMIT 10;


