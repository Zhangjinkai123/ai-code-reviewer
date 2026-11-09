import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

public final class V1AcceptanceQuery {
    public static boolean userExists(Connection connection, String userName)
            throws SQLException {
        String sql = "SELECT id FROM users WHERE name = '" + userName + "'";
        try (Statement statement = connection.createStatement();
             ResultSet results = statement.executeQuery(sql)) {
            return results.next();
        }
    }
}
