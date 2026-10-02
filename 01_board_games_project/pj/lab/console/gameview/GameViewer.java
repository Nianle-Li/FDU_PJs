package console.gameview;

import java.util.ArrayList;
import java.util.List;

import console.command.Command;
import console.command.PlaybackCommand;
import console.playground.PlayGround;
import console.playground.Player;
import console.screen.Screen;
import domain.board.Location;
import domain.game.Game;

/**
 * 游戏视图，负责显示游戏的提示信息、状态，以及确定能接受用户输入的命令。
 * 该类型是抽象类，不同的游戏有不同的实现。
 */
abstract public class GameViewer {

    // 游戏描述,用于标记游戏的信息，比如：2.peace(结束状态测试) 中，结束状态测试就是游戏描述
    private String gameDesc;

    public GameViewer(String gameDesc) {
        this.gameDesc = gameDesc;
    }

    public String getGameDesc() {
        return gameDesc;
    }

    /**
     * 游戏视图管理的Game
     */
    abstract public Game getGame() ;

    public String getGameType() {
        return getGame().getGameType();
    }

    /**
     * 不同的游戏显示Board的方式不同
     */
    abstract public void showBoard(Screen screen);

    /**
     * 显示游戏的状态信息，包括游戏的胜负和结束状态等
     */
    abstract public String getGameStatus();

    /**
     * 获取游戏的通用命令列表（每个游戏都共有的命令）
     */
    protected List<Command> getCommonCommands(PlayGround playGround) {
        List<Command> commonCommands = new ArrayList<>();
        commonCommands.add(new PlaybackCommand(playGround));
        return commonCommands;
    }

    /**
     * 不同的游戏支持不同的命令集
     */
    abstract public List<Command> getCommandList(PlayGround playGround);

    /**
     * 显示当前玩家可以执行的命令，只显示当前有效的命令，
     * 比如，如果当前游戏已经完成，落子命令就不应该显示和执行。命令列表的典型格式为：
     * 
     * 请玩家[Tom]输入落子位置(1A)/游戏编号:(1~4)/新游戏(peace/gomoku/reversi)/退出程序(quit)
     */
    public void showCommandList(Screen screen, PlayGround playGround) {
        List<Command> commands = getCommandList(playGround);
        String prompt = String.join("/",
                commands.stream()
                        .filter(x -> x.isEnabled())
                        .map(x -> x.prompt()).toList());
        screen.print(0, 0, prompt);
    }

    /**
     * 将玩家信息显示为：Player1 [Tom ] ●
     */
    public String getPlayerStatus(int index, Player player, boolean isCurrentPlayer, boolean gameOver) {
        String name = player.getName();
        String currentIndicator = gameOver ? " " : isCurrentPlayer ? player.getPieceColor().toString() : " ";
        return String.format("Player%d [%-6s] %s", index + 1, name, currentIndicator);
    }

    abstract public Location getSize();
}