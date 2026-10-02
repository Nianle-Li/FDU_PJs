package gui.controllers;

import domain.board.Location;
import domain.board.PieceColor;
import domain.game.Game;
import domain.game.GameException;
import domain.game.GameFactory;
import gui.models.GameSession;
import gui.models.GameStateManager;
import gui.views.BoardView;
import gui.views.GameListView;
import javafx.application.Platform;
import javafx.fxml.FXML;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.VBox;
import javafx.stage.FileChooser;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class MainController {

    @FXML private BorderPane mainPane;
    @FXML private BoardView boardView;
    @FXML private VBox playerInfoPanel;
    @FXML private Label player1Label;
    @FXML private Label player2Label;
    @FXML private Label currentRoundLabel;
    @FXML private Label player1BombsLabel;
    @FXML private Label player2BombsLabel;
    @FXML private Label gameStatusLabel;
    @FXML private Label currentGameLabel;
    @FXML private GameListView gameListView;
    @FXML private Button newPeaceGameButton;
    @FXML private Button newReversiGameButton;
    @FXML private Button newGomokuGameButton;
    @FXML private Button passButton;
    @FXML private Button useBombButton;
    @FXML private Button playbackButton;
    @FXML private Button quitButton;
    @FXML private Label gameResultLabel;

    private GameSession gameSession;
    private ScheduledExecutorService playbackExecutor;

    // 初始化控制器
    public void initialize() {
        initializeGameSession();
        initializeUI();
        initializeEventHandlers();
        updateUI();
    }
    
    // 初始化游戏会话，尝试恢复保存的状态或创建新会话
    private void initializeGameSession() {
        GameSession loadedSession = GameStateManager.loadGameState();
        if (loadedSession != null) {
            gameSession = loadedSession;
        } else {
            gameSession = new GameSession("黑棋 [Jia] ", "白棋 [Ran] ");
        }
    }
    
    // 初始化UI组件
    private void initializeUI() {
        // 初始化游戏列表
        gameListView.setItems(gameSession.getGames());
        
        // 监听游戏选择变化
        gameListView.getSelectionModel().selectedItemProperty().addListener((obs, oldVal, newVal) -> {
            if (newVal != null) {
                switchGame(gameListView.getSelectionModel().getSelectedIndex());
            }
        });
        
        // 监听当前游戏索引变化
        gameSession.currentGameIndexProperty().addListener((obs, oldVal, newVal) -> {
            gameListView.getSelectionModel().select(newVal.intValue());
        });
        
        // 初始化棋盘视图
        boardView.setOnCellClicked(this::handleBoardClick);
        
        // 选择当前游戏
        if (!gameSession.getGames().isEmpty()) {
            int currentIndex = Math.max(0, Math.min(gameSession.getCurrentGameIndex(), 
                                                   gameSession.getGames().size() - 1));
            gameListView.getSelectionModel().select(currentIndex);
        }
    }
    
    // 初始化所有事件处理器
    private void initializeEventHandlers() {
        // 动态创建游戏按钮事件
        newPeaceGameButton.setOnAction(e -> createNewGame("peace"));
        newReversiGameButton.setOnAction(e -> createNewGame("reversi"));
        newGomokuGameButton.setOnAction(e -> createNewGame("gomoku"));
        
        passButton.setOnAction(e -> executeGameAction("pass"));
        useBombButton.setOnAction(e -> { // 修改 useBombButton 的事件处理器
            boardView.setBombMode(true);
            updateUI(); // 添加这行来刷新UI并显示提示
        });
        playbackButton.setOnAction(e -> openPlaybackFile());
        quitButton.setOnAction(e -> quitApplication());
    }

    // 处理棋盘点击事件
    private void handleBoardClick(int row, int col) {
        try {
            Game currentGame = gameSession.getCurrentGame();
            
            // 处理炸弹模式 - 这里 instanceof 仍然是合理的，因为它是非常特定的交互
            if (boardView.isBombMode() && currentGame.getGameType().equals("gomoku")) {
                 // 需要确保 useBomb 是 GomokuGame 的公共方法或通过 executeAction 调用
                if (currentGame instanceof domain.game.GomokuGame gomokuGame) { // 安全转换
                    gomokuGame.useBomb(new Location(row, col));
                }
                boardView.setBombMode(false);
            } else {
                currentGame.placePiece(new Location(row, col));
            }
            
            updateUI();
        } catch (GameException e) {
            // 移除错误显示，简化处理
        }
    }

    // 切换到指定索引的游戏
    private void switchGame(int index) {
        gameSession.setCurrentGameIndex(index);
        boardView.setBombMode(false);
        updateUI();
    }

    // 创建新游戏
    private void createNewGame(String gameType) {
        try {
            Game newGame = GameFactory.createGame(gameType);
            gameSession.addGame(newGame);
            boardView.setBombMode(false);
        } catch (Exception e) {
            // 处理创建游戏失败
        }
    }
    
    // 执行游戏特殊操作
    private void executeGameAction(String action) {
        try {
            Game currentGame = gameSession.getCurrentGame();
            if (currentGame.getSupportedActions().contains(action)) {
                currentGame.executeAction(action);
                updateUI();
            }
        } catch (GameException e) {
            // 处理执行动作失败
        }
    }

    // 更新所有UI元素显示
    private void updateUI() {
        Game currentGame = gameSession.getCurrentGame();
        if (currentGame == null) return; // 添加null检查
        
        // 更新当前游戏局数标签
        int gameIndex = gameListView.getSelectionModel().getSelectedIndex() + 1;
        currentGameLabel.setText("游戏" + gameIndex);
        
        // 更新棋盘
        boardView.updateBoard(currentGame.getBoard());
        
        // 更新游戏结果显示
        updateGameResult(currentGame);
        
        // 更新当前玩家信息
        PieceColor currentColor = currentGame.getCurrentPlayer();
        String player1BaseText = gameSession.getPlayer1Name(); // 例如 "黑棋 [Jia] "
        String player2BaseText = gameSession.getPlayer2Name(); // 例如 "白棋 [Ran] "

        String player1DisplayText = player1BaseText.trim(); // 移除末尾空格以便拼接
        String player2DisplayText = player2BaseText.trim(); // 移除末尾空格以便拼接

        // 清除之前的高亮样式
        player1Label.getStyleClass().remove("current-player-highlight");
        player2Label.getStyleClass().remove("current-player-highlight");

        // 为当前玩家应用高亮样式并追加棋子符号
        if (currentColor == PieceColor.BLACK) {
            player1Label.getStyleClass().add("current-player-highlight");
            player1DisplayText += " ●";
        } else { // currentColor == PieceColor.WHITE
            player2Label.getStyleClass().add("current-player-highlight");
            player2DisplayText += " ○";
        }

        // 追加游戏特定信息（分数或炸弹）
        Integer blackScore = currentGame.getPlayerScore(PieceColor.BLACK);
        Integer whiteScore = currentGame.getPlayerScore(PieceColor.WHITE);
        if (blackScore != null && whiteScore != null) {
            player1DisplayText += " " + blackScore;
            player2DisplayText += " " + whiteScore;
        }

        Integer blackBombs = currentGame.getPlayerBombs(PieceColor.BLACK);
        Integer whiteBombs = currentGame.getPlayerBombs(PieceColor.WHITE);
        if (blackBombs != null) {
            player1DisplayText += " 💣*" + blackBombs;
        }
        if (whiteBombs != null) {
            player2DisplayText += " 💣*" + whiteBombs;
        }
        
        player1Label.setText(player1DisplayText);
        player2Label.setText(player2DisplayText);
        
        // 更新游戏状态
        if (currentGame.isOver()) {
            PieceColor winner = currentGame.getWinner();
            if (winner != null) {
                gameStatusLabel.setText("游戏结束! " + (winner == PieceColor.BLACK ? "黑方" : "白方") + "获胜!");
            } else {
                gameStatusLabel.setText("游戏结束! 平局!");
            }
        } else {
            // 修改此处：不再显示轮到哪一方
            gameStatusLabel.setText("游戏进行中"); 
        }
        
        // 更新特殊游戏信息
        updateSpecialGameInfo(currentGame);
        
        // 更新按钮状态
        updateButtonStatus(currentGame);
    }

    // 更新游戏结果显示
    private void updateGameResult(Game game) {
        if (game.isOver()) {
            gameResultLabel.setVisible(true);
            PieceColor winner = game.getWinner();
            
            // 使用 getPlayerScore 获取分数
            Integer blackScore = game.getPlayerScore(PieceColor.BLACK);
            Integer whiteScore = game.getPlayerScore(PieceColor.WHITE);

            if (blackScore != null && whiteScore != null) { // 表明是类似黑白棋的游戏
                String blackPlayerName = gameSession.getPlayer1Name().trim().replaceAll(".*\\[(.*)\\].*", "$1");
                String whitePlayerName = gameSession.getPlayer2Name().trim().replaceAll(".*\\[(.*)\\].*", "$1");
                
                String resultText = String.format("游戏结束！黑棋 [%s] %d  白棋 [%s] %d\n", 
                    blackPlayerName, blackScore, whitePlayerName, whiteScore);
                
                if (winner != null) {
                    String winnerName = winner == PieceColor.BLACK ? blackPlayerName : whitePlayerName;
                    resultText += String.format("玩家 [%s] 获胜！", winnerName);
                } else {
                    resultText += "平局！";
                }
                gameResultLabel.setText(resultText);
            } else {
                // 其他游戏的结果显示
                if (winner != null) {
                    String winnerName = winner == PieceColor.BLACK ? 
                        gameSession.getPlayer1Name().trim() : gameSession.getPlayer2Name().trim();
                    gameResultLabel.setText("游戏结束! " + winnerName + " 获胜!");
                } else {
                    gameResultLabel.setText("游戏结束! 平局!");
                }
            }
        } else if (boardView.isBombMode()) { // 修改这里，优先判断炸弹模式
            // 炸弹模式提示
            gameResultLabel.setVisible(true);
            gameResultLabel.setText("请放置炸弹💣！"); // 修改提示文本
        } else {
            gameResultLabel.setVisible(false);
        }
    }

    // 更新游戏特殊信息显示（如回合数、可落子位置等）
    private void updateSpecialGameInfo(Game game) {
        // 隐藏所有特定游戏的UI元素
        player1BombsLabel.setVisible(false); 
        player2BombsLabel.setVisible(false); 
        currentRoundLabel.setVisible(false);
        
        // 根据游戏类型显示特定信息
        Integer round = game.getCurrentRound();
        if (round != null) {
            currentRoundLabel.setText("当前回合: " + round);
            currentRoundLabel.setVisible(true);
        }
        
        // 显示有效移动位置
        List<Location> validMoves = game.getCurrentPlayerValidMoves();
        if (!validMoves.isEmpty()) {
            boardView.highlightValidMoves(validMoves);
        } else {
            boardView.clearHighlights();
        }
    }
    
    // 更新游戏操作按钮状态
    private void updateButtonStatus(Game game) {
        // 通用按钮状态
        boolean gameActive = !game.isOver();
        
        // 游戏特定按钮状态
        passButton.setVisible(game.getGameType().equals("reversi")); // 或者更通用的方式
        passButton.setDisable(!gameActive || !game.canCurrentPlayerPass());
        
        useBombButton.setVisible(game.getGameType().equals("gomoku")); // 或者更通用的方式
        useBombButton.setDisable(!gameActive || !game.canCurrentPlayerUseBomb());
    }

    // 打开回放文件选择对话框
    private void openPlaybackFile() {
        FileChooser fileChooser = new FileChooser();
        fileChooser.setTitle("选择回放文件");
        fileChooser.getExtensionFilters().add(
            new FileChooser.ExtensionFilter("命令文件", "*.cmd")
        );
        
        File selectedFile = fileChooser.showOpenDialog(mainPane.getScene().getWindow());
        if (selectedFile != null) {
            startPlayback(selectedFile.getAbsolutePath());
        }
    }
    
    // 开始回放指定文件中的命令
    private void startPlayback(String filename) {
        try {
            List<String> commands = new ArrayList<>();
            
            // 读取命令文件
            File file = new File(filename);
            if (!file.exists()) {
                throw new GameException("找不到文件: " + filename);
            }
            
            try (BufferedReader reader = new BufferedReader(new FileReader(file))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (!line.isEmpty() && !line.startsWith("REM")) {
                        commands.add(line);
                    }
                }
            }
            
            if (commands.isEmpty()) {
                showError("命令文件为空");
                return;
            }
            
            // 如果已经有回放在进行，先取消
            if (playbackExecutor != null && !playbackExecutor.isShutdown()) {
                playbackExecutor.shutdownNow();
            }
            
            // 创建新的回放执行器
            playbackExecutor = Executors.newSingleThreadScheduledExecutor();
            
            final int[] commandIndex = {0};
            playbackExecutor.scheduleAtFixedRate(() -> {
                if (commandIndex[0] < commands.size()) {
                    String cmd = commands.get(commandIndex[0]++);
                    Platform.runLater(() -> processPlaybackCommand(cmd));
                } else {
                    // 移除对messageArea的引用
                    Platform.runLater(() -> System.out.println("回放完成"));
                    playbackExecutor.shutdown();
                }
            }, 0, 1, TimeUnit.SECONDS);
            
        } catch (Exception e) {
            showError("回放错误: " + e.getMessage());
        }
    }
    
    // 处理单条回放命令
    private void processPlaybackCommand(String command) {
        if (command == null || command.trim().isEmpty()) {
            return;
        }

        try {
            if (command.equalsIgnoreCase("quit")) {
                Platform.exit();
                return;
            }

            Game currentGame = gameSession.getCurrentGame();

            if (command.matches("\\d+")) { // 切换游戏
                int gameIndex = Integer.parseInt(command) - 1;
                if (gameIndex >= 0 && gameIndex < gameSession.getGames().size()) {
                    switchGame(gameIndex);
                } else {
                    showError("回放：无效的游戏编号 " + command);
                }
            } else if (command.equals("peace") || command.equals("reversi") || command.equals("gomoku")) { // 创建新游戏
                createNewGame(command);
            } else if (command.equals("pass")) { // Pass命令
                if (currentGame.getSupportedActions().contains("pass")) {
                    currentGame.executeAction("pass");
                    updateUI();
                } else {
                    showError("回放：当前游戏不支持pass命令");
                }
            } else if (command.startsWith("@") && command.length() == 3) { // 使用炸弹，例如 @3F
                if (currentGame.getSupportedActions().contains("useBomb")) {
                    char rowChar = Character.toUpperCase(command.charAt(1));
                    char colChar = Character.toUpperCase(command.charAt(2));
                    int row, col;

                    if (rowChar >= '1' && rowChar <= '9') {
                        row = rowChar - '1';
                    } else if (rowChar >= 'A' && rowChar <= 'F') {
                        row = (rowChar - 'A') + 9;
                    } else {
                        throw new IllegalArgumentException("回放：无效的炸弹行坐标: " + rowChar);
                    }
                    col = colChar - 'A'; // 列标签 A-O 对应 0-14

                    if (row >= 0 && row < currentGame.getBoard().getSize() && 
                        col >= 0 && col < currentGame.getBoard().getSize()) {
                        currentGame.executeAction("useBomb", new Location(row, col));
                        updateUI();
                    } else {
                        throw new IllegalArgumentException("回放：炸弹坐标超出棋盘范围: " + command);
                    }
                } else {
                    showError("回放：当前游戏不支持炸弹命令");
                }
            } else if (command.length() == 2) { // 落子命令，例如 1A, H8
                char rowChar = Character.toUpperCase(command.charAt(0));
                char colChar = Character.toUpperCase(command.charAt(1));
                int row, col;

                if (rowChar >= '1' && rowChar <= '9') {
                    row = rowChar - '1';
                } else if (rowChar >= 'A' && rowChar <= 'F') { // 假设最大15x15，行标签 A-F 对应 9-14
                    row = (rowChar - 'A') + 9;
                } else {
                    throw new IllegalArgumentException("回放：无效的落子行坐标: " + rowChar);
                }
                col = colChar - 'A'; // 列标签 A-O 对应 0-14

                if (row >= 0 && row < currentGame.getBoard().getSize() && col >= 0 && col < currentGame.getBoard().getSize()) {
                    currentGame.placePiece(new Location(row, col));
                    updateUI();
                } else {
                    throw new IllegalArgumentException("回放：落子坐标超出棋盘范围: " + command);
                }
            } else {
                showError("回放：未知命令: " + command);
            }
        } catch (Exception e) {
            showError("回放处理命令时出错: " + command + " - " + e.getMessage());
        }
    }
    
    // 退出应用程序，保存游戏状态
    private void quitApplication() {
        GameStateManager.saveGameState(gameSession);
        Platform.exit();
    }
    
    // 显示错误信息
    private void showError(String message) {
        // 简化错误处理，仅输出到控制台
        System.err.println("错误: " + message);
    }
    
    // 获取当前游戏会话
    public GameSession getGameSession() {
        return gameSession;
    }
}
