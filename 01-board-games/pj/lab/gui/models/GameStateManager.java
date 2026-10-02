package gui.models;

import domain.board.Board;
import domain.board.PieceColor;
import domain.game.Game;
import domain.game.GameFactory; // 使用GameFactory创建游戏实例
import java.io.*;
import java.lang.reflect.Field; // 添加此行导入
import java.util.ArrayList;
import java.util.List;



/**
 * 游戏状态管理器，负责保存和恢复游戏状态
 */
public class GameStateManager {
    private static final String SAVE_FILE = "pj.game";
    
    /**
     * 保存游戏状态到文件
     */
    public static void saveGameState(GameSession gameSession) {
        try {
            GameState gameState = convertToGameState(gameSession);
            
            try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(SAVE_FILE))) {
                oos.writeObject(gameState);
                System.out.println("游戏状态已保存到 " + SAVE_FILE);
            }
        } catch (Exception e) {
            System.err.println("保存游戏状态失败: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * 从文件恢复游戏状态
     */
    public static GameSession loadGameState() {
        File saveFile = new File(SAVE_FILE);
        if (!saveFile.exists()) {
            System.out.println("未找到保存文件，创建新游戏会话");
            return null;
        }
        
        try (ObjectInputStream ois = new ObjectInputStream(new FileInputStream(SAVE_FILE))) {
            GameState gameState = (GameState) ois.readObject();
            System.out.println("游戏状态已从 " + SAVE_FILE + " 恢复");
            return convertFromGameState(gameState);
        } catch (Exception e) {
            System.err.println("恢复游戏状态失败: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * 将GameSession转换为可序列化的GameState
     */
    private static GameState convertToGameState(GameSession gameSession) throws Exception {
        List<SerializableGame> serializableGames = new ArrayList<>();
        
        for (Game game : gameSession.getGames()) {
            SerializableGame sg = new SerializableGame();
            sg.setGameType(game.getGameType());
            sg.setCurrentPlayer(game.getCurrentPlayer());
            sg.setFinished(game.isOver());
            sg.setWinner(game.getWinner());
            
            // 保存棋盘状态
            Board board = game.getBoard();
            sg.setBoardSize(board.getSize());
            PieceColor[][] boardState = new PieceColor[board.getSize()][board.getSize()];
            for (int i = 0; i < board.getSize(); i++) {
                for (int j = 0; j < board.getSize(); j++) {
                    boardState[i][j] = board.getPiece(i, j);
                }
            }
            sg.setBoardState(boardState);
            
            // 保存附加属性
            sg.setAdditionalAttributes(game.getAdditionalAttributes());
            
            serializableGames.add(sg);
        }
        
        return new GameState(
            gameSession.getPlayer1Name(),
            gameSession.getPlayer2Name(),
            serializableGames,
            gameSession.getGames().indexOf(gameSession.getCurrentGame()) // 确保 getCurrentGame() 返回有效索引
        );
    }
    
    /**
     * 将GameState转换为GameSession
     */
    private static GameSession convertFromGameState(GameState gameState) throws Exception {
        GameSession gameSession = new GameSession(gameState.getPlayer1Name(), gameState.getPlayer2Name());
        
        // 清空默认游戏
        gameSession.getGames().clear();
        
        // 恢复游戏列表
        for (SerializableGame sg : gameState.getGames()) {
            Game game = createGameFromSerializable(sg);
            gameSession.getGames().add(game);
        }
        
        // 设置当前游戏
        if (gameState.getCurrentGameIndex() >= 0 && gameState.getCurrentGameIndex() < gameSession.getGames().size()) {
            gameSession.setCurrentGameIndex(gameState.getCurrentGameIndex());
        }
        
        return gameSession;
    }
    
    /**
     * 从序列化数据创建具体的Game对象
     */
    private static Game createGameFromSerializable(SerializableGame sg) throws Exception {
        // 使用 GameFactory 创建游戏实例
        Game game = GameFactory.createGame(sg.getGameType());
        
        // 恢复棋盘状态
        Board board = game.getBoard();
        board.clear(); 
        
        PieceColor[][] boardState = sg.getBoardState();
        if (boardState != null) {
            for (int i = 0; i < sg.getBoardSize(); i++) {
                for (int j = 0; j < sg.getBoardSize(); j++) {
                    if (boardState[i][j] != null) {
                        board.placePiece(i, j, boardState[i][j]);
                    }
                }
            }
        }
        
        // 恢复游戏基本状态
        setPrivateField(game, "currentPieceColor", sg.getCurrentPlayer());
        setPrivateField(game, "finished", sg.isFinished());
        setPrivateField(game, "winner", sg.getWinner());

        // 恢复附加属性
        if (sg.getAdditionalAttributes() != null) {
            game.restoreAdditionalAttributes(sg.getAdditionalAttributes());
        }
        
        return game;
    }
    
    /**
     * 使用反射设置私有字段
     */
    private static void setPrivateField(Object obj, String fieldName, Object value) throws Exception {
        Class<?> clazz = obj.getClass();
        Field field = null;
        
        // 在当前类及其父类中查找字段
        while (clazz != null && field == null) {
            try {
                field = clazz.getDeclaredField(fieldName);
            } catch (NoSuchFieldException e) {
                clazz = clazz.getSuperclass();
            }
        }
        
        if (field != null) {
            field.setAccessible(true);
            field.set(obj, value);
        }
    }
}
