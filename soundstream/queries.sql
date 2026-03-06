-- queries.sql


-- 1. Tracks Per Artist: Top 10 artists by track count.
select a.name, count(t.track_id) as track_count
from artists a
left join albums al on a.artist_id = al.artist_id
left join tracks t on al.album_id = t.album_id
order by track_count
limit 10;
  


-- 2. Longest Album: Album with highest total duration.
select al.title, sum(t.duration_seconds) as total_duration
from albums al
left join tracks t on al.album_id = t.album_id
group by al.title
order by total_duration desc
limit 1;



-- 3. Artists by Country: Count of artists per country.
select distinct country, count(*) as artists
from artists
group by country;





-- 4. Recent Albums: Albums released in the last 365 days.
select title
from albums
where release_date >= now() - interval '365 days';





-- 5. Longest Tracks: Top 20 tracks > 5 minutes (formatted as M:SS).
select title, 
    to_char((duration_seconds * interval '1 second), 
    'MI:SS') as duration
from tracks
where duration_seconds > 300
order by duration_seconds desc
limit 20;