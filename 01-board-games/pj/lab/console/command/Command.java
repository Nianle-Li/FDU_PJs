package console.command;

/**
 * 命令接口。不同的游戏有相同的命令，也有不同的命令。每个命令对象需要能够：
 * <ul>
 * <li>判断输入的字符是否可以解析为命令</li>
 * <li>命令是否可用。比如，PlacePieceCommand在游戏结束后不可用</li>
 * <li>命令的提示信息，比如"退出游戏(quit)"等</li>
 * <li>执行命令</li>
 * </ul>
 */
public interface Command {

    // 判断输入的字符是否可以解析为命令
    boolean canAccept(String input);

    // 执行命令
    void execute(String input);

    // 命令的提示信息，比如"退出游戏(quit)"等
    String prompt();

    // 命令是否可用。比如，PlacePieceCommand在游戏结束后不可用
    boolean isEnabled();
}

