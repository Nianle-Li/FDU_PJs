package console.gameview;

import java.util.ArrayList;
import java.util.List;

import console.BoardViewer;
import console.command.Command;
import console.command.NewGameCommand;
import console.command.PassCommand;
import console.command.PlacePieceCommand;
import console.command.QuitCommand;
import console.command.SelectGameCommand;
import console.playground.PlayGround;
import console.playground.Player;
import console.screen.Screen;
import domain.board.Location;
import domain.board.PieceColor;
import domain.game.ReversiGame;

public class ReversiGameView extends GameViewer {
    private final ReversiGame game;
    // 添加PlayGround成员变量
    private PlayGround playGround;

    public static ReversiGameView create() {
        return new ReversiGameView(new ReversiGame());
    }

    public ReversiGameView(ReversiGame game, String gameDesc) {
        super(gameDesc);
        this.game = game;
    }

    public ReversiGameView(ReversiGame game) {
        this(game, "");
    }

    @Override
    public ReversiGame getGame() {
        return game;
    }

    public void showBoard(Screen screen) {
        // 先用BoardUI显示棋盘
        BoardViewer boardUI = new BoardViewer(game.getBoard());
        boardUI.display(screen);

        // 获取当前玩家所有合法落子点
        PieceColor currentPiece = game.getCurrentPlayer();
        List<Location> validMoves = game.getAllValidLocation(currentPiece);

        // 在合法落子点位置覆盖为'+'
        for (Location loc : validMoves) {
            // BoardUI的棋盘内容起始行为1，起始列为2+2*y
            screen.print(loc.getX() + 1, 2 + loc.getY() * 2, '+');
        }
    }

    @Override
    public String getGameStatus() {
        if (game.isOver()) {
            if (game.getWinner() == null)
                return "游戏结束：平局";
            else {
                // 获取比分
                Integer blackCount = game.getPlayerScore(PieceColor.BLACK); // 使用新方法
                Integer whiteCount = game.getPlayerScore(PieceColor.WHITE); // 使用新方法
                
                // 如果playGround不为null，获取玩家信息
                if (playGround != null) {
                    Player blackPlayer = playGround.getPlayer(PieceColor.BLACK);
                    Player whitePlayer = playGround.getPlayer(PieceColor.WHITE);
                    
                    // 获取获胜玩家
                    Player winner = playGround.getPlayer(game.getWinner());
                    
                    // 返回包含玩家名称的格式化信息
                    return String.format("游戏结束，[%s] 获胜！ ([%s]● %d ; [%s]○ %d)", 
                        winner.getName(), 
                        blackPlayer.getName(), blackCount, 
                        whitePlayer.getName(), whiteCount);
                } else {
                    // 如果没有playGround引用，使用原有格式
                    return String.format("游戏结束，%s获胜(%d:%d)", game.getWinner(), 
                                       blackCount != null ? blackCount : 0, 
                                       whiteCount != null ? whiteCount : 0);
                }
            }
        } else if (game.canCurrentPlayerPass()) { // 使用新方法
            return "当前玩家无法落子,请pass跳过";
        } else {
            return "";
        }
    }

    public String getPlayerStatus(int index, Player player, boolean isCurrentPlayer, boolean gameOver) {
        String playerStatus = super.getPlayerStatus(index, player, isCurrentPlayer, gameOver);
        // 玩家状态信息中显示棋子数量
        Integer count = game.getPlayerScore(player.getPieceColor()); // 使用新方法
        return playerStatus + " " + (count != null ? count : "");
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
                return !game.isOver() && !game.canCurrentPlayerPass(); // 使用新方法
            }
        });
        commands.add(new SelectGameCommand(session));
        commands.add(new NewGameCommand(session));
        commands.add(new PassCommand(game));
        commands.add(new QuitCommand());
        
        // 添加通用命令
        commands.addAll(getCommonCommands(session));
        
        return commands;
    }

    @Override
    public Location getSize() {
        return Location.of(game.getBoard().getSize(), game.getBoard().getSize());
    }

}

