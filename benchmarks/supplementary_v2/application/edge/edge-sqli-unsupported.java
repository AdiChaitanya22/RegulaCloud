package com.regulacloud.benchmark;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

class EdgeSqliUnsupported {
    public void getUserComplex(Connection conn, String id, String dept) throws SQLException {
        Statement stmt = conn.createStatement();
        String query = "SELECT * FROM users WHERE status = 'active' AND id = " + id + " AND dept = " + dept;
        ResultSet rs = stmt.executeQuery(query);
    }
}
