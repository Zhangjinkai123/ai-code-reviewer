public class HelloWorld {
    public static void main(String[] args) {
        String ids = "1,2,3";
        String sql =
            "select * from user where id="
            + ids;
        System.out.println("Hello World!");
    }
}
