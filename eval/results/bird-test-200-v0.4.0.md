# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 200

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 64/200 (32%) |
| pass rate after self-repair | 95/200 (48%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 2.63 |
| tokens per case (in+out) | 8,699 |
| prompt cache hit rate | 87% |
| latency per case | 11.8s |
| cost per case (upper bound) | $0.0019 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| california_schools_11 | public | ✅ | ❌ | 0 | 5 |  |
| california_schools_12 | public | ✅ | ❌ | 0 | 5 |  |
| california_schools_17 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| california_schools_23 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| california_schools_24 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| california_schools_25 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| california_schools_26 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| california_schools_27 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| california_schools_40 | public | ✅ | ❌ | 0 | 5 |  |
| california_schools_46 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| california_schools_5 | public | ✅ | ❌ | 0 | 5 |  |
| california_schools_50 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| california_schools_62 | public | ✅ | ❌ | 0 | 4 |  |
| california_schools_83 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| card_games_341 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_347 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| card_games_371 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| card_games_414 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| card_games_424 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_427 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| card_games_440 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_462 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_465 | public | ❌ | ❌ | 1 | 5 | result sets differ |
| card_games_466 | public | ✅ | ✅ | 0 | 2 |  |
| card_games_469 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_472 | public | ✅ | ✅ | 0 | 2 |  |
| card_games_474 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_486 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_522 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_528 | public | ❌ | ❌ | 1 | 6 | result sets differ |
| card_games_529 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| card_games_530 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| codebase_community_537 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_544 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_549 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_563 | public | ✅ | ❌ | 0 | 3 |  |
| codebase_community_567 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_571 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_576 | public | ✅ | ❌ | 0 | 2 |  |
| codebase_community_584 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| codebase_community_629 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_637 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| codebase_community_669 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_682 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| codebase_community_694 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| codebase_community_704 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_705 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_710 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| codebase_community_716 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| debit_card_specializing_1476 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| debit_card_specializing_1493 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| debit_card_specializing_1501 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| debit_card_specializing_1514 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| debit_card_specializing_1525 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| debit_card_specializing_1528 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| debit_card_specializing_1531 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1025 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1028 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1031 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| european_football_2_1032 | public | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1058 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| european_football_2_1068 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| european_football_2_1076 | public | ✅ | ✅ | 0 | 2 |  |
| european_football_2_1078 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1094 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| european_football_2_1096 | public | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1098 | public | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1103 | public | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1107 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1110 | public | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1114 | public | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1139 | public | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1146 | public | ✅ | ✅ | 0 | 1 |  |
| financial_112 | public | ✅ | ❌ | 1 | 3 |  |
| financial_118 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| financial_129 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| financial_137 | public | ✅ | ❌ | 0 | 4 |  |
| financial_138 | public | ✅ | ❌ | 0 | 3 |  |
| financial_152 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| financial_192 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| financial_89 | public | ✅ | ❌ | 0 | 4 |  |
| financial_98 | public | ✅ | ❌ | 0 | 6 |  |
| financial_99 | public | ✅ | ❌ | 0 | 4 |  |
| formula_1_1001 | public | ✅ | ❌ | 0 | 3 |  |
| formula_1_846 | public | ✅ | ❌ | 0 | 2 |  |
| formula_1_854 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_859 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_861 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| formula_1_862 | public | ✅ | ❌ | 0 | 3 |  |
| formula_1_868 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_872 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_875 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_879 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| formula_1_880 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| formula_1_884 | public | ✅ | ❌ | 0 | 2 |  |
| formula_1_895 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_896 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| formula_1_898 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_901 | public | ✅ | ❌ | 1 | 2 |  |
| formula_1_904 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| formula_1_912 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_915 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| formula_1_928 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_931 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_944 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| formula_1_945 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_950 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_954 | public | ✅ | ✅ | 0 | 2 |  |
| formula_1_959 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| formula_1_963 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_964 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_967 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_971 | public | ✅ | ✅ | 0 | 2 |  |
| formula_1_978 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| formula_1_981 | public | ✅ | ✅ | 0 | 2 |  |
| formula_1_989 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| formula_1_994 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| student_club_1312 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1323 | public | ✅ | ❌ | 0 | 5 |  |
| student_club_1334 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| student_club_1338 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| student_club_1340 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| student_club_1356 | public | ✅ | ❌ | 1 | 2 |  |
| student_club_1368 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1371 | public | ✅ | ❌ | 0 | 2 |  |
| student_club_1380 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1381 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| student_club_1387 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| student_club_1389 | public | ✅ | ✅ | 0 | 3 |  |
| student_club_1392 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| student_club_1394 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1398 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1403 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1404 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| student_club_1410 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| student_club_1411 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| student_club_1427 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| student_club_1432 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| student_club_1435 | public | ✅ | ❌ | 0 | 2 |  |
| superhero_723 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_724 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_726 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| superhero_739 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_745 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_747 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_750 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_753 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_764 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_766 | public | ✅ | ❌ | 0 | 5 |  |
| superhero_773 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_775 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_779 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_782 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_788 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| superhero_790 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| superhero_798 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| superhero_800 | public | ✅ | ❌ | 0 | 2 |  |
| superhero_819 | public | ✅ | ❌ | 0 | 3 |  |
| superhero_824 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_825 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1149 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1156 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1164 | public | ✅ | ❌ | 0 | 3 |  |
| thrombosis_prediction_1169 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| thrombosis_prediction_1175 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| thrombosis_prediction_1179 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| thrombosis_prediction_1187 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| thrombosis_prediction_1192 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1205 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| thrombosis_prediction_1220 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1225 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1231 | public | ✅ | ❌ | 1 | 3 |  |
| thrombosis_prediction_1232 | public | ✅ | ❌ | 0 | 3 |  |
| thrombosis_prediction_1238 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| thrombosis_prediction_1239 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1247 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1255 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| thrombosis_prediction_1257 | public | ✅ | ✅ | 0 | 2 |  |
| thrombosis_prediction_1267 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| thrombosis_prediction_1275 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| thrombosis_prediction_1281 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1302 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| toxicology_197 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| toxicology_198 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| toxicology_201 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| toxicology_207 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| toxicology_213 | public | ✅ | ✅ | 0 | 1 |  |
| toxicology_215 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| toxicology_218 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| toxicology_232 | public | ✅ | ✅ | 0 | 2 |  |
| toxicology_234 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| toxicology_236 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| toxicology_243 | public | ✅ | ❌ | 0 | 3 |  |
| toxicology_245 | public | ✅ | ✅ | 0 | 2 |  |
| toxicology_247 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| toxicology_249 | public | ✅ | ✅ | 0 | 1 |  |
| toxicology_253 | public | ✅ | ❌ | 0 | 2 |  |
| toxicology_255 | public | ✅ | ✅ | 0 | 1 |  |
| toxicology_260 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| toxicology_273 | public | ✅ | ❌ | 0 | 3 |  |

## Failing cases — SQL comparison

### california_schools_17

- question: Rank schools by their average score in Writing where the score is greater than 499, showing their charter numbers.
- expected: `SELECT CharterNum, AvgScrWrite, RANK() OVER (ORDER BY AvgScrWrite DESC) AS WritingScoreRank FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds WHERE T2.AvgScrWrite > 499 AND CharterNum is not null`
- agent: `SELECT RANK() OVER (ORDER BY s.AvgScrWrite DESC) AS rank, s.sname AS school_name, sc.CharterNum AS charter_number, s.AvgScrWrite AS avg_writing_score FROM satscores s JOIN schools sc ON sc.CDSCode = s.cds WHERE s.rtype = 'S' AND s.AvgScrWrite > 499 AND sc.CharterNum IS NOT NULL ORDER BY s.AvgScrWrite DESC`

### california_schools_23

- question: List the names of schools with more than 30 difference in enrollements between K-12 and ages 5-17? Please also give the full street adress of the schools.
- expected: `SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.`Enrollment (K-12)` - T2.`Enrollment (Ages 5-17)` > 30`
- agent: `SELECT f."School Name" AS school_name, s.Street || ', ' || s.City || ', ' || s.Zip || ', ' || s.State AS full_address, (f."Enrollment (K-12)" - f."Enrollment (Ages 5-17)") AS enroll_diff FROM frpm f JOIN schools s ON f.CDSCode = s.CDSCode WHERE f."Enrollment (K-12)" IS NOT NULL AND f."Enrollment (Ages 5-17)" IS NOT NULL AND ABS(f."Enrollment (K-12)" - f."Enrollment (Ages 5-17)") > 30 ORDER BY f."School Name"`

### california_schools_24

- question: Give the names of the schools with the percent eligible for free meals in K-12 is more than 0.1 and test takers whose test score is greater than or equal to 1500?
- expected: `SELECT T2.`School Name` FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode WHERE CAST(T2.`Free Meal Count (K-12)` AS REAL) / T2.`Enrollment (K-12)` > 0.1 AND T1.NumGE1500 > 0`
- agent: `SELECT DISTINCT sc.School FROM schools sc JOIN frpm f ON sc.CDSCode = f.CDSCode JOIN satscores s ON sc.CDSCode = s.cds AND s.rtype = 'S' WHERE f."Enrollment (K-12)" > 0 AND (f."Free Meal Count (K-12)" / f."Enrollment (K-12)") > 0.1 AND s.NumGE1500 > 0 ORDER BY sc.School LIMIT 200 OFFSET 600`

### california_schools_25

- question: Name schools in Riverside which the average of average math score for SAT is grater than 400, what is the funding type of these schools?
- expected: `SELECT T1.sname, T2.`Charter Funding Type` FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode WHERE T2.`District Name` LIKE 'Riverside%' GROUP BY T1.sname, T2.`Charter Funding Type` HAVING CAST(SUM(T1.AvgScrMath) AS REAL) / COUNT(T1.cds) > 400`
- agent: `SELECT sch.School AS school_name, sch.FundingType AS funding_type FROM satscores s JOIN schools sch ON sch.CDSCode = s.cds WHERE s.rtype = 'S' AND s.cname = 'Riverside' AND s.AvgScrMath > 400 ORDER BY sch.School`

### california_schools_26

- question: State the names and full communication address of high schools in Monterey which has more than 800 free or reduced price meals for ages 15-17?
- expected: `SELECT T1.`School Name`, T2.Street, T2.City, T2.State, T2.Zip FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Monterey' AND T1.`Free Meal Count (Ages 5-17)` > 800 AND T1.`School Type` = 'High Schools (Public)'`
- agent: `SELECT s."CDSCode", s."School", s."Street", s."City", s."State", s."Zip", s."MailStreet", s."MailCity", s."MailState", s."MailZip" FROM schools s WHERE s."CDSCode" IN ( SELECT f."CDSCode" FROM frpm f WHERE f."County Name" = 'Monterey' AND f."School Type" LIKE '%High School%' AND f."FRPM Count (Ages 5-17)" > 800 ) ORDER BY s."School"`

### california_schools_27

- question: What is the average score in writing for the schools that were opened after 1991 or closed before 2000? List the school names along with the score. Also, list the communication number of the schools if there is any.
- expected: `SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'`
- agent: `SELECT sch.School AS school_name, s.AvgScrWrite AS writing_score, sch.Phone AS phone FROM satscores s JOIN schools sch ON sch.CDSCode = s.cds WHERE s.rtype = 'S' AND (sch.OpenDate > '1991-12-31' OR sch.ClosedDate < '2000-01-01') AND s.AvgScrWrite IS NOT NULL ORDER BY sch.School LIMIT 200 OFFSET 400`

### california_schools_46

- question: Which state special schools have the highest number of enrollees from grades 1 through 12?
- expected: `SELECT T2.School FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.DOC = 31 ORDER BY T1.`Enrollment (K-12)` DESC LIMIT 1`
- agent: `SELECT s.School, f."Enrollment (K-12)" AS enroll_k12 FROM schools s JOIN frpm f ON f.CDSCode = s.CDSCode WHERE s.DOC = '31' ORDER BY f."Enrollment (K-12)" DESC`

### california_schools_50

- question: What is the postal street address for the school with the 7th highest Math average? Indicate the school's name.
- expected: `SELECT T2.MailStreet, T2.School FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY T1.AvgScrMath DESC LIMIT 6, 1`
- agent: `SELECT sc.CDSCode, sc.School, sc.Street, sc.City, sc.Zip, sc.State FROM satscores ss JOIN schools sc ON sc.CDSCode = ss.cds WHERE ss.rtype = 'S' AND ss.AvgScrMath IS NOT NULL ORDER BY ss.AvgScrMath DESC LIMIT 1 OFFSET 6`

### california_schools_83

- question: Of the schools that offers a magnet program serving a grade span of Kindergarten to 8th grade, how many offers Multiple Provision Types? List the number of cities that offers a Kindergarten to 8th grade span and indicate how many schools are there serving such grade span for each city.
- expected: `SELECT T2.City, COUNT(T2.CDSCode) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.Magnet = 1 AND T2.GSoffered = 'K-8' AND T1.`NSLP Provision Status` = 'Multiple Provision Types' GROUP BY T2.City`
- agent: `WITH k8 AS ( SELECT s.City, COUNT(DISTINCT f.CDSCode) AS num_schools FROM frpm f JOIN schools s ON s.CDSCode = f.CDSCode WHERE f."Low Grade" = 'K' AND f."High Grade" = '8' GROUP BY s.City ) SELECT COUNT(*) AS cities_ge2, SUM(CASE WHEN num_schools = 1 THEN 1 ELSE 0 END) AS cities_eq1 FROM k8`

### card_games_341

- question: What are the borderless cards available without powerful foils?
- expected: `SELECT id FROM cards WHERE borderColor = 'borderless' AND (cardKingdomId IS NULL OR cardKingdomId IS NULL)`
- agent: `SELECT DISTINCT name FROM cards WHERE borderColor = 'borderless' AND (cardKingdomFoilId IS NULL OR cardKingdomId IS NULL) ORDER BY name`

### card_games_347

- question: Find all cards illustrated by Stephen Daniel and describe the text of the ruling of these cards. State if these cards have missing or degraded properties and values.
- expected: `SELECT T1.id, T2.text, T1.hasContentWarning FROM cards AS T1 INNER JOIN rulings AS T2 ON T1.uuid = T2.uuid WHERE T1.artist = 'Stephen Daniele'`
- agent: `SELECT c.id, c.name, c.setCode, c.hasContentWarning FROM cards c WHERE c.artist = 'Stephen Daniele' ORDER BY c.id`

### card_games_371

- question: What is the percentage of cards whose language is French among the Story Spotlight cards?
- expected: `SELECT CAST(SUM(CASE WHEN T2.language = 'French' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T1.isStorySpotlight = 1`
- agent: `SELECT ROUND(100.0 * french_story_spotlight / total_story_spotlight, 2) AS percentage FROM ( SELECT (SELECT COUNT(*) FROM cards WHERE isStorySpotlight = 1) AS total_story_spotlight, (SELECT COUNT(DISTINCT c.id) FROM cards c JOIN foreign_data f ON c.uuid = f.uuid WHERE c.isStorySpotlight = 1 AND f.language = 'French') AS french_story_spotlight );`

### card_games_414

- question: What language is the set of 180 cards that belongs to the Ravnica block translated into?
- expected: `SELECT T2.language FROM sets AS T1 INNER JOIN set_translations AS T2 ON T1.code = T2.setCode WHERE T1.block = 'Ravnica' AND T1.baseSetSize = 180`
- agent: `SELECT s.code, s.name, st.language, st.translation FROM sets s JOIN set_translations st ON st.setCode = s.code WHERE s.baseSetSize = 180 AND s.block = 'Ravnica' ORDER BY st.language`

### card_games_424

- question: What proportion of cards do not have a text box with a normal layout?
- expected: `SELECT CAST(SUM(CASE WHEN isTextless = 1 AND layout = 'normal' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM cards`
- agent: `SELECT layout, COUNT(*) AS cnt FROM cards WHERE isTextless = 1 GROUP BY layout ORDER BY cnt DESC;`

### card_games_427

- question: What languages are available in the set known as Archenemy on the magic card market and having the code ARC?
- expected: `SELECT T2.language FROM sets AS T1 INNER JOIN set_translations AS T2 ON T1.code = T2.setCode WHERE T1.mcmName = 'Archenemy' AND T2.setCode = 'ARC'`
- agent: `SELECT fd.language, fd.name, fd.uuid, fd.multiverseid FROM foreign_data fd LIMIT 10`

### card_games_462

- question: What's the Italian name of the set of cards with "Ancestor's Chosen" is in?
- expected: `SELECT translation FROM set_translations WHERE setCode IN ( SELECT setCode FROM cards WHERE name = 'Ancestor''s Chosen' ) AND language = 'Italian'`
- agent: `SELECT DISTINCT c.setCode, s.name AS set_name, st.translation FROM cards c JOIN sets s ON s.code = c.setCode JOIN set_translations st ON st.setCode = c.setCode AND st.language = 'Italian' WHERE c.name = 'Ancestor''s Chosen'`

### card_games_465

- question: For the set of cards with "Ancestor's Chosen" in it, is there a Korean version of it?
- expected: `SELECT IIF(SUM(CASE WHEN T2.language = 'Korean' AND T2.translation IS NOT NULL THEN 1 ELSE 0 END) > 0, 'YES', 'NO') FROM cards AS T1 INNER JOIN set_translations AS T2 ON T2.setCode = T1.setCode WHERE T1.name = 'Ancestor''s Chosen'`
- agent: `SELECT language, COUNT(*) AS cnt FROM foreign_data GROUP BY language ORDER BY cnt DESC`

### card_games_469

- question: Did the set of cards with "Angel of Mercy" appear on Magic: The Gathering Online?
- expected: `SELECT IIF(T2.mtgoCode IS NOT NULL, 'YES', 'NO') FROM cards AS T1 INNER JOIN sets AS T2 ON T2.code = T1.setCode WHERE T1.name = 'Angel of Mercy'`
- agent: `SELECT DISTINCT s.code, s.name, s.mtgoCode FROM cards c JOIN sets s ON c.setCode = s.code WHERE c.name = 'Angel of Mercy' AND s.mtgoCode IS NOT NULL ORDER BY s.code;`

### card_games_474

- question: Among the sets of cards that have an Italian translation, how many of them have a base set number of under 100?
- expected: `SELECT COUNT(T1.id) FROM sets AS T1 INNER JOIN set_translations AS T2 ON T2.setCode = T1.code WHERE T2.translation IS NOT NULL AND T1.baseSetSize < 100 AND T2.language = 'Italian'`
- agent: `SELECT COUNT(DISTINCT s.code) AS total_italian_sets, SUM(CASE WHEN s.baseSetSize < 10 THEN 1 ELSE 0 END) AS under_10, SUM(CASE WHEN s.baseSetSize < 100 THEN 1 ELSE 0 END) AS under_100 FROM sets s JOIN set_translations st ON st.setCode = s.code WHERE st.language = 'Italian' AND st.translation IS NOT NULL;`

### card_games_486

- question: What is the percentage of the cards with a converted mana cost of 7 in the set Coldsnap?
- expected: `SELECT CAST(SUM(CASE WHEN T1.convertedManaCost = 7 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id) FROM cards AS T1 INNER JOIN sets AS T2 ON T2.code = T1.setCode WHERE T2.name = 'Coldsnap'`
- agent: `SELECT SUM(convertedManaCost = 7) AS cards_cmc7, SUM(convertedManaCost) AS sum_cmc, COUNT(*) AS total_cards, SUM(convertedManaCost = 7) * 100.0 / SUM(convertedManaCost) AS pct_hint_formula, SUM(convertedManaCost = 7) * 100.0 / COUNT(*) AS pct_of_cards FROM cards WHERE setCode = 'CSP';`

### card_games_528

- question: List the names of all the cards in the set Hour of Devastation and find the formats in which these cards are legal.
- expected: `SELECT DISTINCT T2.name , CASE WHEN T1.status = 'Legal' THEN T1.format ELSE NULL END FROM legalities AS T1 INNER JOIN cards AS T2 ON T2.uuid = T1.uuid WHERE T2.setCode IN ( SELECT code FROM sets WHERE name = 'Hour of Devastation' )`
- agent: `SELECT DISTINCT c.name FROM cards c JOIN sets s ON c.setCode = s.code JOIN legalities l ON c.uuid = l.uuid WHERE s.name = 'Hour of Devastation' AND l.status = 'Legal' ORDER BY c.name;`

### card_games_529

- question: Find and list the names of sets which doesn't have Japanese translation but have Korean translation.
- expected: `SELECT name FROM sets WHERE code IN ( SELECT setCode FROM set_translations WHERE language = 'Korean' AND language NOT LIKE '%Japanese%' )`
- agent: `SELECT k.setCode FROM (SELECT DISTINCT setCode FROM set_translations WHERE language = 'Korean') k LEFT JOIN (SELECT DISTINCT setCode FROM set_translations WHERE language = 'Japanese') j ON k.setCode = j.setCode WHERE j.setCode IS NULL`

### card_games_530

- question: List all the frame styles and cards Allen Williams worked on and find any banned cards if there are any.
- expected: `SELECT DISTINCT T1.frameVersion, T1.name , IIF(T2.status = 'Banned', T1.name, 'NO') FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T1.artist = 'Allen Williams'`
- agent: `SELECT DISTINCT name FROM cards WHERE artist = 'Allen Williams' ORDER BY name`

### codebase_community_584

- question: Write all the comments left by users who edited the post titled 'Why square the difference instead of taking the absolute value in standard deviation?'
- expected: `SELECT T2.Comment FROM posts AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.PostId WHERE T1.Title = 'Why square the difference instead of taking the absolute value in standard deviation?'`
- agent: `SELECT Id, LENGTH(Text) AS len, substr(Text, 1, 200) AS part1 FROM comments WHERE Id = 135385`

### codebase_community_637

- question: State all the tags used by Mark Meckes in his posts that doesn't have comments.
- expected: `SELECT T3.Tags FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T3.Id = T2.PostId WHERE T1.DisplayName = 'Mark Meckes' AND T3.CommentCount = 0`
- agent: `SELECT DISTINCT Tags FROM posts WHERE OwnerUserId = (SELECT Id FROM users WHERE DisplayName = 'Mark Meckes') AND CommentCount = 0 AND Tags IS NOT NULL`

### codebase_community_682

- question: Which is the most valuable post in 2010? Please give its id and the owner's display name.
- expected: `SELECT T2.OwnerUserId, T1.DisplayName FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE STRFTIME('%Y', T1.CreationDate) = '2010' ORDER BY T2.FavoriteCount DESC LIMIT 1`
- agent: `SELECT p.Id, u.DisplayName, p.FavoriteCount FROM posts p LEFT JOIN users u ON p.OwnerUserId = u.Id WHERE CAST(strftime('%Y', p.CreaionDate) AS INTEGER) = 2010 ORDER BY p.FavoriteCount DESC LIMIT 1;`

### codebase_community_694

- question: Provide the text of the latest 10 comments to the post with the title 'Analysing wind data with R' and the display name of the user who left it.
- expected: `SELECT T3.Text, T1.DisplayName FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId INNER JOIN comments AS T3 ON T2.Id = T3.PostId WHERE T2.Title = 'Analysing wind data with R' ORDER BY T1.CreationDate DESC LIMIT 10`
- agent: `SELECT Id, substr(Text, 1, 150) AS Chunk1, substr(Text, 151, 150) AS Chunk2, substr(Text, 301, 150) AS Chunk3, substr(Text, 451, 150) AS Chunk4 FROM comments WHERE Id IN (11451, 11456, 11505) ORDER BY Id;`

### codebase_community_710

- question: In posts with 1 comment, how many of the comments have 0 score?
- expected: `SELECT COUNT(T1.id) FROM comments AS T1 INNER JOIN posts AS T2 ON T1.PostId = T2.Id WHERE T2.CommentCount = 1 AND T2.Score = 0`
- agent: `SELECT COUNT(*) AS zero_score_comment_count FROM comments c JOIN posts p ON p.Id = c.PostId WHERE p.CommentCount = 1 AND c.Score = 0;`

### codebase_community_716

- question: Among the comments with scores between 5 to 10, what is the percentage of the users with 0 up votes?
- expected: `SELECT CAST(SUM(IIF(T1.UpVotes = 0, 1, 0)) AS REAL) * 100/ COUNT(T1.Id) AS per FROM users AS T1 INNER JOIN comments AS T2 ON T1.Id = T2.UserId WHERE T2.Score BETWEEN 5 AND 10`
- agent: `SELECT COUNT(*) AS total_comments, SUM(CASE WHEN u.UpVotes = 0 THEN 1 ELSE 0 END) AS users_with_zero_upvotes, ROUND(SUM(CASE WHEN u.UpVotes = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS percentage FROM comments c JOIN users u ON u.Id = c.UserId WHERE c.Score BETWEEN 5 AND 10`

### debit_card_specializing_1476

- question: What was the difference in gas consumption between CZK-paying customers and EUR-paying customers in 2012?
- expected: `SELECT SUM(IIF(T1.Currency = 'CZK', T2.Consumption, 0)) - SUM(IIF(T1.Currency = 'EUR', T2.Consumption, 0)) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2012'`
- agent: `SELECT c.Currency, SUM(ym.Consumption) AS total FROM yearmonth ym JOIN customers c ON c.CustomerID = ym.CustomerID WHERE ym.Date BETWEEN '201201' AND '201212' GROUP BY c.Currency`

### debit_card_specializing_1493

- question: In February 2012, what percentage of customers consumed more than 528.3?
- expected: `SELECT CAST(SUM(IIF(Consumption > 528.3, 1, 0)) AS FLOAT) * 100 / COUNT(CustomerID) FROM yearmonth WHERE Date = '201202'`
- agent: `SELECT COUNT(*) AS total_customers, SUM(CASE WHEN Consumption > 528.3 THEN 1 ELSE 0 END) AS above_threshold, ROUND(100.0 * SUM(CASE WHEN Consumption > 528.3 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct FROM yearmonth WHERE Date LIKE '201202%'`

### debit_card_specializing_1501

- question: Please list the countries of the gas stations with transactions taken place in June, 2013.
- expected: `SELECT DISTINCT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN yearmonth AS T3 ON T1.CustomerID = T3.CustomerID WHERE T3.Date = '201306'`
- agent: `SELECT count(*) AS total_2013 FROM transactions_1k WHERE substr(Date, 1, 4) = '2013'`

### debit_card_specializing_1514

- question: What kind of currency did the customer paid at 16:25:00 in 2012/8/24?
- expected: `SELECT DISTINCT T3.Currency FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID INNER JOIN customers AS T3 ON T1.CustomerID = T3.CustomerID WHERE T1.Date = '2012-08-24' AND T1.Time = '16:25:00'`
- agent: `SELECT c.Currency FROM transactions_1k t JOIN customers c ON t.CustomerID = c.CustomerID WHERE t.Date = '2012-08-24' AND t.Time = '16:25:00'`

### debit_card_specializing_1525

- question: What is the percentage of the customers who used EUR in 2012/8/25?
- expected: `SELECT CAST(SUM(IIF(T2.Currency = 'EUR', 1, 0)) AS FLOAT) * 100 / COUNT(T1.CustomerID) FROM transactions_1k AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Date = '2012-08-25'`
- agent: `SELECT ROUND(100.0 * COUNT(DISTINCT CASE WHEN c.Currency = 'EUR' THEN t.CustomerID END) / COUNT(DISTINCT t.CustomerID), 2) AS pct_eur FROM transactions_1k t LEFT JOIN customers c ON c.CustomerID = t.CustomerID WHERE t.Date = '2012-08-25';`

### debit_card_specializing_1528

- question: What is the percentage of "premium" against the overall segment in Country = "SVK"?
- expected: `SELECT CAST(SUM(IIF(Country = 'SVK' AND Segment = 'Premium', 1, 0)) AS FLOAT) * 100 / SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations`
- agent: `SELECT ROUND(100.0 * SUM(CASE WHEN Segment = 'Premium' THEN 1 ELSE 0 END) / COUNT(*), 2) AS premium_pct FROM gasstations WHERE Country = 'SVK'`

### debit_card_specializing_1531

- question: Who is the top spending customer and how much is the average price per single item purchased by this customer? What currency was being used?
- expected: `SELECT T2.CustomerID, SUM(T2.Price / T2.Amount), T1.Currency FROM customers AS T1 INNER JOIN transactions_1k AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.CustomerID = ( SELECT CustomerID FROM yearmonth ORDER BY Consumption DESC LIMIT 1 ) GROUP BY T2.CustomerID, T1.Currency`
- agent: `WITH spending AS ( SELECT CustomerID, SUM(Price) AS total_spend, SUM(Amount) AS total_amount FROM transactions_1k WHERE CustomerID IS NOT NULL GROUP BY CustomerID ) SELECT c.CustomerID, c.Currency, s.total_spend, s.total_amount, s.total_spend / s.total_amount AS avg_price_per_item FROM spending s JOIN customers c ON c.CustomerID = s.CustomerID ORDER BY s.total_spend DESC LIMIT 1;`

### european_football_2_1025

- question: Give the name of the league had the most goals in the 2016 season?
- expected: `SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1`
- agent: `SELECT l.name, SUM(m.home_team_goal + m.away_team_goal) AS total_goals FROM Match m JOIN League l ON m.league_id = l.id WHERE m.season = '2015/2016' GROUP BY l.id, l.name ORDER BY total_goals DESC LIMIT 1;`

### european_football_2_1028

- question: In Scotland Premier League, which away team won the most during the 2010 season?
- expected: `SELECT teamInfo.team_long_name FROM League AS leagueData INNER JOIN Match AS matchData ON leagueData.id = matchData.league_id INNER JOIN Team AS teamInfo ON matchData.away_team_api_id = teamInfo.team_api_id WHERE leagueData.name = 'Scotland Premier League' AND matchData.season = '2009/2010' AND matchData.away_team_goal - matchData.home_team_goal > 0 GROUP BY matchData.away_team_api_id ORDER BY COUNT(*) DESC LIMIT 1`
- agent: `SELECT t.team_long_name, COUNT(*) AS away_wins FROM Match m JOIN League l ON m.league_id = l.id JOIN Team t ON m.away_team_api_id = t.team_api_id WHERE l.name = 'Scotland Premier League' AND m.season = '2009/2010' AND m.away_team_goal > m.home_team_goal GROUP BY m.away_team_api_id ORDER BY away_wins DESC LIMIT 1;`

### european_football_2_1031

- question: At present, calculate for the player's age who have a sprint speed of no less than 97 between 2013 to 2015.
- expected: `SELECT DISTINCT DATETIME() - T2.birthday age FROM Player_Attributes AS t1 INNER JOIN Player AS t2 ON t1.player_api_id = t2.player_api_id WHERE STRFTIME('%Y',t1.`date`) >= '2013' AND STRFTIME('%Y',t1.`date`) <= '2015' AND t1.sprint_speed >= 97`
- agent: `SELECT DISTINCT p.player_name, CAST(strftime('%Y', 'now') AS INTEGER) - CAST(strftime('%Y', p.birthday) AS INTEGER) - CASE WHEN strftime('%m-%d', 'now') < strftime('%m-%d', p.birthday) THEN 1 ELSE 0 END AS age_now FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id WHERE pa.sprint_speed >= 97 AND CAST(strftime('%Y', pa.date) AS INTEGER) BETWEEN 2013 AND 2015;`

### european_football_2_1058

- question: Who has the highest average finishing rate between the highest and shortest football player?
- expected: `SELECT A FROM ( SELECT AVG(finishing) result, 'Max' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = ( SELECT MAX(height) FROM Player ) UNION SELECT AVG(finishing) result, 'Min' A FROM Player AS T1 INNER JOIN Player_Attributes AS T2 ON T1.player_api_id = T2.player_api_id WHERE T1.height = ( SELECT MIN(height) FROM Player ) ) ORDER BY result DESC LIMIT 1`
- agent: `SELECT p.player_name, p.height, AVG(pa.finishing) AS avg_finishing FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id WHERE p.height = (SELECT MAX(height) FROM Player) OR p.height = (SELECT MIN(height) FROM Player) GROUP BY p.player_name, p.height`

### european_football_2_1068

- question: From 2010 to 2015, what was the average overall rating of players who are higher than 170?
- expected: `SELECT CAST(SUM(t2.overall_rating) AS REAL) / COUNT(t2.id) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id WHERE t1.height > 170 AND STRFTIME('%Y',t2.`date`) >= '2010' AND STRFTIME('%Y',t2.`date`) <= '2015'`
- agent: `SELECT AVG(t2.overall_rating) AS avg_overall_rating, COUNT(*) AS n FROM Player_Attributes t2 JOIN Player p ON p.player_api_id = t2.player_api_id WHERE strftime('%Y', t2.date) >= '2010' AND strftime('%Y', t2.date) <= '2015' AND p.height > 170;`

### european_football_2_1078

- question: Which player is older, Aaron Lennon or Abdelaziz Barrada?
- expected: `SELECT player_name FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada') ORDER BY birthday ASC LIMIT 1`
- agent: `SELECT player_name, birthday FROM Player WHERE player_name IN ('Aaron Lennon', 'Abdelaziz Barrada')`

### european_football_2_1094

- question: How much higher in percentage is Ariel Borysiuk's overall rating than that of Paulin Puel?
- expected: `SELECT (SUM(CASE WHEN t1.player_name = 'Ariel Borysiuk' THEN t2.overall_rating ELSE 0 END) * 1.0 - SUM(CASE WHEN t1.player_name = 'Paulin Puel' THEN t2.overall_rating ELSE 0 END)) * 100 / SUM(CASE WHEN t1.player_name = 'Paulin Puel' THEN t2.overall_rating ELSE 0 END) FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_api_id = t2.player_api_id`
- agent: `WITH latest AS ( SELECT p.player_name, pa.overall_rating, ROW_NUMBER() OVER (PARTITION BY p.player_name ORDER BY pa.date DESC) AS rn FROM Player p JOIN Player_Attributes pa ON pa.player_api_id = p.player_api_id WHERE p.player_name IN ('Ariel Borysiuk', 'Paulin Puel') ) SELECT ROUND( (MAX(CASE WHEN player_name = 'Ariel Borysiuk' THEN overall_rating END) - MAX(CASE WHEN player_name = 'Paulin Puel' THEN overall_rating END)) * 100.0 / MAX(CASE WHEN player_name = 'Paulin Puel' THEN overall_rating END), 2) AS pct_higher FROM latest WHERE rn = 1;`

### european_football_2_1107

- question: When was the first time did Kevin Constant have his highest crossing score? Give the date.
- expected: `SELECT `date` FROM ( SELECT t2.crossing, t2.`date` FROM Player AS t1 INNER JOIN Player_Attributes AS t2 ON t1.player_fifa_api_id = t2.player_fifa_api_id WHERE t1.player_name = 'Kevin Constant' ORDER BY t2.crossing DESC) ORDER BY date DESC LIMIT 1`
- agent: `SELECT MIN(date) AS first_date FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Kevin Constant') AND crossing = (SELECT MAX(crossing) FROM Player_Attributes WHERE player_api_id = (SELECT player_api_id FROM Player WHERE player_name = 'Kevin Constant'))`

### financial_118

- question: For loan amount less than USD100,000, what is the percentage of accounts that is still running with no issue.
- expected: `SELECT CAST(SUM(status = 'C') AS REAL) * 100 / COUNT(account_id) FROM loan WHERE amount < 100000`
- agent: `SELECT SUM(CASE WHEN status = 'C' THEN amount ELSE 0 END) * 100.0 / SUM(amount) AS percentage FROM loan WHERE amount < 100000;`

### financial_129

- question: Which are the top ten withdrawals (non-credit card) by district names for the month of January 1996?
- expected: `SELECT DISTINCT T1.A2 FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id INNER JOIN trans AS T3 ON T2.account_id = T3.account_id WHERE T3.type = 'VYDAJ' AND T3.date LIKE '1996-01%' ORDER BY A2 ASC LIMIT 10`
- agent: `SELECT d.A2 AS district_name, SUM(t.amount) AS total_withdrawals FROM trans t JOIN account a ON t.account_id = a.account_id JOIN district d ON a.district_id = d.district_id WHERE t.type = 'VYDAJ' AND t.date LIKE '1996-01%' GROUP BY d.A2 ORDER BY total_withdrawals DESC LIMIT 10;`

### financial_152

- question: What is the average number of crimes committed in 1995 in regions where the number exceeds 4000 and the region has accounts that are opened starting from the year 1997?
- expected: `SELECT AVG(T1.A15) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE STRFTIME('%Y', T2.date) >= '1997' AND T1.A15 > 4000`
- agent: `SELECT d.district_id, d.A2, d.A3, d.A15 FROM district d WHERE d.A15 > 4000 AND d.district_id IN (SELECT DISTINCT a.district_id FROM account a WHERE a.date >= '1997-01-01') ORDER BY d.A15 DESC`

### financial_192

- question: What is the average amount of loan which are still on running contract with statement issuance after each transaction?
- expected: `SELECT AVG(T2.amount) FROM account AS T1 INNER JOIN loan AS T2 ON T1.account_id = T2.account_id WHERE T2.status IN ('C', 'D') AND T1.frequency = 'POPLATEK PO OBRATU'`
- agent: `SELECT AVG(l.amount) AS avg_amount, COUNT(*) AS cnt FROM loan l JOIN account a ON a.account_id = l.account_id WHERE l.status IN ('C', 'D') AND a.frequency = 'POPLATEK PO OBRATU';`

### formula_1_861

- question: What is his number of the driver who finished 0:01:54 in the Q3 of qualifying race No.903?
- expected: `SELECT T2.number FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 903 AND T1.q3 LIKE '1:54%'`
- agent: `SELECT raceId, year, round, name, date FROM races WHERE raceId = 903;`

### formula_1_879

- question: For the driver who set the fastest lap speed, what is his nationality?
- expected: `SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId ORDER BY T2.fastestLapSpeed DESC LIMIT 1`
- agent: `SELECT d.nationality FROM results r JOIN drivers d ON d.driverId = r.driverId WHERE CAST(r.fastestLapSpeed AS REAL) = (SELECT MAX(CAST(fastestLapSpeed AS REAL)) FROM results WHERE fastestLapSpeed IS NOT NULL);`

### formula_1_880

- question: Paul di Resta was in the No. 853 race, what percent faster did he finish in the 853rd race than the next race for the fastest lap speed?
- expected: `SELECT (SUM(IIF(T2.raceId = 853, T2.fastestLapSpeed, 0)) - SUM(IIF(T2.raceId = 854, T2.fastestLapSpeed, 0))) * 100 / SUM(IIF(T2.raceId = 853, T2.fastestLapSpeed, 0)) FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T1.forename = 'Paul' AND T1.surname = 'di Resta'`
- agent: `SELECT ROUND((a.fastestLapSpeed - b.fastestLapSpeed) * 100.0 / a.fastestLapSpeed, 2) AS percent_faster FROM results a JOIN results b ON b.raceId = 854 AND a.driverId = b.driverId JOIN drivers d ON d.driverId = a.driverId WHERE a.raceId = 853 AND d.forename = 'Paul' AND d.surname = 'di Resta';`

### formula_1_896

- question: Calculate the percentage whereby Hamilton was not at the 1st track of the the f1 circuit since 2010.
- expected: `SELECT CAST(COUNT(CASE WHEN T2.position <> 1 THEN T2.position END) AS REAL) * 100 / COUNT(T2.driverStandingsId) FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.surname = 'Hamilton' AND T1.year >= 2010`
- agent: `SELECT COUNT(*) AS total_races, COUNT(CASE WHEN r.position > 1 THEN 1 END) AS not_first, COUNT(CASE WHEN r.position = 1 THEN 1 END) AS wins FROM results r JOIN drivers d ON r.driverId = d.driverId JOIN races ra ON r.raceId = ra.raceId WHERE d.surname = 'Hamilton' AND ra.year >= 2010;`

### formula_1_898

- question: How old is the youngest Japanese driver? What is his name?
- expected: `SELECT STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', dob), forename , surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1`
- agent: `SELECT forename, surname, dob FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1`

### formula_1_904

- question: State the race and year of race in which Michael Schumacher had his fastest lap.
- expected: `SELECT T1.name, T1.year FROM races AS T1 INNER JOIN lapTimes AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Michael' AND T3.surname = 'Schumacher' ORDER BY T2.milliseconds ASC LIMIT 1`
- agent: `SELECT r.name, r.year, r.round, c.name AS circuit FROM races r JOIN circuits c ON r.circuitId = c.circuitId WHERE r.raceId = 113;`

### formula_1_915

- question: Which country is the oldest driver from?
- expected: `SELECT nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1`
- agent: `SELECT forename, surname, dob, nationality FROM drivers WHERE dob IS NOT NULL ORDER BY dob ASC LIMIT 1;`

### formula_1_928

- question: Which driver ranked the first in the Canadian Grand Prix in 2007? Please give his reference name.
- expected: `SELECT T3.forename, T3.surname, T3.driverRef FROM races AS T1 INNER JOIN results AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T1.name = 'Canadian Grand Prix' AND T2.rank = 1 AND T1.year = 2007`
- agent: `SELECT d.driverRef FROM races r JOIN results res ON r.raceId = res.raceId JOIN drivers d ON res.driverId = d.driverId WHERE r.name = 'Canadian Grand Prix' AND r.year = 2007 AND res.positionOrder = 1`

### formula_1_944

- question: How much faster in percentage is the champion than the driver who finished the race last in the 2008 Australian Grand Prix?
- expected: `WITH time_in_seconds AS ( SELECT T1.positionOrder, CASE WHEN T1.positionOrder = 1 THEN (CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600) + (CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60) + CAST(SUBSTR(T1.time, 6) AS REAL) ELSE CAST(SUBSTR(T1.time, 2) AS REAL) END AS time_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 2008 ), champion_time AS ( SELECT time_seconds FROM time_in_seconds WHERE positionOrder = 1), last_driver_incremental AS ( SELECT time_seconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds) ) SELECT (CAST((SELECT time_seconds FROM last_driver_incremental) AS REAL) * 100) / (SELECT time_seconds + (SELECT time_seconds FROM last_driver_incremental) FROM champion_time)`
- agent: `SELECT * FROM races WHERE raceId = 18`

### formula_1_945

- question: How many circuits are there in Adelaide, Australia?
- expected: `SELECT COUNT(circuitId) FROM circuits WHERE location = 'Adelaide' AND country = 'Australia'`
- agent: `SELECT circuitId, name, location, country FROM circuits WHERE country = 'Australia' ORDER BY location`

### formula_1_950

- question: Please list the constructor names with 0 points at race 291.
- expected: `SELECT T2.name FROM constructorStandings AS T1 INNER JOIN constructors AS T2 on T1.constructorId = T2.constructorId WHERE T1.points = 0 AND T1.raceId = 291`
- agent: `SELECT c.name FROM constructors c JOIN constructorResults cr ON c.constructorId = cr.constructorId WHERE cr.raceId = 291 AND cr.points = 0;`

### formula_1_959

- question: What is the fastest lap number of the champion in 2009?
- expected: `SELECT T1.fastestLap FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId WHERE T2.year = 2009 AND T1.time LIKE '_:%:__.___'`
- agent: `SELECT r.round, r.name, res.fastestLap, res.fastestLapTime, res.rank, res.position, res.time, res.laps FROM results res JOIN races r ON r.raceId = res.raceId WHERE r.year = 2009 AND res.driverId = 18 ORDER BY r.round`

### formula_1_963

- question: How many French drivers who obtain the laptime less than 02:00.00?
- expected: `SELECT COUNT(T1.driverId) FROM drivers AS T1 INNER JOIN lapTimes AS T2 on T1.driverId = T2.driverId WHERE T1.nationality = 'French' AND (CAST(SUBSTR(T2.time, 1, 2) AS INTEGER) * 60 + CAST(SUBSTR(T2.time, 4, 2) AS INTEGER) + CAST(SUBSTR(T2.time, 7, 2) AS REAL) / 1000) < 120`
- agent: `SELECT COUNT(DISTINCT d.driverId) AS french_drivers_fast_laps FROM lapTimes lt JOIN drivers d ON lt.driverId = d.driverId WHERE d.nationality = 'French' AND lt.milliseconds < 120000;`

### formula_1_964

- question: List out the code for drivers who have nationality in American.
- expected: `SELECT code FROM drivers WHERE Nationality = 'American'`
- agent: `SELECT DISTINCT code FROM drivers WHERE nationality = 'American' AND code IS NOT NULL ORDER BY code;`

### formula_1_967

- question: State code numbers of top 3 yougest drivers. How many Netherlandic drivers among them?
- expected: `SELECT COUNT(*) FROM ( SELECT T1.nationality FROM drivers AS T1 ORDER BY JULIANDAY(T1.dob) DESC LIMIT 3) AS T3 WHERE T3.nationality = 'Dutch'`
- agent: `SELECT code, forename, surname, nationality, dob FROM drivers ORDER BY dob DESC LIMIT 3;`

### formula_1_978

- question: How many times the circuits were held in Austria? Please give their location and coordinates.
- expected: `SELECT DISTINCT location, lat, lng FROM circuits WHERE country = 'Austria'`
- agent: `SELECT COUNT(*) AS total_races_in_austria FROM races r JOIN circuits c ON r.circuitId = c.circuitId WHERE c.country = 'Austria';`

### formula_1_989

- question: Who is the champion of the Canadian Grand Prix in 2008? Indicate his finish time.
- expected: `SELECT T1.time FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T2.name = 'Canadian Grand Prix' AND T2.year = 2008 AND T1.time LIKE '_:%:__.___'`
- agent: `SELECT d.forename, d.surname, res.position, res.positionText, res.time, res.milliseconds, res.statusId, s.status FROM results res JOIN drivers d ON res.driverId = d.driverId JOIN status s ON res.statusId = s.statusId WHERE res.raceId = 24 AND res.positionOrder = 1;`

### formula_1_994

- question: Which constructor scored most points from Monaco Grand Prix between 1980 and 2010? List the score, name and nationality of this team.
- expected: `SELECT SUM(T1.points), T2.name, T2.nationality FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId INNER JOIN races AS T3 ON T3.raceid = T1.raceid WHERE T3.name = 'Monaco Grand Prix' AND T3.year BETWEEN 1980 AND 2010 GROUP BY T2.name ORDER BY SUM(T1.points) DESC LIMIT 1`
- agent: `SELECT DISTINCT ra.year, ra.name FROM races ra WHERE ra.year BETWEEN 1980 AND 2010 AND ra.name LIKE '%Monaco%' ORDER BY ra.year;`

### student_club_1334

- question: List the full name of the Student_Club members that grew up in Illinois state.
- expected: `SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN zip_code AS T2 ON T1.zip = T2.zip_code WHERE T2.state = 'Illinois'`
- agent: `SELECT m.first_name || ' ' || m.last_name AS full_name FROM member m JOIN zip_code z ON m.zip = z.zip_code WHERE z.state = 'Illinois' ORDER BY full_name;`

### student_club_1338

- question: Was each expense in October Meeting on October 8, 2019 approved?
- expected: `SELECT T3.approved FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting' AND T1.event_date LIKE '2019-10-08%'`
- agent: `SELECT exp.expense_id, exp.expense_description, exp.expense_date, exp.cost, exp.approved FROM expense exp JOIN budget b ON exp.link_to_budget = b.budget_id JOIN event ev ON b.link_to_event = ev.event_id WHERE ev.event_name = 'October Meeting' AND substr(ev.event_date, 1, 10) = '2019-10-08'`

### student_club_1340

- question: Calculate the difference of the total amount spent in all events by the Student_Club in year 2019 and 2020.
- expected: `SELECT SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2019' THEN T2.spent ELSE 0 END) - SUM(CASE WHEN SUBSTR(T1.event_date, 1, 4) = '2020' THEN T2.spent ELSE 0 END) AS num FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event`
- agent: `SELECT substr(e.event_date, 1, 4) AS yr, COUNT(*) AS budget_rows, SUM(b.spent) AS total_spent FROM budget b JOIN event e ON b.link_to_event = e.event_id WHERE substr(e.event_date, 1, 4) IN ('2019', '2020') GROUP BY yr`

### student_club_1381

- question: List the name of students that have attended more than 7 events.
- expected: `SELECT T1.first_name, T1.last_name FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member GROUP BY T2.link_to_member HAVING COUNT(T2.link_to_event) > 7`
- agent: `SELECT m.first_name || ' ' || m.last_name AS full_name FROM attendance a JOIN member m ON a.link_to_member = m.member_id GROUP BY m.member_id HAVING COUNT(a.link_to_event) > 7;`

### student_club_1387

- question: Which student has been entrusted to manage the budget for the Yearly Kickoff?
- expected: `SELECT T4.first_name, T4.last_name FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget INNER JOIN member AS T4 ON T3.link_to_member = T4.member_id WHERE T1.event_name = 'Yearly Kickoff'`
- agent: `SELECT first_name || ' ' || last_name AS full_name FROM member WHERE position = 'Treasurer'`

### student_club_1392

- question: Indicate the top source of funds received in September 2019 based on their amount.
- expected: `SELECT source FROM income WHERE date_received BETWEEN '2019-09-01' and '2019-09-30' ORDER BY source DESC LIMIT 1`
- agent: `SELECT source, MAX(amount) AS max_single_amount FROM income WHERE date_received BETWEEN '2019-09-01' AND '2019-09-30' GROUP BY source ORDER BY max_single_amount DESC`

### student_club_1404

- question: Identify the type of expenses and their total value approved for 'October Meeting' event.
- expected: `SELECT T1.type, SUM(T3.cost) FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event INNER JOIN expense AS T3 ON T2.budget_id = T3.link_to_budget WHERE T1.event_name = 'October Meeting'`
- agent: `SELECT e.expense_id, e.expense_description, e.cost, e.approved, b.category, b.budget_id FROM expense e JOIN budget b ON e.link_to_budget = b.budget_id JOIN event ev ON b.link_to_event = ev.event_id WHERE ev.event_name = 'October Meeting' ORDER BY b.category`

### student_club_1410

- question: List out the full name and total cost that member id "rec4BLdZHS2Blfp4v" incurred?
- expected: `SELECT T1.first_name, T1.last_name, SUM(T2.cost) FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.member_id = 'rec4BLdZHS2Blfp4v'`
- agent: `SELECT m.first_name || ' ' || m.last_name AS full_name, COALESCE(SUM(e.cost), 0) AS total_cost FROM member m LEFT JOIN expense e ON e.link_to_member = m.member_id WHERE m.member_id = 'rec4BLdZHS2Blfp4v' GROUP BY m.member_id;`

### student_club_1411

- question: State what kind of expenses that Sacha Harrison incurred?
- expected: `SELECT T2.expense_description FROM member AS T1 INNER JOIN expense AS T2 ON T1.member_id = T2.link_to_member WHERE T1.first_name = 'Sacha' AND T1.last_name = 'Harrison'`
- agent: `SELECT DISTINCT e.expense_description FROM expense e JOIN member m ON e.link_to_member = m.member_id WHERE m.first_name = 'Sacha' AND m.last_name = 'Harrison';`

### student_club_1427

- question: What are the budget category of the events located at MU 215 and a guest speaker type with a 0 budget spent?
- expected: `SELECT DISTINCT T2.category, T1.type FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'`
- agent: `SELECT DISTINCT b.category FROM budget b JOIN event e ON b.link_to_event = e.event_id WHERE e.location = 'MU 215' AND e.type = 'Guest Speaker' AND b.spent = 0;`

### student_club_1432

- question: Among the members with t-shirt size of medium, what is the percentage of the amount 50 received by the Student_Club?
- expected: `SELECT CAST(SUM(CASE WHEN T2.amount = 50 THEN 1.0 ELSE 0 END) AS REAL) * 100 / COUNT(T2.income_id) FROM member AS T1 INNER JOIN income AS T2 ON T1.member_id = T2.link_to_member WHERE T1.position = 'Member' AND T1.t_shirt_size = 'Medium'`
- agent: `SELECT m.member_id, m.first_name, m.last_name, m.t_shirt_size, m.position, GROUP_CONCAT(i.amount) AS income_amounts FROM member m LEFT JOIN income i ON i.link_to_member = m.member_id WHERE m.t_shirt_size = 'Medium' AND m.position = 'Member' GROUP BY m.member_id`

### superhero_726

- question: Rank heroes published by Marvel Comics by their height in descending order.
- expected: `SELECT superhero_name, height_cm, RANK() OVER (ORDER BY height_cm DESC) AS HeightRank FROM superhero INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics'`
- agent: `SELECT s.superhero_name, s.height_cm FROM superhero s JOIN publisher p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' AND s.height_cm IS NOT NULL ORDER BY s.height_cm DESC LIMIT 166 OFFSET 200`

### superhero_788

- question: How many percent of female heroes were published by Marvel Comics?
- expected: `SELECT CAST(COUNT(CASE WHEN T3.gender = 'Female' AND T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) AS REAL) / COUNT(CASE WHEN T2.publisher_name = 'Marvel Comics' THEN 1 ELSE NULL END) * 100 FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id INNER JOIN gender AS T3 ON T1.gender_id = T3.id`
- agent: `SELECT ROUND(100.0 * SUM(CASE WHEN g.gender = 'Female' AND p.publisher_name = 'Marvel Comics' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN g.gender = 'Female' THEN 1 ELSE 0 END), 0), 2) AS pct_female_marvel FROM superhero s JOIN gender g ON s.gender_id = g.id LEFT JOIN publisher p ON s.publisher_id = p.id;`

### superhero_790

- question: Calculate the difference between Emil Blonsky's weight and Charles Chandler's weight.
- expected: `SELECT ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Emil Blonsky' ) - ( SELECT weight_kg FROM superhero WHERE full_name LIKE 'Charles Chandler' ) AS CALCULATE`
- agent: `SELECT full_name, weight_kg FROM superhero WHERE full_name IN ('Emil Blonsky', 'Charles Chandler')`

### superhero_798

- question: What is the publisher for Hawkman, Karate Kid and Speedy?
- expected: `SELECT T2.publisher_name FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id WHERE T1.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy')`
- agent: `SELECT s.superhero_name, p.publisher_name FROM superhero s JOIN publisher p ON s.publisher_id = p.id WHERE s.superhero_name IN ('Hawkman', 'Karate Kid', 'Speedy');`

### thrombosis_prediction_1149

- question: Are there more in-patient or outpatient who were male? What is the deviation in percentage?
- expected: `SELECT CAST(SUM(CASE WHEN Admission = '+' THEN 1 ELSE 0 END) AS REAL) * 100 / SUM(CASE WHEN Admission = '-' THEN 1 ELSE 0 END) FROM Patient WHERE SEX = 'M'`
- agent: `SELECT SUM(CASE WHEN SEX = 'M' AND Admission = '+' THEN 1 ELSE 0 END) AS male_inpatient, SUM(CASE WHEN SEX = 'M' AND Admission = '-' THEN 1 ELSE 0 END) AS male_outpatient, ROUND(100.0 * SUM(CASE WHEN SEX = 'M' AND Admission = '+' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN SEX = 'M' AND Admission = '-' THEN 1 ELSE 0 END), 0), 2) AS inpatient_pct_of_outpatient FROM Patient;`

### thrombosis_prediction_1169

- question: What is the ratio of male to female patients among all those with abnormal uric acid counts?
- expected: `SELECT CAST(SUM(CASE WHEN T2.UA <= 8.0 AND T1.SEX = 'M' THEN 1 ELSE 0 END) AS REAL) / SUM(CASE WHEN T2.UA <= 6.5 AND T1.SEX = 'F' THEN 1 ELSE 0 END) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID`
- agent: `SELECT SUM(CASE WHEN p.SEX='M' AND l.UA <= 8.0 THEN 1 ELSE 0 END) AS male_cnt, SUM(CASE WHEN p.SEX='F' AND l.UA <= 6.5 THEN 1 ELSE 0 END) AS female_cnt, ROUND(1.0 * SUM(CASE WHEN p.SEX='M' AND l.UA <= 8.0 THEN 1 ELSE 0 END) / SUM(CASE WHEN p.SEX='F' AND l.UA <= 6.5 THEN 1 ELSE 0 END), 4) AS ratio FROM Laboratory l JOIN Patient p ON p.ID = l.ID;`

### thrombosis_prediction_1175

- question: How old was the patient who had the highest hemoglobin count at the time of the examination, and what is the doctor's diagnosis?
- expected: `SELECT STRFTIME('%Y', T2.Date) - STRFTIME('%Y', T1.Birthday), T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID ORDER BY T2.HGB DESC LIMIT 1`
- agent: `SELECT * FROM Examination ORDER BY ID LIMIT 10;`

### thrombosis_prediction_1179

- question: For the patient who was diagnosed with SLE on 1994/2/19, what was his/her anti-Cardiolipin antibody concentration status on 1993/11/12?
- expected: `SELECT `aCL IgA`, `aCL IgG`, `aCL IgM` FROM Examination WHERE ID IN ( SELECT ID FROM Patient WHERE Diagnosis = 'SLE' AND Description = '1994-02-19' ) AND `Examination Date` = '1993-11-12'`
- agent: `SELECT e.ID, e."Examination Date", e."aCL IgM", e.Diagnosis FROM Examination e WHERE e."Examination Date" IN ('1993-11-12', '1993/11/12');`

### thrombosis_prediction_1187

- question: How many patients who were examined between 1987/7/6 and 1996/1/31 had a GPT level greater than 30 and an ALB level less than 4? List them by their ID.
- expected: `SELECT DISTINCT ID FROM Laboratory WHERE Date BETWEEN '1987-07-06' AND '1996-01-31' AND GPT > 30 AND ALB < 4`
- agent: `SELECT e.ID, e."Examination Date", l.Date AS LabDate, l.GPT, l.ALB FROM Examination e JOIN Laboratory l ON e.ID = l.ID WHERE e."Examination Date" BETWEEN '1987-07-06' AND '1996-01-31' AND l.GPT > 30 AND l.ALB < 4 ORDER BY e.ID`

### thrombosis_prediction_1205

- question: Was the patient with the number 57266's uric acid within a normal range?
- expected: `SELECT CASE WHEN (T1.SEX = 'F' AND T2.UA > 6.5) OR (T1.SEX = 'M' AND T2.UA > 8.0) THEN true ELSE false END FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID = 57266`
- agent: `SELECT p.SEX, COUNT(l.UA) AS n_measurements, MIN(l.UA) AS min_UA, MAX(l.UA) AS max_UA, SUM(CASE WHEN p.SEX = 'M' AND l.UA > 8.0 THEN 1 ELSE 0 END) AS n_within_normal_M FROM Patient p LEFT JOIN Laboratory l ON p.ID = l.ID WHERE p.ID = 57266 AND l.UA IS NOT NULL GROUP BY p.SEX`

### thrombosis_prediction_1225

- question: List and group all patients by sex for total bilirubin (T-BIL) level not within the normal range.
- expected: `SELECT T1.ID,T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.`T-BIL` >= 2.0 GROUP BY T1.SEX,T1.ID`
- agent: `SELECT p.SEX, GROUP_CONCAT(DISTINCT l.ID) AS PatientIDs FROM Laboratory l JOIN Patient p ON p.ID = l.ID WHERE l."T-BIL" >= 2.0 GROUP BY p.SEX;`

### thrombosis_prediction_1238

- question: Among the patients who were diagnosed with SLE, who is the oldest with normal hemoglobin level. Provide the ID and sex.
- expected: `SELECT T1.ID, T1.SEX FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.Diagnosis = 'SLE' AND T2.HGB > 10 AND T2.HGB < 17 ORDER BY T1.Birthday ASC LIMIT 1`
- agent: `SELECT p.ID, p.SEX, p.Birthday, COUNT(l.HGB) AS normal_hgb_count FROM Patient p JOIN Laboratory l ON l.ID = p.ID WHERE p.Diagnosis = 'SLE' AND l.HGB > 10 AND l.HGB < 17 GROUP BY p.ID ORDER BY p.Birthday ASC LIMIT 3`

### thrombosis_prediction_1239

- question: Name the ID and age of patient with two or more laboratory examinations which show their hematoclit level exceeded the normal range.
- expected: `SELECT DISTINCT T1.ID, STRFTIME('%Y', CURRENT_TIMESTAMP) - STRFTIME('%Y', T1.Birthday) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T1.ID IN ( SELECT ID FROM Laboratory WHERE HCT >= 52 GROUP BY ID HAVING COUNT(ID) >= 2 )`
- agent: `SELECT L.ID, (CAST(strftime('%Y', 'now') AS INTEGER) - CAST(strftime('%Y', P.Birthday) AS INTEGER)) AS age FROM Laboratory L JOIN Patient P ON P.ID = L.ID WHERE L.HCT >= 52 GROUP BY L.ID HAVING COUNT(L.ID) > 2 ORDER BY L.ID;`

### thrombosis_prediction_1247

- question: Among the male patients who have a normal level of white blood cells, how many of them have an abnormal fibrinogen level?
- expected: `SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.FG <= 150 OR T2.FG >= 450 AND T2.WBC > 3.5 AND T2.WBC < 9.0 AND T1.SEX = 'M'`
- agent: `SELECT COUNT(DISTINCT p.ID) AS cnt FROM Patient p JOIN Laboratory l ON p.ID = l.ID WHERE p.SEX = 'M' AND l.WBC > 3.5 AND l.WBC < 9.0 AND (l.FG <= 150 OR l.FG >= 450)`

### thrombosis_prediction_1255

- question: For the patients with an abnormal Ig M level, what is the most common disease they are diagnosed with?
- expected: `SELECT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.IGM NOT BETWEEN 40 AND 400 GROUP BY T1.Diagnosis ORDER BY COUNT(T1.Diagnosis) DESC LIMIT 1`
- agent: `SELECT p.Diagnosis, COUNT(p.Diagnosis) AS cnt FROM Laboratory l JOIN Patient p ON l.ID = p.ID WHERE (l.IGM <= 40 OR l.IGM >= 400) AND p.Diagnosis IS NOT NULL GROUP BY p.Diagnosis ORDER BY cnt DESC LIMIT 1`

### thrombosis_prediction_1267

- question: Among the patients with normal anti-SM, how many of them does not have thrombosis?
- expected: `SELECT COUNT(T1.ID) FROM Examination AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.SM IN ('negative','0') AND T1.Thrombosis = 0`
- agent: `SELECT L.ID, L.SM, E.Thrombosis FROM Laboratory L JOIN Examination E ON L.ID = E.ID WHERE L.SM IN ('negative', '0') AND E.Thrombosis = 0 ORDER BY L.ID`

### thrombosis_prediction_1275

- question: Among the patients who has a normal level of anti-centromere and a normal level of anti-SSB, how many of them are male?
- expected: `SELECT COUNT(DISTINCT T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.CENTROMEA IN ('negative', '0') AND T2.SSB IN ('negative', '0') AND T1.SEX = 'M'`
- agent: `SELECT 'RNP' AS col, value, COUNT(*) AS cnt FROM (SELECT RNP AS value FROM Laboratory) GROUP BY value UNION ALL SELECT 'SM', value, COUNT(*) FROM (SELECT SM AS value FROM Laboratory) GROUP BY value UNION ALL SELECT 'SC170', value, COUNT(*) FROM (SELECT SC170 AS value FROM Laboratory) GROUP BY value UNION ALL SELECT 'SSA', value, COUNT(*) FROM (SELECT SSA AS value FROM Laboratory) GROUP BY value UNION ALL SELECT 'DNA', value, COUNT(*) FROM (SELECT DNA AS value FROM Laboratory) GROUP BY value`

### thrombosis_prediction_1302

- question: For the patients with a normal range of creatinine phosphokinase, how many of them have a positive measure of degree of coagulation?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T1.ID = T3.ID WHERE T2.CPK < 250 AND (T3.KCT = '+' OR T3.RVVT = '+' OR T3.LAC = '+')`
- agent: `SELECT DISTINCT e.ID, e.KCT, e.RVVT, e.LAC, l.CPK FROM Examination e JOIN Laboratory l ON l.ID = e.ID WHERE (e.KCT = '+' OR e.RVVT = '+' OR e.LAC = '+') AND l.CPK < 250`

### toxicology_197

- question: Calculate the average number of oxygen atoms in single-bonded molecules.
- expected: `SELECT AVG(oxygen_count) FROM (SELECT T1.molecule_id, COUNT(T1.element) AS oxygen_count FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '-' AND T1.element = 'o' GROUP BY T1.molecule_id) AS oxygen_counts`
- agent: `WITH single_bonded AS ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '-' ) SELECT (SELECT COUNT(*) FROM single_bonded) AS n_molecules, (SELECT COUNT(*) FROM atom a WHERE a.molecule_id IN (SELECT molecule_id FROM single_bonded) AND a.element = 'o') AS n_oxygen, (SELECT COUNT(*) FROM atom a WHERE a.molecule_id IN (SELECT molecule_id FROM single_bonded)) AS n_atoms`

### toxicology_198

- question: On average how many carcinogenic molecules are single bonded?
- expected: `SELECT AVG(single_bond_count) FROM (SELECT T3.molecule_id, COUNT(T1.bond_type) AS single_bond_count FROM bond AS T1 INNER JOIN atom AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN molecule AS T3 ON T3.molecule_id = T2.molecule_id WHERE T1.bond_type = '-' AND T3.label = '+' GROUP BY T3.molecule_id) AS subquery`
- agent: `SELECT (SELECT COUNT(*) FROM bond b JOIN molecule m ON b.molecule_id = m.molecule_id WHERE m.label = '+' AND b.bond_type = '-') * 1.0 / (SELECT COUNT(*) FROM atom a JOIN molecule m ON a.molecule_id = m.molecule_id WHERE m.label = '+') AS avg_single_bonds_per_atom;`

### toxicology_201

- question: What is the percentage of carbon in double-bond molecules?
- expected: `SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T1.atom_id) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='`
- agent: `WITH db_mols AS ( SELECT DISTINCT molecule_id FROM bond WHERE bond_type = '=' ) SELECT SUM(CASE WHEN a.element = 'c' THEN 1 ELSE 0 END) AS carbon_atoms, COUNT(a.atom_id) AS total_atoms, SUM(CASE WHEN a.element = 'c' THEN 1 ELSE 0 END) * 100.0 / COUNT(a.atom_id) AS pct_carbon FROM atom a JOIN db_mols d ON a.molecule_id = d.molecule_id;`

