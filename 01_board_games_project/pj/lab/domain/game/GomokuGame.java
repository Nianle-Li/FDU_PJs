package domain.game;

import java.util.List;
import java.util.stream.Stream;
import java.io.Serializable;
import java.util.Map;
import java.util.HashMap;


import domain.board.Board;
import domain.board.Direction;
import domain.board.Location;
import domain.board.Piece;
import domain.board.PieceColor;

public class GomokuGame implements Game {
    private final Board board;
    private boolean finished = false;
    private PieceColor winner = null;
    private PieceColor currentPieceColor;
    
    // 黑方和白方的炸弹数量
    private int blackBombs = 2;  // 黑方初始2个炸弹
    private int whiteBombs = 3;  // 白方初始3个炸弹
    
    // 添加回合计数器
    private int roundCount = 1;

    public GomokuGame() {
        this.board = new Board(15);  // 15×15棋盘
        
        // 初始化障碍物位置
        board.placePiece(2, 5, PieceColor.BARRIER);   // 3F
        board.placePiece(7, 6, PieceColor.BARRIER);   // 8G
        board.placePiece(8, 5, PieceColor.BARRIER);   // 9F
        board.placePiece(11, 10, PieceColor.BARRIER); // CK
        
        currentPieceColor = PieceColor.BLACK;
    }

    @Override
    public String getGameType() {
        return "gomoku";
    }
    
    @Override
    public List<String> getSupportedActions() {
        return List.of("useBomb");
    }
    
    @Override
    public boolean executeAction(String action, Object... params) {
        if ("useBomb".equals(action) && params.length > 0 && params[0] instanceof Location) {
            return useBomb((Location) params[0]);
        }
        return Game.super.executeAction(action, params);
    }

    /**
     * 在指定位置落子
     */
    public boolean placePiece(Location loc) {
        if (finished) {
            throw new GameException("游戏已经结束");
        }
        if (!board.isValidPlacement(loc)) {
            throw new GameException("无效位置:" + loc.toString());
        }

        board.placePiece(loc, currentPieceColor);
        if (checkWin(loc, currentPieceColor)) {
            finished = true;
            winner = currentPieceColor;
        } else {
            // 如果当前是白棋(后手)并且游戏没有结束，下完后回合数增加
            if (currentPieceColor == PieceColor.WHITE) {
                roundCount++;
            }
            currentPieceColor = currentPieceColor.oppositeColor();
        }
        return true;
    }

    /**
     * 计算从起始位置开始同色连续棋子数量
     */
    private int countHead(PieceColor pieceColor, List<Piece> pieces) {
        int currentCount = 0;
        for (Piece p : pieces) {
            if (p.getColor() == pieceColor) {
                currentCount++;
            } else {
                return currentCount;
            }
        }
        return currentCount;
    }

    /**
     * 检查是否连成五子
     * 分别检查横、竖、左斜、右斜四个方向
     */
    private boolean checkWin(Location location, PieceColor pieceColor) {
        return Stream.of(Direction.getOppositeDirections())
                .map((Direction[] dirs) -> countHead(
                        pieceColor, board.getLine(location, dirs[0]))
                        + countHead(pieceColor, board.getLine(location, dirs[1])) + 1)
                .anyMatch(c -> (c >= 5));
    }

    public boolean isOver() {
        return finished;
    }

    public PieceColor getWinner() {
        return winner;
    }

    public PieceColor getCurrentPlayer() {
        return currentPieceColor;
    }

    public Board getBoard() {
        return board;
    }

    /**
     * 获取当前玩家的炸弹数量
     */
    public int getCurrentPlayerBombs() {
        return currentPieceColor == PieceColor.BLACK ? blackBombs : whiteBombs;
    }
    
    /**
     * 获取指定颜色玩家的炸弹数量
     */
    @Override
    public Integer getPlayerBombs(PieceColor color) {
        return color == PieceColor.BLACK ? blackBombs : whiteBombs;
    }
    
    /**
     * 使用炸弹移除对方棋子
     */
    public boolean useBomb(Location loc) {
        if (finished) {
            throw new GameException("游戏已经结束");
        }
        
        // 检查当前玩家是否有炸弹
        if (getCurrentPlayerBombs() <= 0) {
            throw new GameException("没有炸弹可用");
        }
        
        // 检查该位置是否有效
        if (!board.isValidLocation(loc)) {
            throw new GameException("无效位置:" + loc.toString());
        }
        
        // 检查该位置是否有对方棋子
        PieceColor targetPiece = board.getPiece(loc);
        if (targetPiece != currentPieceColor.oppositeColor()) {
            throw new GameException("炸弹只能用于移除对方棋子");
        }
        
        // 使用炸弹，减少计数
        if (currentPieceColor == PieceColor.BLACK) {
            blackBombs--;
        } else {
            whiteBombs--;
        }
        
        // 移除对方棋子，放置弹坑
        board.replacePiece(loc, PieceColor.BOMB_CRATER);
        
        // 如果当前是白棋使用炸弹，回合数增加
        if (currentPieceColor == PieceColor.WHITE) {
            roundCount++;
        }
        
        // 切换到对方回合
        currentPieceColor = currentPieceColor.oppositeColor();
        
        return true;
    }

    /**
     * 获取当前回合数
     */
    @Override
    public Integer getCurrentRound() {
        return roundCount;
    }

    @Override
    public Map<String, Serializable> getAdditionalAttributes() {
        Map<String, Serializable> attributes = new HashMap<>();
        attributes.put("blackBombs", blackBombs);
        attributes.put("whiteBombs", whiteBombs);
        attributes.put("roundCount", roundCount);
        return attributes;
    }

    @Override
    public void restoreAdditionalAttributes(Map<String, Serializable> attributes) {
        if (attributes.containsKey("blackBombs")) {
            this.blackBombs = (Integer) attributes.get("blackBombs");
        }
        if (attributes.containsKey("whiteBombs")) {
            this.whiteBombs = (Integer) attributes.get("whiteBombs");
        }
        if (attributes.containsKey("roundCount")) {
            this.roundCount = (Integer) attributes.get("roundCount");
        }
    }

    @Override
    public boolean canCurrentPlayerUseBomb() {
        return getCurrentPlayerBombs() > 0;
    }
}