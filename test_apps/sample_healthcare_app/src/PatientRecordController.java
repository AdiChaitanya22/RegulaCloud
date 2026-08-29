package com.regulacloud.health.controllers;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;

public class PatientRecordController {

    private Connection dbConnection;

    public String getPatientById(String patientAadhaarOrId) throws Exception {
        // SECURITY FLAW: CWE-89 (SQL Injection)
        // SonarQube Rule: javasecurity:S3649
        Statement stmt = dbConnection.createStatement();
        String query = "SELECT patient_id, full_name, medical_history FROM patients WHERE id = '" + patientAadhaarOrId + "'";
        ResultSet rs = stmt.executeQuery(query);
        
        if (rs.next()) {
            return rs.getString("full_name") + ": " + rs.getString("medical_history");
        }
        return "Patient Not Found";
    }
}
