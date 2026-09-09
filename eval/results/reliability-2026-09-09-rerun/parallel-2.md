# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 100
- scoring: v2 (query trajectory and completion reported separately)
- Natural-language answer correctness is not measured.

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 32/100 (32%) |
| query-trajectory hit rate | 47/100 (47%) |
| completed with SQL hit | 46/100 (46%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 3.10 |
| tokens per case (in+out) | 11,758 |
| prompt cache hit rate | 87% |
| latency per case | 12.5s |
| cost per case (upper bound) | $0.0027 |
| unmeasured (upstream unreachable) | 0 |

## Cases

| id | kind | SQL hit | completed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|---|
| california_schools_36 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| california_schools_37 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_39 | public | ❌ | ✅ | ❌ | 0 | 7 | result sets differ |
| california_schools_41 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_45 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| california_schools_72 | public | ❌ | ✅ | ❌ | 0 | 7 | result sets differ |
| california_schools_85 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| card_games_340 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| card_games_345 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_346 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| card_games_358 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_368 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_379 | public | ✅ | ❌ | ✅ | 0 | 8 | no final answer after 8 turns |
| card_games_397 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| card_games_407 | public | ❌ | ❌ | ❌ | 0 | 7 | no final answer after 8 turns |
| card_games_409 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_412 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| card_games_415 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| card_games_422 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_459 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_468 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_479 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| card_games_480 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| codebase_community_539 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_557 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| codebase_community_573 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_581 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_604 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| codebase_community_633 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| codebase_community_634 | public | ❌ | ✅ | ❌ | 0 | 7 | result sets differ |
| codebase_community_640 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| codebase_community_678 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| codebase_community_685 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| codebase_community_701 | public | ❌ | ❌ | ❌ | 0 | 5 | reference expected_sql failed (case bug?): interrupted |
| codebase_community_707 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| debit_card_specializing_1481 | public | ❌ | ❌ | ❌ | 0 | 7 | no final answer after 8 turns |
| debit_card_specializing_1484 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| european_football_2_1030 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1079 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1134 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| european_football_2_1135 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| financial_115 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| financial_117 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| financial_128 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| financial_159 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| financial_168 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| financial_169 | public | ❌ | ❌ | ❌ | 0 | 2 | multiple SQL statements are not allowed (2 found); send exactly one SELECT |
| financial_189 | public | ❌ | ❌ | ❌ | 0 | 7 | no final answer after 8 turns |
| financial_92 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| financial_93 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| financial_95 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| formula_1_866 | public | ❌ | ❌ | ❌ | 0 | 2 | multiple SQL statements are not allowed (2 found); send exactly one SELECT |
| formula_1_869 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| formula_1_877 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| formula_1_897 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| formula_1_906 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| formula_1_909 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_910 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_940 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| formula_1_955 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| formula_1_960 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_972 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| formula_1_977 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| formula_1_990 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| student_club_1317 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| student_club_1346 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1350 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| student_club_1352 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1361 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| student_club_1376 | public | ✅ | ✅ | ❌ | 0 | 6 |  |
| student_club_1378 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1399 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| student_club_1405 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| student_club_1409 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1422 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| student_club_1426 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_717 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_719 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_728 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| superhero_730 | public | ✅ | ✅ | ✅ | 0 | 4 |  |
| superhero_733 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_751 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| superhero_758 | public | ✅ | ✅ | ❌ | 0 | 5 |  |
| superhero_765 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_806 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1168 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| thrombosis_prediction_1195 | public | ❌ | ❌ | ❌ | 0 | 7 | no final answer after 8 turns |
| thrombosis_prediction_1201 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1209 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| thrombosis_prediction_1252 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| thrombosis_prediction_1256 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1270 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| toxicology_200 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| toxicology_206 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| toxicology_212 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| toxicology_228 | public | ✅ | ✅ | ✅ | 0 | 3 |  |
| toxicology_242 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| toxicology_268 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| toxicology_282 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| toxicology_327 | public | ✅ | ✅ | ✅ | 0 | 2 |  |

## Failing cases — SQL comparison

### california_schools_36

- question: Under whose administration is the school with the highest number of students scoring 1500 or more on the SAT? Indicate their full names.
- expected: `SELECT T2.AdmFName1, T2.AdmLName1, T2.AdmFName2, T2.AdmLName2, T2.AdmFName3, T2.AdmLName3 FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY T1.NumGE1500 DESC LIMIT 1`
- agent: `SELECT * FROM satscores WHERE cds = '38684783833407'`

### california_schools_37

- question: What is the complete address of the school with the lowest excellence rate? Indicate the Street, City, Zip and State.
- expected: `SELECT T2.Street, T2.City, T2.State, T2.Zip FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY CAST(T1.NumGE1500 AS REAL) / T1.NumTstTakr ASC LIMIT 1`
- agent: `SELECT s.cds, s.sname, sc.School, sc.Street, sc.City, sc.Zip, sc.State FROM satscores s JOIN schools sc ON sc.CDSCode = s.cds WHERE s.rtype='S' AND s.NumTstTakr > 0 AND s.NumGE1500 = 0 ORDER BY s.NumTstTakr DESC, sc.School`

### california_schools_39

- question: What is the average number of test takers from Fresno schools that opened between 1/1/1980 and 12/31/1980?
- expected: `SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'`
- agent: `SELECT t.cname, COUNT(*) FROM schools s JOIN satscores t ON t.cds = s.CDSCode WHERE s.County = 'Fresno' AND s.OpenDate BETWEEN '1980-01-01' AND '1980-12-31' AND t.rtype = 'S' GROUP BY t.cname`

### california_schools_41

- question: List the names of virtual schools that are among the top 5 in their respective counties based on average reading scores.
- expected: `SELECT School FROM (SELECT T2.School,T1.AvgScrRead, RANK() OVER (PARTITION BY T2.County ORDER BY T1.AvgScrRead DESC) AS rnk FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.Virtual = 'F' ) ranked_schools WHERE rnk <= 5`
- agent: `WITH scored AS ( SELECT s.CDSCode, s.School, s.County, t.AvgScrRead FROM schools s JOIN satscores t ON s.CDSCode = t.cds AND t.rtype='S' WHERE t.AvgScrRead IS NOT NULL ), ranked AS ( SELECT CDSCode, School, County, AvgScrRead, RANK() OVER (PARTITION BY County ORDER BY AvgScrRead DESC) AS rnk FROM scored ) SELECT r.School, r.County, r.AvgScrRead, r.rnk FROM ranked r JOIN schools s ON s.CDSCode = r.CDSCode WHERE s.Virtual='F' AND r.rnk <= 5 ORDER BY r.County, r.rnk`

### california_schools_72

- question: How many students from the ages of 5 to 17 are enrolled at the State Special School school in Fremont for the 2014-2015 academic year?
- expected: `SELECT T1.`Enrollment (Ages 5-17)` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1.`Academic Year` BETWEEN 2014 AND 2015`
- agent: `SELECT frpm."School Name", frpm."Enrollment (Ages 5-17)" AS enrollment_5_17 FROM frpm JOIN schools ON frpm.CDSCode = schools.CDSCode WHERE frpm."Academic Year" = '2014-2015' AND schools.EdOpsCode = 'SSS' AND schools.City = 'Fremont'`

### california_schools_85

- question: What is the Percent (%) Eligible Free (K-12) in the school administered by an administrator whose first name is Alusine. List the district code of the school.
- expected: `SELECT T1.`Free Meal Count (K-12)` * 100 / T1.`Enrollment (K-12)`, T1.`District Code` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'`
- agent: `SELECT s.CDSCode, f."District Code", f."Enrollment (K-12)", f."Free Meal Count (K-12)", ROUND(f."Free Meal Count (K-12)" / f."Enrollment (K-12)" * 100, 2) AS pct_eligible_free FROM schools s JOIN frpm f ON f.CDSCode = s.CDSCode WHERE s.AdmFName1 = 'Alusine' OR s.AdmFName2 = 'Alusine' OR s.AdmFName3 = 'Alusine'`

### card_games_340

- question: Which are the cards that have incredibly powerful foils.
- expected: `SELECT id FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL`
- agent: `SELECT COUNT(DISTINCT name) AS distinct_names FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL;`

### card_games_346

- question: List all the card id and artist with unknown power which are legal for commander play format.
- expected: `SELECT T1.id, T1.artist FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T2.status = 'Legal' AND T2.format = 'commander' AND (T1.power IS NULL OR T1.power = '*')`
- agent: `SELECT COUNT(*) AS total_rows, COUNT(DISTINCT c.id) AS distinct_ids, SUM(CASE WHEN c.artist IS NULL THEN 1 ELSE 0 END) AS null_artist_rows FROM cards c JOIN legalities l ON l.uuid = c.uuid WHERE l.format = 'commander' AND l.status = 'Legal' AND (c.power = '*' OR c.power IS NULL);`

### card_games_397

- question: What is the mana cost of cards with a normal layout, a 2003 frame version, with a black border color, and available in paper and mtgo?
- expected: `SELECT manaCost FROM cards WHERE availability = 'mtgo,paper' AND borderColor = 'black' AND frameVersion = 2003 AND layout = 'normal'`
- agent: `SELECT COUNT(*) AS total_cards, COUNT(DISTINCT manaCost) AS distinct_mana_costs, COUNT(manaCost) AS cards_with_mana_cost FROM cards WHERE layout = 'normal' AND frameVersion = '2003' AND borderColor = 'black' AND availability = 'mtgo,paper';`

### card_games_407

- question: Lists all types of cards in German.
- expected: `SELECT T1.subtypes, T1.supertypes FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T2.language = 'German' AND T1.subtypes IS NOT NULL AND T1.supertypes IS NOT NULL`
- agent: `WITH german_cards AS ( SELECT DISTINCT c.uuid, c.supertypes AS st, c.subtypes AS sb FROM cards c JOIN (SELECT DISTINCT uuid FROM foreign_data WHERE language = 'German') g ON g.uuid = c.uuid WHERE c.supertypes IS NOT NULL AND c.subtypes IS NOT NULL ), all_types AS ( SELECT j.value AS type_value FROM german_cards gc, json_each('["' || replace(gc.st, ',', '","') || '"]') j UNION SELECT j2.value FROM german_cards gc, json_each('["' || replace(gc.sb, ',', '","') || '"]') j2 ) SELECT type_value FROM all_types ORDER BY type_value LIMIT -1 OFFSET 200`

### card_games_412

- question: What is the foreign name of the card in French of type Creature, normal layout and black border color, by artist Matthew D. Wilson?
- expected: `SELECT name FROM foreign_data WHERE uuid IN ( SELECT uuid FROM cards WHERE types = 'Creature' AND layout = 'normal' AND borderColor = 'black' AND artist = 'Matthew D. Wilson' ) AND language = 'French'`
- agent: `SELECT COUNT(*) AS total_cards, COUNT(DISTINCT name) AS distinct_names FROM cards WHERE artist = 'Matthew D. Wilson'`

### card_games_422

- question: What is the language of the card with the multiverse number 149934?
- expected: `SELECT language FROM foreign_data WHERE multiverseid = 149934`
- agent: `SELECT language, name, multiverseid FROM foreign_data WHERE multiverseid = 149934;`

### card_games_459

- question: Which card costs more converted mana, "Serra Angel" or "Shrine Keeper"?
- expected: `SELECT name FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper') ORDER BY convertedManaCost DESC LIMIT 1`
- agent: `SELECT name, convertedManaCost FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper');`

### card_games_480

- question: What is the Italian flavor text of the card "Ancestor's Chosen"?
- expected: `SELECT T2.flavorText FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T2.uuid = T1.uuid WHERE T1.name = 'Ancestor''s Chosen' AND T2.language = 'Italian'`
- agent: `SELECT uuid, name, language, flavorText, multiverseid FROM foreign_data WHERE uuid IN ('5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c','b7c19924-b4bf-56fc-aa73-f586e940bd42','7a7e2e9b-93ad-5616-8e3f-ed53a06acfd4','02f098cf-93bc-5a4e-8d29-724d3b273cda') AND language = 'Italian';`

### codebase_community_557

- question: Among the posts with a score of over 5, what is the percentage of them being owned by an elder user?
- expected: `SELECT CAST(SUM(IIF(T2.Age > 65, 1, 0)) AS REAL) * 100 / COUNT(T1.Id) FROM posts AS T1 INNER JOIN users AS T2 ON T1.OwnerUserId = T2.Id WHERE T1.Score > 5`
- agent: `SELECT 100.0 * COUNT(CASE WHEN u.Age > 65 THEN 1 END) / COUNT(*) AS elder_owned_percentage FROM posts p LEFT JOIN users u ON p.OwnerUserId = u.Id WHERE p.Score > 5;`

### codebase_community_604

- question: What is the average of the up votes and the average user age for users creating more than 10 posts?
- expected: `SELECT AVG(T1.UpVotes), AVG(T1.Age) FROM users AS T1 INNER JOIN ( SELECT OwnerUserId, COUNT(*) AS post_count FROM posts GROUP BY OwnerUserId HAVING post_count > 10) AS T2 ON T1.Id = T2.OwnerUserId`
- agent: `WITH qualifying_users AS ( SELECT OwnerUserId AS UserId FROM posts WHERE OwnerUserId IS NOT NULL GROUP BY OwnerUserId HAVING COUNT(*) > 10 ) SELECT SUM(u.UpVotes) * 1.0 / COUNT(u.Id) AS avg_up_votes, SUM(u.Age) * 1.0 / COUNT(u.Id) AS avg_user_age FROM users u JOIN qualifying_users q ON u.Id = q.UserId;`

### codebase_community_633

- question: Which post by slashnick has the most answers count? State the post ID.
- expected: `SELECT T2.PostId FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'slashnick' ORDER BY T3.AnswerCount DESC LIMIT 1`
- agent: `SELECT COUNT(*) AS total_posts, SUM(CASE WHEN OwnerDisplayName IS NOT NULL THEN 1 ELSE 0 END) AS with_dispname, SUM(CASE WHEN OwnerUserId IS NULL THEN 1 ELSE 0 END) AS null_owner FROM posts`

### codebase_community_634

- question: Among posts by Harvey Motulsky and Noah Snyder, which one has higher popularity?
- expected: `SELECT T1.DisplayName FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' GROUP BY T1.DisplayName ORDER BY SUM(T3.ViewCount) DESC LIMIT 1`
- agent: `WITH user_posts AS ( SELECT u.DisplayName AS DisplayName, p.ViewCount AS ViewCount FROM users u LEFT JOIN posts p ON p.OwnerUserId = u.Id WHERE u.DisplayName IN ('Harvey Motulsky', 'Noah Snyder') ) SELECT DisplayName, COUNT(ViewCount) AS question_count_with_views, COALESCE(SUM(ViewCount), 0) AS total_views FROM user_posts GROUP BY DisplayName ORDER BY total_views DESC;`

### codebase_community_640

- question: Calculate the difference in view count from post posted by Mornington and view count from posts posted by Amos.
- expected: `SELECT SUM(IIF(T1.DisplayName = 'Mornington', T3.ViewCount, 0)) - SUM(IIF(T1.DisplayName = 'Amos', T3.ViewCount, 0)) AS diff FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T3.Id = T2.PostId`
- agent: `SELECT Id, PostTypeId, OwnerUserId, OwnerDisplayName, Title, ViewCount FROM posts WHERE OwnerUserId = 47;`

### codebase_community_678

- question: Which post by Harvey Motulsky has the most views? Please give the id and title of this post.
- expected: `SELECT T2.Id, T2.Title FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.DisplayName = 'Harvey Motulsky' ORDER BY T2.ViewCount DESC LIMIT 1`
- agent: `SELECT p.Id, p.Title, p.ViewCount FROM posts p JOIN users u ON p.OwnerUserId = u.Id WHERE u.DisplayName = 'Harvey Motulsky' ORDER BY p.ViewCount DESC LIMIT 1;`

### codebase_community_685

- question: Identify the total views on the post 'Computer Game Datasets'. Name the user who posted it last time.
- expected: `SELECT T2.ViewCount, T3.DisplayName FROM postHistory AS T1 INNER JOIN posts AS T2 ON T1.PostId = T2.Id INNER JOIN users AS T3 ON T2.LastEditorUserId = T3.Id WHERE T1.Text = 'Computer Game Datasets'`
- agent: `SELECT Id, PostHistoryTypeId, PostId, UserId, UserDisplayName, CreationDate, substr(Text,1,80) AS txt FROM postHistory WHERE PostId = 8222 ORDER BY CreationDate`

### debit_card_specializing_1481

- question: What is the difference in the annual average consumption of the customers with the least amount of consumption paid in CZK for 2013 between SME and LAM, LAM and KAM, and KAM and SME?
- expected: `SELECT CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' AND T2.Consumption = ( SELECT MIN(Consumption) FROM yearmonth ) AND T2.Date BETWEEN 201301 AND 201312`
- agent: `WITH czk AS ( SELECT CustomerID, Segment FROM customers WHERE Currency='CZK' AND Segment IN ('SME','LAM','KAM') ), tot AS ( SELECT y.CustomerID, c.Segment, SUM(y.Consumption) AS total2013 FROM yearmonth y JOIN czk c ON c.CustomerID = y.CustomerID WHERE substr(y.Date,1,4)='2013' GROUP BY y.CustomerID, c.Segment ), mn AS ( SELECT Segment, MIN(total2013) AS min_total FROM tot GROUP BY Segment ) SELECT t.Segment, t.CustomerID, t.total2013 FROM tot t JOIN mn m ON m.Segment = t.Segment AND m.min_total = t.total2013 ORDER BY t.Segment`

### debit_card_specializing_1484

- question: How many more "discount" gas stations does the Czech Republic have compared to Slovakia?
- expected: `SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'`
- agent: `SELECT SUM(CASE WHEN Country = 'CZE' THEN 1 ELSE 0 END) AS cze_discount, SUM(CASE WHEN Country = 'SVK' THEN 1 ELSE 0 END) AS svk_discount, SUM(CASE WHEN Country = 'CZE' THEN 1 ELSE 0 END) - SUM(CASE WHEN Country = 'SVK' THEN 1 ELSE 0 END) AS difference FROM gasstations WHERE Segment = 'Discount'`

### european_football_2_1030

- question: Give the name of the league had the most matches end as draw in the 2016 season?
- expected: `SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1`
- agent: `SELECT l.name AS league_name, SUM(CASE WHEN m.home_team_goal = m.away_team_goal THEN 1 ELSE 0 END) AS draw_count FROM Match m JOIN League l ON m.league_id = l.id WHERE m.season = '2015/2016' GROUP BY l.name ORDER BY draw_count DESC LIMIT 1;`

### european_football_2_1079

- question: Which player is the tallest?
- expected: `SELECT player_name FROM Player ORDER BY height DESC LIMIT 1`
- agent: `SELECT player_name, height FROM Player WHERE height = (SELECT MAX(height) FROM Player);`

### european_football_2_1134

- question: What is the difference between players 6 and 23's jumping scores?
- expected: `SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1`
- agent: `SELECT pa.id, pa.player_api_id, p.player_name, pa.date, pa.jumping FROM Player_Attributes pa JOIN Player p ON p.player_api_id = pa.player_api_id WHERE p.id IN (6, 23) ORDER BY p.id, pa.date;`

### european_football_2_1135

- question: Please provide top four football players' IDs who are among the lowest potential players and prefer to use the right foot when attacking.
- expected: `SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4`
- agent: `SELECT DISTINCT pa.player_api_id, p.player_name, pa.potential FROM Player_Attributes pa LEFT JOIN Player p ON p.player_api_id = pa.player_api_id WHERE pa.preferred_foot = 'right' AND pa.potential IS NOT NULL ORDER BY pa.potential ASC, pa.player_api_id LIMIT 10;`

### financial_115

- question: For the branch which located in the south Bohemia with biggest number of inhabitants, what is the percentage of the male clients?
- expected: `SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY T2.A4 DESC LIMIT 1`
- agent: `SELECT SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) AS males, COUNT(*) AS total, 100.0 * SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) / COUNT(*) AS pct_male FROM client WHERE district_id = 14`

### financial_159

- question: List all the withdrawals in cash transactions that the client with the id 3356 makes.
- expected: `SELECT T4.trans_id FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'`
- agent: `SELECT t.trans_id, t.date, t.amount, t.k_symbol, t.balance FROM trans t JOIN disp d ON d.account_id = t.account_id WHERE d.client_id = 3356 AND t.operation = 'VYBER' ORDER BY t.date, t.trans_id`

### financial_168

- question: What percentage of clients who opened their accounts in the district with an average salary of over 10000 are women?
- expected: `SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000`
- agent: `SELECT COUNT(*) AS accounts_total FROM account`

### financial_169

- question: What was the growth rate of the total amount of loans across all accounts for a male client between 1996 and 1997?
- expected: `SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'`
- agent: `SELECT strftime('%Y', date) AS yr, COUNT(*) AS n, MIN(date) AS min_date, MAX(date) AS max_date FROM loan GROUP BY yr ORDER BY yr;`

### financial_189

- question: Name the account numbers of female clients who are oldest and have lowest average salary?
- expected: `SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1`
- agent: `SELECT c.client_id, c.gender, c.birth_date, d.A2, d.A11 FROM client c JOIN district d ON c.district_id = d.district_id WHERE d.A11 = (SELECT MIN(A11) FROM district) ORDER BY c.birth_date LIMIT 10;`

### financial_95

- question: List out the account numbers of clients who are youngest and have highest average salary?
- expected: `SELECT T1.account_id FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id`
- agent: `SELECT c.client_id, c.birth_date, c.district_id, d.A11 FROM client c JOIN district d ON c.district_id = d.district_id WHERE d.A11 = (SELECT MAX(A11) FROM district) AND c.birth_date = (SELECT MAX(c2.birth_date) FROM client c2 JOIN district d2 ON c2.district_id = d2.district_id WHERE d2.A11 = (SELECT MAX(A11) FROM district));`

### formula_1_866

- question: Who was the player that got the lap time of 0:01:27 in the race No. 161? Show his introduction website.
- expected: `SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'`
- agent: `SELECT d.driverId, d.forename, d.surname, d.url, lt.lap, lt.time FROM lapTimes lt JOIN drivers d ON d.driverId = lt.driverId WHERE lt.raceId = 161 AND lt.time LIKE '1:27%' ORDER BY lt.driverId, lt.lap;`

### formula_1_869

- question: For the constructor which got the highest point in the race No. 9 , what is its introduction website?
- expected: `SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1`
- agent: `SELECT c.name, c.url, cr.points FROM constructorResults cr JOIN constructors c ON c.constructorId = cr.constructorId WHERE cr.raceId = 9 ORDER BY cr.points DESC`

### formula_1_877

- question: For all the drivers who finished the game in race No. 872, who is the youngest?
- expected: `SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1`
- agent: `SELECT d.driverId, d.forename, d.surname, d.dob FROM results r JOIN drivers d ON d.driverId = r.driverId WHERE r.raceId = 872 AND r.time IS NOT NULL AND r.time != '' ORDER BY d.dob DESC LIMIT 1;`

### formula_1_897

- question: Name the driver with the most winning. Mention his nationality and what is his maximum point scores.
- expected: `SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1`
- agent: `SELECT MAX(points) AS max_standings_points FROM driverStandings WHERE driverId = 30;`

### formula_1_906

- question: Which was Lewis Hamilton first race? What was his points recorded for his first race event?
- expected: `SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1`
- agent: `SELECT r.name AS first_race, r.date, res.points FROM results res JOIN races r ON r.raceId = res.raceId JOIN drivers d ON d.driverId = res.driverId WHERE d.forename = 'Lewis' AND d.surname = 'Hamilton' ORDER BY r.year ASC, r.round ASC LIMIT 1;`

### formula_1_955

- question: What is the average time in seconds of champion for each year, before year 1975?
- expected: `WITH time_in_seconds AS ( SELECT T2.year, T2.raceId, T1.positionOrder, CASE WHEN T1.positionOrder = 1 THEN (CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600) + (CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60) + CAST(SUBSTR(T1.time, 6,2) AS REAL ) + CAST(SUBSTR(T1.time, 9) AS REAL)/1000 ELSE 0 END AS time_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T1.time IS NOT NULL ), champion_time AS ( SELECT year, raceId, time_seconds FROM time_in_seconds WHERE positionOrder = 1 ) SELECT year, AVG(time_seconds) FROM champion_time WHERE year < 1975 GROUP BY year HAVING AVG(time_seconds) IS NOT NULL`
- agent: `WITH champ AS ( SELECT r.year, res.time AS t, CAST(substr(res.time,1,instr(res.time,':')-1) AS REAL) * 3600.0 + CAST(substr(substr(res.time,instr(res.time,':')+1),1, instr(substr(res.time,instr(res.time,':')+1),':')-1) AS REAL) * 60.0 + CAST(substr(res.time, instr(res.time,':')+1 + instr(substr(res.time,instr(res.time,':')+1),':')) AS REAL) AS secs FROM results res JOIN races r ON res.raceId = r.raceId WHERE r.year < 1975 AND res.positionOrder = 1 AND res.time IS NOT NULL ) SELECT year, ROUND(AVG(secs), 3) AS avg_seconds FROM champ GROUP BY year ORDER BY year`

### formula_1_972

- question: Which drivers who were born in 1971 and has the fastest lap time on the race? Give id and code of these drivers.
- expected: `SELECT T2.driverId, T2.code FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL`
- agent: `SELECT DISTINCT d.driverId, d.code FROM drivers d JOIN results r ON d.driverId = r.driverId WHERE strftime('%Y', d.dob) = '1971' AND r.fastestLapTime IS NOT NULL AND r.fastestLapTime != '' ORDER BY d.driverId;`

### formula_1_990

- question: What is the constructor reference name of the champion in the 2009 Singapore Grand Prix? Please give its website.
- expected: `SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'`
- agent: `SELECT r.resultId, r.raceId, r.driverId, r.constructorId, r.grid, r.position, r.positionOrder, r.time, r.milliseconds, d.forename, d.surname, c.name AS constructor_name, c.constructorRef, c.url FROM results r JOIN drivers d ON d.driverId = r.driverId JOIN constructors c ON c.constructorId = r.constructorId WHERE r.raceId = 14 AND r.positionOrder = 1`

### student_club_1399

- question: Did Maya Mclean attend the 'Women's Soccer' event?
- expected: `SELECT CASE WHEN T3.event_name = 'Women''s Soccer' THEN 'YES' END AS result FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean'`
- agent: `SELECT a.link_to_member, a.link_to_event FROM attendance a JOIN member m ON a.link_to_member = m.member_id JOIN event e ON a.link_to_event = e.event_id WHERE m.first_name = 'Maya' AND m.last_name = 'Mclean' AND e.event_name = 'Women''s Soccer';`

### student_club_1422

- question: State the category of events were held at MU 215.
- expected: `SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215'`
- agent: `SELECT DISTINCT type FROM event WHERE location = 'MU 215';`

### superhero_728

- question: Rank superheroes from Marvel Comics by their eye color popularity, starting with the most common color.
- expected: `SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour`
- agent: `SELECT c.colour AS eye_colour, COUNT(s.id) AS num_superheroes FROM superhero s JOIN publisher p ON s.publisher_id = p.id JOIN colour c ON s.eye_colour_id = c.id WHERE p.publisher_name = 'Marvel Comics' GROUP BY c.colour ORDER BY num_superheroes DESC, eye_colour`

### superhero_751

- question: List down at least five superpowers of male superheroes.
- expected: `SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male' LIMIT 5`
- agent: `SELECT DISTINCT sp.power_name FROM superhero s JOIN gender g ON s.gender_id = g.id JOIN hero_power hp ON hp.hero_id = s.id JOIN superpower sp ON hp.power_id = sp.id WHERE g.gender = 'Male' ORDER BY sp.power_name LIMIT 10;`

### thrombosis_prediction_1168

- question: The oldest SJS patient's medical laboratory work was completed on what date, and what age was the patient when they initially arrived at the hospital?
- expected: `SELECT T1.Date, STRFTIME('%Y', T2.`First Date`) - STRFTIME('%Y', T2.Birthday),T2.Birthday FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC LIMIT 1`
- agent: `SELECT * FROM Patient WHERE ID = 125619`

### thrombosis_prediction_1195

- question: What is the average blood albumin level for female patients with a PLT greater than 400 who have been diagnosed with SLE?
- expected: `SELECT AVG(T2.ALB) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.PLT > 400 AND T1.Diagnosis = 'SLE' AND T1.SEX = 'F'`
- agent: `SELECT Diagnosis, COUNT(*) FROM Patient GROUP BY Diagnosis ORDER BY COUNT(*) DESC`

### thrombosis_prediction_1209

- question: Please provide the diagnosis of patients with ALT glutamic pylvic transaminase beyond the normal range by ascending order of their date of birth.
- expected: `SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC`
- agent: `SELECT p.Diagnosis FROM Patient p WHERE p.ID IN ( SELECT DISTINCT l.ID FROM Laboratory l WHERE l.GPT > 60 ) ORDER BY p.Birthday ASC;`

### thrombosis_prediction_1252

- question: Among the patients with a normal Ig G level, how many of them have symptoms?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL`
- agent: `SELECT ID, COUNT(*) AS cnt FROM Laboratory GROUP BY ID ORDER BY cnt DESC LIMIT 10`

### thrombosis_prediction_1256

- question: How many patients with a abnormal C-reactive protein don't have their data recorded?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+' ) AND T1.Description IS NULL`
- agent: `SELECT COUNT(DISTINCT p.ID) AS patient_count FROM Patient p JOIN Laboratory l ON l.ID = p.ID WHERE l.CRP = '+' AND p.Description IS NULL`

### toxicology_212

- question: Which element is the least numerous in non-carcinogenic molecules?
- expected: `SELECT T.element FROM (SELECT T1.element, COUNT(DISTINCT T1.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '-' GROUP BY T1.element ORDER BY COUNT(DISTINCT T1.molecule_id) ASC LIMIT 1) t`
- agent: `SELECT a.element, COUNT(*) AS cnt FROM atom a JOIN molecule m ON a.molecule_id = m.molecule_id WHERE m.label = '-' GROUP BY a.element HAVING COUNT(*) = ( SELECT MIN(c) FROM ( SELECT COUNT(*) AS c FROM atom a2 JOIN molecule m2 ON a2.molecule_id = m2.molecule_id WHERE m2.label = '-' GROUP BY a2.element ) )`

### toxicology_282

- question: What is the ratio of Hydrogen elements in molecule ID TR006? List the ratio with its label.
- expected: `WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label`
- agent: `SELECT m.label, SUM(CASE WHEN a.element = 'h' THEN 1 ELSE 0 END) * 1.0 / COUNT(a.atom_id) AS ratio_h FROM molecule m JOIN atom a ON a.molecule_id = m.molecule_id WHERE m.molecule_id = 'TR006' GROUP BY m.molecule_id, m.label`

