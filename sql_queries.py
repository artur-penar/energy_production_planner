GET_LATEST_ENERGY_PRODUCTION_DATE = """ 
SELECT MAX(date) AS last_real_date
FROM produced_energy 
WHERE type = :type_value
"""

GET_LATEST_WEATHER_DATE = """
SELECT MAX(date) AS last_real_date
FROM weather
WHERE type = :type_value
"""

IS_WEATHER_DAY_COMPLETE = """
SELECT COUNT(*) AS hour_count
FROM weather
WHERE date = :date AND type = :type_value
"""

GET_PRODUCED_ENERGY_TRAINING_DATA = """
SELECT
    p.date,
    p.hour,
    w.temp,
    w.cloud,
    w.gti,
    p.produced_energy
FROM produced_energy p
JOIN weather w
  ON p.date = w.date AND p.hour = w.hour AND w.type = 'real' AND p.type = 'real'
WHERE p.produced_energy IS NOT NULL
AND p.object_id = 1 
"""
GET_SOLD_ENERGY_TRAINING_DATA = """
SELECT
    s.date,
    s.hour,
    p.produced_energy,
    s.sold_energy
FROM sold_energy s
JOIN produced_energy p
  ON s.date = p.date AND s.hour = p.hour AND p.type = 'real' and s.type = 'real'
WHERE s.sold_energy IS NOT NULL
AND s.object_id = 1
"""

GET_PRODUCED_ENERGY_PREDICTION_DATA = """ 
SELECT
    p.date,
    p.hour,
    w.temp,
    w.cloud,
    w.gti,
    p.produced_energy,
    p.type,
    p.object_id
FROM produced_energy p
JOIN weather w
  ON p.date = w.date AND p.hour = w.hour AND w.type = 'predicted'
WHERE p.produced_energy IS NULL
"""

GET_SOLD_ENERGY_PREDICTION_DATA = """
SELECT
    s.date,
    s.hour,
    p.produced_energy,
    s.sold_energy,
    s.type,
    s.object_id
FROM sold_energy s
JOIN produced_energy p
  ON s.date = p.date AND s.hour = p.hour AND s.type = 'predicted' AND p.type = 'predicted'
WHERE s.sold_energy IS NULL
"""

GET_PRODUCED_ENERGY_FOR_DATE = """
SELECT
    p.date,
    p.hour,
    p.produced_energy
FROM produced_energy p
WHERE p.produced_energy IS NOT NULL
  AND p.date = :date
  AND p.type = :data_type
  AND p.object_id = :object_id
ORDER BY p.hour
"""

GET_SOLD_ENERGY_FOR_DATE = """
SELECT
    s.date,
    s.hour,
    s.sold_energy
FROM sold_energy s
WHERE s.sold_energy IS NOT NULL
  AND s.date = :date
  AND s.type = :data_type
  AND s.object_id = :object_id
ORDER BY s.hour
"""

INSERT_OR_UPDATE_WEATHER = """
INSERT INTO weather (date, hour, temp, cloud, gti, type)
VALUES (:date, :hour, :temp, :cloud, :gti, :type)
ON CONFLICT (date, hour, type)
DO UPDATE SET
    temp = EXCLUDED.temp,
    cloud = EXCLUDED.cloud,
    gti = EXCLUDED.gti
"""

UPDATE_PRODUCED_ENERGY = """
UPDATE produced_energy
SET produced_energy = :produced_energy
WHERE date = :date AND hour = :hour AND type = :type AND object_id = :object_id
"""

UPDATE_SOLD_ENERGY = """
UPDATE sold_energy
SET sold_energy = :sold_energy
WHERE date = :date AND hour = :hour AND type = :type AND object_id = :object_id
"""

DELETE_PRODUCED_ENERGY_PREDICTION = """
DELETE FROM produced_energy WHERE type = 'predicted' AND date >= :from_date
"""

DELETE_SOLD_ENERGY_PREDICTION = """
DELETE FROM sold_energy WHERE type = 'predicted' AND date >= :from_date
"""

SELECT_DISTINCT_PREDICTED_WEATHER = """
SELECT DISTINCT date, hour
FROM weather
WHERE type = 'predicted'
"""