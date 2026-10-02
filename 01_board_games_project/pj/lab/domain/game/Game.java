package domain.game;

import domain.board.Board;
import domain.board.Location;
import domain.board.PieceColor;
import java.util.List;
import java.util.Map;
import java.io.Serializable;
import java.util.Collections;

public interface Game {

    // 获取游戏类型标识符
    String getGameType();

    // 判断游戏是否结束
    boolean isOver();

    // 获取胜利者（如果有）
    PieceColor getWinner();

    // 获取当前回合的玩家
    PieceColor getCurrentPlayer();

    // 在指定位置放置棋子
    boolean placePiece(Location loc);

    // 在坐标(x,y)处放置棋子的便捷方法
    default boolean placePiece(int x, int y) {
        return placePiece(Location.of(x, y));
    }
    
    // 获取游戏棋盘
    Board getBoard();
    
    // 获取游戏支持的特殊操作列表（如"跳过"、"使用炸弹"等）
    default List<String> getSupportedActions() {
        return List.of();
    }
    
    // 执行特殊操作
    default boolean executeAction(String action, Object... params) {
        throw new GameException("不支持的操作: " + action);
    }

    // 获取游戏特有属性，用于保存游戏状态
    default Map<String, Serializable> getAdditionalAttributes() {
        return Collections.emptyMap();
    }

    // 从保存的属性中恢复游戏特有状态
    default void restoreAdditionalAttributes(Map<String, Serializable> attributes) {
        // 默认不执行任何操作
    }

    // 获取玩家分数（若适用）
    default Integer getPlayerScore(PieceColor playerColor) {
        return null;
    }

    // 获取玩家剩余炸弹数（若适用）
    default Integer getPlayerBombs(PieceColor playerColor) {
        return null;
    }

    // 获取当前回合数（若适用）
    default Integer getCurrentRound() {
        return null;
    }

    // 当前玩家是否可以跳过回合
    default boolean canCurrentPlayerPass() {
        return false;
    }

    // 当前玩家是否可以使用炸弹
    default boolean canCurrentPlayerUseBomb() {
        return false;
    }
    
    // 获取当前玩家可落子的位置列表
    default List<Location> getCurrentPlayerValidMoves() {
        return Collections.emptyList();
    }
}
