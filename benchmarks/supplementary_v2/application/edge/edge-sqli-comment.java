package com.regulacloud.benchmark;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

class EdgeSqliComment {
    public void getUser(Connection conn, String userId) throws SQLException {
        // String query = "SELECT * FROM users WHERE id = '" + userId + "'";
        String query = "SELECT * FROM users WHERE id = ?";
        PreparedStatement ps = conn.prepareStatement(query);
        ps.setString(1, userId);
        ResultSet rs = ps.executeQuery();
    }
}
