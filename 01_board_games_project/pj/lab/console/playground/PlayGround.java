package console.playground;

import java.util.ArrayList;
import java.util.List;

import console.command.Command;
import console.gameview.GameViewer;
import console.gameview.GomokuGameView;
import console.gameview.PeaceGameView;
import console.gameview.ReversiGameView;
import domain.board.PieceColor;
import domain.game.GameException;

public class PlayGround {

    private final Player player1;
    private final Player player2;
    private final List<GameViewer> games = new ArrayList<>();
    private int currentGame = 0;
    // 最后一次用户输入发生的错误
    private String lastErrorMessage;
    
    // 回放模式相关属性
    private List<String> playbackCommands = null;
    private int currentPlaybackIndex = 0;
    private long playbackDelay = 0;
    private boolean inPlaybackMode = false;

    public PlayGround(Player player1, Player player2) {
        this.player1 = player1;
        this.player2 = player2;
        // Initialize default games
        games.add(PeaceGameView.create());
        games.add(ReversiGameView.create());
        games.add(GomokuGameView.create());
    }

    public Player getPlayer1() {
        return player1;
    }

    public Player getPlayer2() {
        return player2;
    }

    public Player getPlayer(PieceColor color) {
        if (color == player1.getPieceColor()) {
            return player1;
        } else {
            return player2;
        }
    }

    public void activateGame(int index) {
        if (index < 0 || index >= games.size()) {
            throw new GameException(String.format("游戏编号应该在1~%d之间", games.size()));
        }
        currentGame = index;
    }

    public List<GameViewer> getGames() {
        return games;
    }

    public void addGame(GameViewer gameViewer) {
        games.add(gameViewer);
    }

    public GameViewer getCurrentGameViewer() {
        return games.get(currentGame);
    }

    public String getLastErrorMessage() {
        return lastErrorMessage;
    }

    public void setLastErrorMessage(String message) {
        this.lastErrorMessage = message;
    }

    public void clearLastErrorMessage() {
        this.lastErrorMessage = null;
    }

    public void executeCommand(String input) {
        // 如果输入以playback开头，输出调试信息
        if (input != null && input.toLowerCase().startsWith("playback")) {
            System.out.println("检测到playback命令: " + input);
        }
        
        GameViewer gameViewer = getCurrentGameViewer();
        List<Command> commands = gameViewer.getCommandList(this);
        for (Command command : commands) {
            if (command.isEnabled() && command.canAccept(input)) {
                // 如果是playback命令，输出成功识别的信息
                if (command.getClass().getSimpleName().equals("PlaybackCommand")) {
                    System.out.println("成功识别playback命令，正在执行...");
                }
                
                command.execute(input);
                clearLastErrorMessage();
                return;
            }
        }
        throw new GameException("未识别的或当前无效的命令:" + input);
    }
    
    /**
     * 开始命令回放模式
     * @param commands 要执行的命令列表
     * @param delayMs 命令间延迟(毫秒)
     */
    public void startPlayback(List<String> commands, long delayMs) {
        this.playbackCommands = commands;
        this.currentPlaybackIndex = 0;
        this.playbackDelay = delayMs;
        this.inPlaybackMode = true;
    }
    
    /**
     * 检查是否正在回放模式
     */
    public boolean isInPlaybackMode() {
        return inPlaybackMode;
    }
    
    /**
     * 获取下一个要执行的回放命令
     * @return 命令字符串，如果没有更多命令则返回null
     */
    public String getNextPlaybackCommand() {
        if (!inPlaybackMode || playbackCommands == null || 
            currentPlaybackIndex >= playbackCommands.size()) {
            inPlaybackMode = false;
            return null;
        }
        
        return playbackCommands.get(currentPlaybackIndex++);
    }
    
    /**
     * 获取回放模式的延迟时间
     */
    public long getPlaybackDelay() {
        return playbackDelay;
    }
}