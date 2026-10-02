package console.command;

public class QuitCommand implements Command {
    @Override
    public void execute(String input) {
        System.exit(0);
    }
    @Override
    public boolean canAccept(String input) {
        return input.equals("quit");
    }

    @Override
    public String prompt() {
        return "退出程序(quit)";
    }

    @Override
    public boolean isEnabled() {
        return true; // 总是启用quit命令
    }

}
