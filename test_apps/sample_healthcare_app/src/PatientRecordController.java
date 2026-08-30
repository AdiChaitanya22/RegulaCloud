package com.regulacloud.health.controllers;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

public class PatientRecordController {

    private Connection dbConnection;

    public String getPatientById(String patientAadhaarOrId) throws Exception {
        // SECURE: Parameterized query eliminates SQL Injection (CWE-89 / S3649)
        String query = "SELECT patient_id, full_name, medical_history FROM patients WHERE id = ?";
        PreparedStatement ps = dbConnection.prepareStatement(query);
        ps.setString(1, patientAadhaarOrId);
        ResultSet rs = ps.executeQuery();
        
        if (rs.next()) {
            return rs.getString("full_name") + ": " + rs.getString("medical_history");
        }
        return "Patient Not Found";
    }
}
