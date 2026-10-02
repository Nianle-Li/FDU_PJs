package console.gameview;

import java.util.ArrayList;
import java.util.List;

import console.BoardViewer;
import console.command.Command;
import console.command.NewGameCommand;
import console.command.PlacePieceCommand;
import console.command.QuitCommand;
import console.command.SelectGameCommand;
import console.command.UseBombCommand;
import console.playground.PlayGround;
import console.playground.Player;
import console.screen.Screen;
import domain.board.Location;
import domain.game.GomokuGame;

public class GomokuGameView extends GameViewer {
    private final GomokuGame game;
    private final BoardViewer boardUI;
    // 添加PlayGround成员变量
    private PlayGround playGround;

    public static GomokuGameView create() {
        return new GomokuGameView(new GomokuGame());
    }

    public GomokuGameView(GomokuGame game, String gameTag) {
        super(gameTag);
        this.game = game;
        this.boardUI = new BoardViewer(game.getBoard());
    }

    public GomokuGameView(GomokuGame game) {
        this(game, "");
    }

    @Override
    public GomokuGame getGame() {
        return game;
    }

    @Override
    public void showBoard(Screen screen) {
        boardUI.display(screen);
    }

    @Override
    public String getGameStatus() {
        if (game.isOver()) {
            if (game.getWinner() == null)
                return "游戏结束：平局";
            else {
                // 如果playGround不为null，获取玩家信息
                if (playGround != null) {
                    Player winner = playGround.getPlayer(game.getWinner());
                    return String.format("游戏结束！[%s] %s 获胜！", winner.getName(), game.getWinner());
                } else {
                    return String.format("游戏结束：%s胜", game.getWinner());
                }
            }
        } else {
            return "";
        }
    }

    @Override
    public List<Command> getCommandList(PlayGround session) {
        // 保存PlayGround引用供getGameStatus使用
        this.playGround = session;
        
        List<Command> commands = new ArrayList<>();
        
        // 添加游戏特定命令
        commands.add(new PlacePieceCommand(game, session) {
            @Override
            public boolean isEnabled() {
                return !game.isOver();
            }
        });
        commands.add(new UseBombCommand(game, session));
        commands.add(new SelectGameCommand(session));
        commands.add(new NewGameCommand(session));
        commands.add(new QuitCommand());
        
        // 添加通用命令
        commands.addAll(getCommonCommands(session));
        
        return commands;
    }

    @Override
    public Location getSize() {
        return Location.of(game.getBoard().getSize(), game.getBoard().getSize());
    }

    /**
     * 重写玩家状态显示方法，添加炸弹数量
     */
    @Override
    public String getPlayerStatus(int index, Player player, boolean isCurrentPlayer, boolean gameOver) {
        String baseStatus = super.getPlayerStatus(index, player, isCurrentPlayer, gameOver);
        
        // 获取玩家炸弹数量
        Integer bombCount = game.getPlayerBombs(player.getPieceColor()); // 使用新方法
        
        // 在基本状态后添加炸弹数量
        return String.format("%s  %d bomb", baseStatus, (bombCount != null ? bombCount : 0));
    }
}