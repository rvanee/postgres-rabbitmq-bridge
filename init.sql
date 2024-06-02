CREATE TABLE IF NOT EXISTS patient
(
    _patientid BIGINT PRIMARY KEY,
    name VARCHAR(255),
    dob DATE,
    sex VARCHAR(2)
);