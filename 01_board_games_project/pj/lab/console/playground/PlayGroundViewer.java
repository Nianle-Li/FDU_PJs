package console.playground;

import java.util.List;
import java.util.Scanner;

import console.gameview.GameViewer;
import console.screen.RawScreen;
import console.screen.Screen;
import domain.board.PieceColor;
import domain.game.Game;
import domain.game.GameException;

/**
 * 控制台游戏界面，显示游戏内容并处理输入
 * 界面布局从左到右，从上到下依次为：
 * 1. 棋盘状态
 * 2. 玩家信息（当前玩家、分数等）
 * 3. 游戏列表
 * 4. 游戏状态信息（错误提示、胜负等）
 * 5. 可用命令提示
 */
public class PlayGroundViewer {

    private final PlayGround playGround;

    public PlayGroundViewer(PlayGround playGround) {
        this.playGround = playGround;
    }

    // 显示游戏列表
    private void displayGameList(Screen screen) {
        int row = 0;
        screen.print(row++, 0, "游戏列表:");
        List<GameViewer> games = playGround.getGames();
        GameViewer currentGameViewer = playGround.getCurrentGameViewer(); // Get current viewer via PlayGround

        for (int i = 0; i < games.size(); i++) {
            GameViewer gameView = games.get(i);
            // Compare viewers directly for current game check
            if (gameView == currentGameViewer)
                screen.print(row++, 0, String.format("> %d.%s", i + 1, gameView.getGameType())); // 修改格式，移除 gameDesc
            else
                screen.print(row++, 0, String.format("  %d.%s", i + 1, gameView.getGameType())); // 修改格式，移除 gameDesc
        }
    }

    /**
     * 显示玩家状态信息
     */
    private void showPlayerStatus(Screen screen, GameViewer gameViewer) {
        Game game = gameViewer.getGame();
        Player player1 = playGround.getPlayer1();
        Player player2 = playGround.getPlayer2();

        // 获取当前游戏的序号(索引+1)
        int gameNumber = playGround.getGames().indexOf(gameViewer) + 1;
        // 在玩家信息上方显示游戏序号
        screen.print(-1, 0, String.format("Game %d", gameNumber));
        
        String player1Status = gameViewer.getPlayerStatus(0, player1,
                game.getCurrentPlayer().equals(player1.getPieceColor()), game.isOver());
        String player2Status = gameViewer.getPlayerStatus(1, player2,
                game.getCurrentPlayer().equals(player2.getPieceColor()), game.isOver());

        screen.print(0, 0, player1Status);
        screen.print(1, 0, player2Status);
        
        // 如果是五子棋游戏，在玩家信息后面显示回合数
        Integer roundCount = game.getCurrentRound(); // 使用新方法
        if (roundCount != null) {
            screen.print(2, 0, String.format("Current round: %d", roundCount));
        }
    }

    /**
     * 显示游戏状态信息
     * 包括错误提示、游戏进行状态和胜负结果等
     */
    private void showGameStatus(Screen screen) {
        List<String> messages = new java.util.ArrayList<>();
        String lastErrorMessage = playGround.getLastErrorMessage(); // Get error from PlayGround
        if (lastErrorMessage != null)
            messages.add("错误：" + lastErrorMessage);

        String gameStatus = playGround.getCurrentGameViewer().getGameStatus(); // Get status from current viewer
        if (!gameStatus.isEmpty())
            messages.add(gameStatus);
        screen.print(0, 0, String.join(";", messages));
    }

    /**
     * 清除终端屏幕
     * 根据操作系统使用不同的清屏命令
     */
    private void clearScreen() {
        try {
            String os = System.getProperty("os.name");
            if (os.contains("Windows")) {
                // Windows系统使用cls命令
                new ProcessBuilder("cmd", "/c", "cls").inheritIO().start().waitFor();
            } else {
                // Unix/Linux/Mac系统使用clear命令
                new ProcessBuilder("clear").inheritIO().start().waitFor();
            }
        } catch (Exception e) {
            // 如果清屏失败，使用ANSI转义序列进行替代清屏
            System.out.print("\033[H\033[2J");
            System.out.flush();
        }
    }

    /**
     * 显示完整游戏界面
     * 包括棋盘、玩家信息、游戏列表、状态信息和命令提示
     */
    private void displayPlayground() {
        GameViewer gameViewer = playGround.getCurrentGameViewer();
        RawScreen screen = new RawScreen(50, 50);
        // 显示游戏。游戏的显示有下面五部分：
        // 1. 棋盘状态
        gameViewer.showBoard(screen.offset(0, 0));
        // 2. 玩家的状态（玩家列表、当前玩家等信息）
        this.showPlayerStatus(screen.offset(gameViewer.getSize().getY() / 2, gameViewer.getSize().getX() * 2 + 4),
                gameViewer);
        // 3. 游戏列表（当前启动的游戏列表以及当前游戏）
        // 增加水平偏移量，为炸弹数量显示留出足够空间
        this.displayGameList(screen.offset(1, gameViewer.getSize().getX() * 2 + 37));
        // 4. 游戏状态（错误信息、游戏当前状态信息等）
        this.showGameStatus(screen.offset(gameViewer.getSize().getY() + 1, 0));
        // 5. 当前游戏支持的命令列表
        gameViewer.showCommandList(screen.offset(gameViewer.getSize().getY() + 2, 0), playGround);
        screen.outputToConsole();
    }

    /**
     * 启动游戏主循环
     * 显示界面、获取输入并执行命令
     */
    public void run() {
        try (Scanner scanner = new Scanner(System.in)) {
            while (true) {
                try {
                    clearScreen();
                    displayPlayground();

                    String input;
                    if (playGround.isInPlaybackMode()) {
                        input = playGround.getNextPlaybackCommand();
                        if (input == null) {
                            // 使用 nextLine() 读取整行输入
                            input = scanner.nextLine().trim();
                        } else {
                            System.out.println("执行命令: " + input);
                            try {
                                Thread.sleep(playGround.getPlaybackDelay());
                            } catch (InterruptedException e) {
                                Thread.currentThread().interrupt();
                            }
                        }
                    } else {
                        // 使用 nextLine() 读取整行输入
                        input = scanner.nextLine().trim();

                    }

                    playGround.executeCommand(input);

                } catch (GameException e) {
                    playGround.setLastErrorMessage(e.getMessage());
                }
            }
        }
    }

    public static void main(String[] args) {
        // Create Players
        Player player1 = new Player("Jiajia", PieceColor.BLACK);
        Player player2 = new Player("Paopao", PieceColor.WHITE);

        // Create PlayGround with players
        PlayGround playGround = new PlayGround(player1, player2);

        // Create PlayGroundVIew with the PlayGround logic instance
        PlayGroundViewer playGroundView = new PlayGroundViewer(playGround);

        // Run the view
        playGroundView.run();
    }
}

