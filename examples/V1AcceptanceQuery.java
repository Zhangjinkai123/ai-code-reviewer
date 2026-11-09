import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public final class V1AcceptanceQuery {
    public static boolean userExists(Connection connection, String userName)
            throws SQLException {
        String sql = "SELECT id FROM users WHERE name = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, userName);
            try (ResultSet results = statement.executeQuery()) {
                return results.next();
            }
        }
    }
}