### toxicology_207

- question: What elements are in a double type bond?
- expected: `SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN connected AS T3 ON T1.atom_id = T3.atom_id WHERE T2.bond_type = '='`
- agent: `SELECT DISTINCT a.element FROM bond b JOIN connected c ON b.bond_id = c.bond_id JOIN atom a ON a.atom_id = c.atom_id WHERE b.bond_type = '=';`

### toxicology_215

- question: How many atoms with iodine and with sulfur type elements are there in single bond molecules?
- expected: `SELECT COUNT(DISTINCT CASE WHEN T1.element = 'i' THEN T1.atom_id ELSE NULL END) AS iodine_nums , COUNT(DISTINCT CASE WHEN T1.element = 's' THEN T1.atom_id ELSE NULL END) AS sulfur_nums FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id INNER JOIN bond AS T3 ON T2.bond_id = T3.bond_id WHERE T3.bond_type = '-'`
- agent: `SELECT COUNT(DISTINCT a.atom_id) AS answer FROM atom a WHERE a.element IN ('i','s') AND a.molecule_id IN (SELECT DISTINCT b.molecule_id FROM bond b WHERE b.bond_type = '-')`

### toxicology_218

- question: What percentage of carcinogenic-type molecules does not contain fluorine?
- expected: `SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element <> 'f' THEN T2.molecule_id ELSE NULL END) AS REAL) * 100 / COUNT(DISTINCT T2.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '+'`
- agent: `WITH carcinogenic AS ( SELECT molecule_id FROM molecule WHERE label = '+' ), with_f AS ( SELECT DISTINCT a.molecule_id FROM atom a JOIN carcinogenic c ON a.molecule_id = c.molecule_id WHERE LOWER(a.element) = 'f' ) SELECT COUNT(DISTINCT c.molecule_id) AS total_carcinogenic, COUNT(DISTINCT w.molecule_id) AS with_fluorine, ROUND(100.0 * (COUNT(DISTINCT c.molecule_id) - COUNT(DISTINCT w.molecule_id)) / COUNT(DISTINCT c.molecule_id), 2) AS pct_no_fluorine FROM carcinogenic c LEFT JOIN with_f w ON c.molecule_id = w.molecule_id`

