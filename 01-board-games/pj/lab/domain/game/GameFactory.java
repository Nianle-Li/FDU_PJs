package domain.game;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.function.Supplier;

/**
 * 游戏工厂类 - 支持动态注册和创建游戏
 */
public class GameFactory {
    private static final Map<String, GameInfo> gameRegistry = new HashMap<>();
    
    static {
        // 注册默认游戏
        register("peace", "和平棋", PeaceGame::new);
        register("reversi", "黑白棋", ReversiGame::new);
        register("gomoku", "五子棋", GomokuGame::new);
    }
    
    /**
     * 游戏信息类
     */
    public static class GameInfo {
        private final String displayName;
        private final Supplier<Game> creator;
        
        public GameInfo(String displayName, Supplier<Game> creator) {
            this.displayName = displayName;
            this.creator = creator;
        }
        
        public String getDisplayName() { return displayName; }
        public Game createGame() { return creator.get(); }
    }
    
    /**
     * 注册游戏类型
     */
    public static void register(String gameType, String displayName, Supplier<Game> creator) {
        gameRegistry.put(gameType.toLowerCase(), new GameInfo(displayName, creator));
    }
    
    /**
     * 创建游戏实例
     */
    public static Game createGame(String gameType) {
        GameInfo info = gameRegistry.get(gameType.toLowerCase());
        if (info == null) {
            throw new IllegalArgumentException("未知游戏类型: " + gameType);
        }
        return info.createGame();
    }
    
    /**
     * 获取游戏显示名称
     */
    public static String getDisplayName(String gameType) {
        GameInfo info = gameRegistry.get(gameType.toLowerCase());
        return info != null ? info.getDisplayName() : gameType;
    }
    
    /**
     * 获取所有注册的游戏类型
     */
    public static Set<String> getSupportedGameTypes() {
        return gameRegistry.keySet();
    }
    
    /**
     * 获取所有游戏信息
     */
    public static Map<String, GameInfo> getAllGameInfo() {
        return new HashMap<>(gameRegistry);
    }
}