### toxicology_234

- question: How many bonds which involved atom 12 does molecule TR009 have?
- expected: `SELECT COUNT(T2.bond_id) FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T1.molecule_id = 'TR009' AND T2.atom_id = T1.molecule_id || '_1' OR T2.atom_id2 = T1.molecule_id || '_2'`
- agent: `SELECT COUNT(*) AS bond_count FROM connected WHERE atom_id = 'TR009_12' OR atom_id2 = 'TR009_12'`

### toxicology_236

- question: What are the bond type and the atoms of the bond ID of TR001_6_9?
- expected: `SELECT T1.bond_type, T2.atom_id, T2.atom_id2 FROM bond AS T1 INNER JOIN connected AS T2 ON T1.bond_id = T2.bond_id WHERE T2.bond_id = 'TR001_6_9'`
- agent: `SELECT b.bond_id, b.bond_type, c.atom_id, c.atom_id2 FROM bond b LEFT JOIN connected c ON b.bond_id = c.bond_id WHERE b.bond_id = 'TR001_6_9';`

### toxicology_247

- question: List all the elements of atoms that can not bond with any other atoms.
- expected: `SELECT DISTINCT T.element FROM atom AS T WHERE T.element NOT IN ( SELECT DISTINCT T1.element FROM atom AS T1 INNER JOIN connected AS T2 ON T1.atom_id = T2.atom_id )`
- agent: `SELECT DISTINCT a.element FROM atom a WHERE a.atom_id NOT IN (SELECT atom_id FROM connected) AND a.atom_id NOT IN (SELECT atom_id2 FROM connected);`

### toxicology_260

- question: Calculate the total atoms with triple-bond molecules containing the element phosphorus or bromine.
- expected: `SELECT COUNT(T1.atom_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '#' AND T1.element IN ('p', 'br')`
- agent: `SELECT a.molecule_id, a.element, COUNT(*) OVER (PARTITION BY a.molecule_id) AS atoms_in_molecule FROM atom a WHERE a.molecule_id IN (SELECT molecule_id FROM bond WHERE bond_type = '#') AND a.molecule_id IN (SELECT molecule_id FROM atom WHERE element IN ('p', 'br')) ORDER BY a.molecule_id;`

